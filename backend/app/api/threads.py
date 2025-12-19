"""Threads API endpoints."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict, Tuple
from datetime import datetime
import enum
import hashlib
import json
import time

from app.database import get_db
from app.models.thread import Thread
from app.models.message import Message, MessageRole
from app.models.provider_key import ProviderType
from app.models.audit import AuditLog
from app.models.org import Org
from app.security import set_rls_context
from app.api.deps import require_org_id, get_current_user_optional, CurrentUser
from app.adapters.base import ProviderAdapterError
from app.services.provider_keys import get_api_key_for_org
from app.services.provider_dispatch import call_provider_adapter, call_provider_adapter_streaming
from app.services.model_registry import get_fallback_model, validate_and_get_model
from app.services.token_estimator import estimate_messages_tokens, estimate_text_tokens
from app.services.ratelimit import (
    enforce_limits,
    record_additional_tokens,
)
from app.services.memory_guard import memory_guard
from app.services.performance import performance_monitor, PerformanceMetrics
from app.services.cancellation import cancellation_registry
from app.services.pacer import build_pacer
from app.services.coalesce import coalescer, coalesce_key
from app.services.stream_hub import stream_hub
from app.services.intelligent_router import intelligent_router
from app.services.memory_service import memory_service
from app.services.syntra_persona import inject_syntra_persona, sanitize_response
from app.services.memory_manager import (
    build_prompt_for_model, smooth_intent, update_last_intent
)
from app.services.thread_naming import generate_thread_title, should_auto_title
# CRITICAL: Use threads_store for thread operations (read/write separation)
# Import Turn and thread operations from threads_store when needed
from app.services.observability import log_turn, calculate_cost_estimate
from app.services.guardrails import sanitize_user_input, should_refuse, SafetyFlags
from app.services.response_cache import make_cache_key, get_cached, set_cached
from app.services.route_and_call import route_and_call
from app.services.collaboration_engine import CollaborationEngine
from app.services.main_assistant import MainAssistant
from app.services.conversation_storage import ConversationStorageService
from app.services.token_track import normalize_usage
from app.services.dynamic_router.integration import route_with_dynamic_router
from app.models.router_run import RouterRun
from contextlib import asynccontextmanager

# OpenTelemetry (optional)
try:
    from opentelemetry import trace
    tracer = trace.get_tracer(__name__)
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    tracer = None
from config import get_settings
import asyncio
import uuid
import os
import logging
logger = logging.getLogger(__name__)

settings = get_settings()

router = APIRouter()


def sse_event(data: dict, event: Optional[str] = None) -> bytes:
    """Generate SSE event frame."""
    chunks = []
    if event:
        chunks.append(f"event: {event}\n")
    chunks.append(f"data: {json.dumps(data, ensure_ascii=False)}\n\n")
    return "".join(chunks).encode("utf-8")
MAX_CONTEXT_MESSAGES = 20  # Increased to preserve more conversation history


async def _save_turn_to_db(
    db: AsyncSession,
    thread_id: str,
    user_id: Optional[str],
    user_content: str,
    assistant_content: str,
    provider: str,
    model: str,
    reason: str,
    scope: str,
    prompt_messages: List[Dict],
    provider_response: Any,
    request: "AddMessageRequest",
    prompt_tokens_estimate: int,
) -> Tuple[Message, Message]:
    """Save a single user+assistant turn to the database (leader only).
    
    Returns:
        (user_message, assistant_message) tuple
    """
    # Get next sequence
    next_sequence = await _get_next_sequence(db, thread_id)
    
    # Create user message
    user_message = Message(
        thread_id=thread_id,
        user_id=user_id,
        role=MessageRole.USER,
        content=user_content,
        sequence=next_sequence,
    )
    db.add(user_message)
    await db.flush()
    
    # Calculate tokens
    actual_prompt_tokens = provider_response.prompt_tokens or prompt_tokens_estimate
    completion_tokens = provider_response.completion_tokens or estimate_text_tokens(assistant_content)
    total_tokens = (actual_prompt_tokens or 0) + (completion_tokens or 0)
    
    # Create assistant message
    assistant_message = Message(
        thread_id=thread_id,
        role=MessageRole.ASSISTANT,
        content=assistant_content,
        provider=provider,
        model=model,
        provider_message_id=provider_response.provider_message_id,
        sequence=next_sequence + 1,
        prompt_tokens=actual_prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        citations=provider_response.citations,
        meta={
            "latency_ms": round(provider_response.latency_ms, 2),
            "request_id": provider_response.request_id,
            "ttfs_ms": round(provider_response.ttfs_ms, 2) if provider_response.ttfs_ms else None,  # Time to first token
        },
    )
    db.add(assistant_message)
    await db.flush()
    
    # Update thread
    thread_stmt = select(Thread).where(Thread.id == thread_id)
    thread_result = await db.execute(thread_stmt)
    thread = thread_result.scalar_one()
    thread.last_provider = provider
    thread.last_model = model
    # Update last message preview (truncate to ~120 chars)
    thread.last_message_preview = user_content[:120] if len(user_content) > 120 else user_content

    # Auto-generate title if this is the first message
    if should_auto_title(thread.title, next_sequence):
        thread.title = generate_thread_title(user_content)

    # Persist transparent routing preference (if explicitly set), and honor user "hide routing" requests.
    try:
        from app.services.routing_header import user_requested_hide_routing
        settings = thread.settings or {}
        if request.transparent_routing is not None:
            settings["transparent_routing"] = bool(request.transparent_routing)
        if user_requested_hide_routing(user_content):
            settings["transparent_routing"] = False
        thread.settings = settings
    except Exception:
        # Never block message persistence on a settings update
        pass

    # updated_at will be auto-updated by SQLAlchemy's onupdate
    
    # Create audit log
    audit_entry = AuditLog(
        thread_id=thread_id,
        message_id=assistant_message.id,
        user_id=user_id,
        provider=provider,
        model=model,
        reason=reason,
        fragments_included=[],
        fragments_excluded=[],
        scope=scope,
        package_hash=_package_hash(prompt_messages, request),
        response_hash=_response_hash(assistant_content),
        prompt_tokens=actual_prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
    db.add(audit_entry)
    
    # Commit all changes
    await db.commit()
    await db.refresh(user_message)
    await db.refresh(assistant_message)

    # CRITICAL: Add turns to in-memory thread store for fast context retrieval
    # This ensures conversation history is available for subsequent requests
    # (prevents context loss when model switches or on follow-up messages)
    try:
        from app.services.threads_store import add_turn, Turn
        add_turn(thread_id, Turn(role="user", content=user_content))
        add_turn(thread_id, Turn(role="assistant", content=assistant_content))
        logger.info(f"✅ Added turns to in-memory store for thread {thread_id}")
    except Exception as e:
        logger.warning(f"⚠️  Failed to add turns to in-memory store: {e}")
        # This is non-critical - DB will be fallback

    return user_message, assistant_message


class CreateThreadRequest(BaseModel):
    """Request to create a new thread."""
    user_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class CreateThreadResponse(BaseModel):
    """Response from creating a thread."""
    thread_id: str
    created_at: datetime


class ForwardScope(str, enum.Enum):
    """Scope for memory forwarding controls."""

    PRIVATE = "private"
    SHARED = "shared"


class MessageAttachment(BaseModel):
    """Attachment in a message."""
    type: str = Field(..., description="Attachment type: 'image' or 'file'")
    name: str = Field(..., description="Filename")
    url: Optional[str] = Field(None, description="Public URL to the attachment")
    data: Optional[str] = Field(None, description="Base64 encoded data")
    mimeType: Optional[str] = Field(None, description="MIME type (e.g., image/png)")


class AddMessageRequest(BaseModel):
    """Request to add a message to a thread."""
    user_id: Optional[str] = None
    content: str = Field(default="", description="Message text content")
    role: MessageRole = MessageRole.USER
    provider: Optional[ProviderType] = None  # Optional - will use intelligent routing if not specified
    model: Optional[str] = None  # Optional - will use intelligent routing if not specified
    reason: Optional[str] = None  # Optional - will be auto-generated if not specified
    transparent_routing: Optional[bool] = None  # If true, prepend a user-visible routing header
    scope: ForwardScope = ForwardScope.PRIVATE
    use_memory: bool = True  # Enable memory-based context by default
    attachments: Optional[List[MessageAttachment]] = None  # Optional image/file attachments
    collaboration_mode: bool = False  # Enable multi-agent collaboration


class MessageResponse(BaseModel):
    """Message response."""
    id: str
    role: str
    content: str
    provider: Optional[str] = None  # Hidden in production, shown only in debug mode
    model: Optional[str] = None  # Hidden in production, shown only in debug mode
    sequence: int
    created_at: datetime
    citations: Optional[Any] = None
    meta: Optional[Dict[str, Any]] = None


class RouterDecision(BaseModel):
    """Router decision (internal, not shown to end users)."""

    provider: str
    model: str
    reason: str


class AddMessageResponse(BaseModel):
    """Response from adding a message."""
    user_message: MessageResponse
    assistant_message: MessageResponse
    # router field removed - internal routing hidden from users


class SaveRawMessageRequest(BaseModel):
    """Request to save a message directly without AI processing."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    provider: Optional[str] = Field(None, description="Provider name (for assistant messages)")
    model: Optional[str] = Field(None, description="Model name (for assistant messages)")
    meta: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class SaveRawMessageResponse(BaseModel):
    """Response from saving a raw message."""
    id: str
    role: str
    content: str
    sequence: int
    created_at: datetime


class ThreadDetailResponse(BaseModel):
    """Thread with messages."""
    id: str
    org_id: str
    title: Optional[str]
    description: Optional[str]
    last_provider: Optional[str]
    last_model: Optional[str]
    created_at: datetime
    messages: List[MessageResponse]


class ThreadListItem(BaseModel):
    """Thread list item for sidebar."""
    id: str
    title: Optional[str]
    last_message_preview: Optional[str]
    last_provider: Optional[str]
    last_model: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    pinned: bool = False
    archived: bool = False


class UpdateThreadRequest(BaseModel):
    """Request to update thread title."""
    title: Optional[str] = None


class UpdateThreadSettingsRequest(BaseModel):
    """Request to update thread settings."""
    mode: Optional[str] = None  # auto, single, collaborate
    primary_model: Optional[Dict[str, Any]] = None
    models: Optional[List[Dict[str, Any]]] = None
    temperature: Optional[float] = None
    pinned: Optional[bool] = None
    transparent_routing: Optional[bool] = None


class AuditEntry(BaseModel):
    """Audit log entry."""

    id: str
    provider: str
    model: str
    reason: str
    scope: str
    package_hash: str
    response_hash: Optional[str]
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    total_tokens: Optional[int]
    created_at: datetime


@router.get("/", response_model=List[ThreadListItem])
async def list_threads(
    limit: int = 50,
    archived: Optional[bool] = None,  # None = exclude archived, True = only archived, False = only non-archived
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """List all threads for the organization, sorted by most recent first.
    
    Args:
        limit: Maximum number of threads to return (default 50)
        archived: Filter by archived status. None = exclude archived (default), 
                 True = only archived, False = only non-archived
    """
    # Set RLS context
    user_id = current_user.id if current_user else None
    await set_rls_context(db, org_id, user_id)

    # Build query - filter by org_id and creator_id if user is authenticated
    query = select(Thread).where(Thread.org_id == org_id)
    
    # CRITICAL FIX: Filter threads by creator_id to prevent cross-user data leaks
    # Also handle legacy threads with creator_id: null - show them only if user has messages in that thread
    if user_id:
        from sqlalchemy import or_, exists, and_
        # Show threads where:
        # 1. creator_id matches the user (new threads), OR
        # 2. creator_id is null AND user has messages in that thread (legacy threads)
        subquery = exists().where(
            and_(
                Message.thread_id == Thread.id,
                Message.user_id == user_id
            )
        )
        query = query.where(
            or_(
                Thread.creator_id == user_id,
                and_(
                    Thread.creator_id.is_(None),
                    subquery
                )
            )
        )
    
    # Filter archived threads (default: exclude archived)
    if archived is None:
        # Exclude archived threads by default
        query = query.where(Thread.archived == False)
    elif archived is True:
        # Only archived threads
        query = query.where(Thread.archived == True)
    else:
        # Only non-archived threads (explicit)
        query = query.where(Thread.archived == False)

    # Query threads ordered by updated_at (most recent first), then created_at
    result = await db.execute(
        query.order_by(Thread.updated_at.desc().nulls_last(), Thread.created_at.desc())
        .limit(limit)
    )
    threads = result.scalars().all()

    return [
        ThreadListItem(
            id=thread.id,
            title=thread.title,
            last_message_preview=thread.last_message_preview,
            last_provider=thread.last_provider,
            last_model=thread.last_model,
            created_at=thread.created_at,
            updated_at=thread.updated_at,
            pinned=thread.pinned or False,
            archived=thread.archived or False
        )
        for thread in threads
    ]


@router.get("/search", response_model=List[ThreadListItem])
async def search_threads(
    q: str = Query(..., description="Search query"),
    limit: int = 50,
    archived: Optional[bool] = None,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Search threads by title or message preview using full-text search.
    
    Args:
        q: Search query string
        limit: Maximum number of results (default 50)
        archived: Filter by archived status. None = exclude archived (default),
                 True = only archived, False = only non-archived
    """
    user_id = current_user.id if current_user else None
    await set_rls_context(db, org_id, user_id)

    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    search_term = f"%{q.strip().lower()}%"
    
    # Build query with search conditions
    from sqlalchemy import or_
    query = select(Thread).where(
        Thread.org_id == org_id,
        or_(
            Thread.title.ilike(search_term),
            Thread.last_message_preview.ilike(search_term)
        )
    )
    
    # CRITICAL FIX: Filter threads by creator_id to prevent cross-user data leaks
    if user_id:
        query = query.where(Thread.creator_id == user_id)
    
    # Filter archived threads (default: exclude archived)
    if archived is None:
        query = query.where(Thread.archived == False)
    elif archived is True:
        query = query.where(Thread.archived == True)
    else:
        query = query.where(Thread.archived == False)

    # Order by relevance (exact matches first, then by recency)
    result = await db.execute(
        query.order_by(
            Thread.title.ilike(f"{q.strip()}%").desc(),  # Exact match at start
            Thread.updated_at.desc().nulls_last(),
            Thread.created_at.desc()
        )
        .limit(limit)
    )
    threads = result.scalars().all()

    return [
        ThreadListItem(
            id=thread.id,
            title=thread.title,
            last_message_preview=thread.last_message_preview,
            last_provider=thread.last_provider,
            last_model=thread.last_model,
            created_at=thread.created_at,
            updated_at=thread.updated_at,
            pinned=thread.pinned or False,
            archived=thread.archived or False
        )
        for thread in threads
    ]


@router.patch("/{thread_id}/archive")
async def archive_thread(
    thread_id: str,
    archived: bool = Query(..., description="True to archive, False to unarchive"),
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Archive or unarchive a thread."""
    user_id = current_user.id if current_user else None
    await set_rls_context(db, org_id, user_id)

    # Get thread - filter by creator_id if user is authenticated
    query = select(Thread).where(Thread.id == thread_id, Thread.org_id == org_id)
    if user_id:
        query = query.where(Thread.creator_id == user_id)
    
    result = await db.execute(query)
    thread = result.scalar_one_or_none()

    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Update archived status
    thread.archived = archived
    if archived:
        from datetime import datetime, timezone
        thread.archived_at = datetime.now(timezone.utc)
    else:
        thread.archived_at = None

    await db.commit()
    await db.refresh(thread)

    return {
        "success": True,
        "thread_id": thread_id,
        "archived": thread.archived,
        "archived_at": thread.archived_at.isoformat() if thread.archived_at else None
    }


@router.patch("/{thread_id}")
async def update_thread(
    thread_id: str,
    request: UpdateThreadRequest,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Update thread title."""
    user_id = current_user.id if current_user else None
    await set_rls_context(db, org_id, user_id)

    # Get thread
    result = await db.execute(
        select(Thread).where(Thread.id == thread_id, Thread.org_id == org_id)
    )
    thread = result.scalar_one_or_none()

    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Update title
    if request.title is not None:
        thread.title = request.title

    await db.commit()
    await db.refresh(thread)

    return {"success": True, "title": thread.title}


@router.patch("/{thread_id}/settings")
async def update_thread_settings(
    thread_id: str,
    request: UpdateThreadSettingsRequest,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Update thread settings (mode, models, temperature, etc.)."""
    user_id = current_user.id if current_user else None
    await set_rls_context(db, org_id, user_id)

    # Get thread - filter by creator_id if user is authenticated
    query = select(Thread).where(Thread.id == thread_id, Thread.org_id == org_id)
    if user_id:
        query = query.where(Thread.creator_id == user_id)
    
    result = await db.execute(query)
    thread = result.scalar_one_or_none()

    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Get existing settings or create new dict
    settings = thread.settings or {}

    # Update settings fields
    if request.mode is not None:
        settings["mode"] = request.mode
    if request.primary_model is not None:
        settings["primaryModel"] = request.primary_model
    if request.models is not None:
        settings["models"] = request.models
    if request.temperature is not None:
        settings["temperature"] = request.temperature
    if request.transparent_routing is not None:
        settings["transparent_routing"] = bool(request.transparent_routing)

    thread.settings = settings

    # Update pinned separately (not in settings JSON)
    if request.pinned is not None:
        thread.pinned = request.pinned

    await db.commit()
    await db.refresh(thread)

    return {"success": True, "settings": thread.settings, "pinned": thread.pinned}


@router.delete("/{thread_id}")
async def delete_thread(
    thread_id: str,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """Delete a single thread and all its messages."""
    await set_rls_context(db, org_id)

    # Get thread
    result = await db.execute(
        select(Thread).where(Thread.id == thread_id, Thread.org_id == org_id)
    )
    thread = result.scalar_one_or_none()

    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Delete messages
    from sqlalchemy import delete
    await db.execute(
        delete(Message).where(Message.thread_id == thread_id)
    )

    # Delete audit logs
    await db.execute(
        delete(AuditLog).where(AuditLog.thread_id == thread_id)
    )

    # Delete thread
    await db.execute(
        delete(Thread).where(Thread.id == thread_id, Thread.org_id == org_id)
    )

    await db.commit()

    return {"success": True, "thread_id": thread_id}


@router.delete("/")
async def delete_all_threads(
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """Delete all threads for the organization."""
    await set_rls_context(db, org_id)

    # Get all threads for the org
    result = await db.execute(
        select(Thread).where(Thread.org_id == org_id)
    )
    threads = result.scalars().all()
    thread_ids = [thread.id for thread in threads]

    # Delete all messages and audit logs for these threads
    from sqlalchemy import delete
    for thread_id in thread_ids:
        await db.execute(
            delete(Message).where(Message.thread_id == thread_id)
        )
        await db.execute(
            delete(AuditLog).where(AuditLog.thread_id == thread_id)
        )

    # Delete all threads
    await db.execute(
        delete(Thread).where(Thread.org_id == org_id)
    )

    await db.commit()

    return {"success": True, "deleted_count": len(thread_ids)}


@router.post("/", response_model=CreateThreadResponse)
async def create_thread(
    request: CreateThreadRequest,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Create a new thread."""
    from app.models.user import User

    # Set RLS context
    user_id = current_user.id if current_user else None
    await set_rls_context(db, org_id, user_id)

    # CRITICAL FIX: Use authenticated user's ID from JWT token, not request.user_id
    # This ensures threads are properly associated with the correct user
    creator_id = None
    if current_user:
        # Use the authenticated user's ID from the JWT token
        creator_id = current_user.id
    elif request.user_id:
        # Fallback: if no authenticated user but user_id provided, try to find user
        result = await db.execute(
            select(User).where(User.id == request.user_id, User.org_id == org_id)
        )
        user = result.scalar_one_or_none()
        if user:
            creator_id = user.id
        else:
            logger.warning(f"⚠️ User '{request.user_id}' not found in users table - thread will have no creator")

    # Create thread
    new_thread = Thread(
        org_id=org_id,
        creator_id=creator_id,
        title=request.title,
        description=request.description
    )
    db.add(new_thread)
    await db.commit()
    await db.refresh(new_thread)

    return CreateThreadResponse(
        thread_id=new_thread.id,
        created_at=new_thread.created_at
    )


@router.post("/{thread_id}/messages", response_model=AddMessageResponse)
async def add_message(
    thread_id: str,
    request: AddMessageRequest,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Add a message to a thread with optional multi-agent collaboration."""
    logger.debug(f"🔍 DEBUG: add_message called - collaboration_mode={request.collaboration_mode}, content={request.content[:50]}...")
    user_id = current_user.id if current_user else None
    await set_rls_context(db, org_id, user_id)
    await memory_guard.ensure_health()

    thread = await _get_thread(db, thread_id, org_id, user_id)

    # Transparent routing header flag (per request, falling back to per-thread setting)
    thread_settings = thread.settings or {}
    transparent_routing = (
        bool(request.transparent_routing)
        if request.transparent_routing is not None
        else bool(thread_settings.get("transparent_routing", False))
    )

    # Check if collaboration mode is enabled
    if request.collaboration_mode:
        # Use main assistant with collaboration
        main_assistant = MainAssistant()
        
        # Collect API keys for all providers
        api_keys = {}
        for provider in [ProviderType.OPENAI, ProviderType.GEMINI, ProviderType.PERPLEXITY]:
            try:
                key = await get_api_key_for_org(db, org_id, provider)
                if key:
                    api_keys[provider.value] = key
            except Exception:
                continue  # Skip if provider not configured
        
        # Generate unique turn ID
        import uuid
        turn_id = str(uuid.uuid4())
        
        # Get chat history
        prior_messages = await _get_recent_messages(db, thread_id)
        chat_history = [
            {"role": msg.role.value, "content": msg.content}
            for msg in prior_messages
        ]
        
        # Handle collaboration
        result = await main_assistant.handle_message(
            user_message=request.content,
            turn_id=turn_id,
            api_keys=api_keys,
            collaboration_mode=request.collaboration_mode,
            chat_history=chat_history,
            nextgen_mode="legacy"
        )
        
        # NOTE: ConversationStorageService disabled - it uses a separate Base and
        # synchronous Session patterns incompatible with our AsyncSession.
        # The collaboration still works, but detailed agent outputs aren't persisted.
        # TODO: Refactor conversation_storage.py to use app.database.Base and async patterns
        # if result.get("type") == "collaboration" and result.get("agent_outputs"):
        #     storage_service = ConversationStorageService(db)
        #     from app.services.collaboration_engine import AgentOutput, AgentRole
        #     agent_outputs = []
        #     for output_dict in result["agent_outputs"]:
        #         agent_outputs.append(AgentOutput(
        #             role=AgentRole(output_dict["role"]),
        #             provider=output_dict["provider"],
        #             content=output_dict["content"],
        #             timestamp=output_dict["timestamp"],
        #             turn_id=turn_id
        #         ))
        #     storage_service.store_collaboration_turn(
        #         turn_id=turn_id,
        #         thread_id=thread_id,
        #         user_query=request.content,
        #         final_report=result["content"],
        #         agent_outputs=agent_outputs,
        #         total_time_ms=result.get("total_time_ms", 0),
        #         collaboration_mode="full"
        #     )
        
        # Save messages to regular thread
        user_msg, assistant_msg = await _save_turn_to_db(
            db=db,
            thread_id=thread_id,
            user_id=request.user_id,
            user_content=request.content,
            assistant_content=result["content"],
            provider="collaboration",
            model="multi-agent",
            reason="Multi-agent collaboration",
            scope=request.scope.value,
            prompt_messages=[{"role": "user", "content": request.content}],
            provider_response=type('obj', (object,), {
                'content': result["content"],
                'prompt_tokens': 0,
                'completion_tokens': len(result["content"]) // 4,  # Rough estimate
                'provider_message_id': turn_id,
                'latency_ms': result.get("total_time_ms", 0),
                'request_id': turn_id,
                'citations': None
            })(),
            request=request,
            prompt_tokens_estimate=len(request.content) // 4,
        )

        user_resp = _to_message_response(user_msg, hide_provider=False)
        assistant_resp = _to_message_response(assistant_msg, hide_provider=False)
        if transparent_routing:
            from app.services.routing_header import RoutingHeaderInfo, build_routing_header, provider_name
            header = build_routing_header(
                RoutingHeaderInfo(
                    provider=provider_name(assistant_msg.provider),
                    model=assistant_msg.model or "unknown",
                    route_reason="Multi-agent collaboration.",
                    context="full_history",
                    repair_attempts=0,
                    fallback_used="no",
                )
            )
            assistant_resp.content = f"{header}{assistant_resp.content}"

        return AddMessageResponse(user_message=user_resp, assistant_message=assistant_resp)

    org = await _get_org(db, org_id)
    request_limit = org.requests_per_day or settings.default_requests_per_day
    token_limit = org.tokens_per_day or settings.default_tokens_per_day

    # Get recent messages
    prior_messages = await _get_recent_messages(db, thread_id)
    conversation_history = [
        {"role": msg.role.value, "content": msg.content}
        for msg in prior_messages
    ]

    # STEP 1: Use intelligent router if provider/model not specified
    routing_decision = None
    has_image_attachments = bool(
        request.attachments and any((getattr(a, "type", "") or "").lower() == "image" for a in request.attachments)
    )

    if has_image_attachments:
        # Analyze image and route to best AI model
        from app.services.image_analyzer import analyze_image_and_route
        
        # Get first image attachment for analysis
        image_attachment = next((a for a in request.attachments if (getattr(a, "type", "") or "").lower() == "image"), None)
        
        if image_attachment:
            # Extract image data (base64)
            image_data = getattr(image_attachment, "data", None) or getattr(image_attachment, "url", None)
            
            if image_data:
                # Get API keys for analysis
                api_keys_dict = {}
                for provider_type in [ProviderType.GEMINI, ProviderType.OPENAI]:
                    try:
                        key = await get_api_key_for_org(db, org_id, provider_type)
                        if key:
                            api_keys_dict[provider_type.value] = key
                    except Exception:
                        continue
                
                # Analyze image and get routing decision
                try:
                    routing_result = await analyze_image_and_route(
                        image_data=image_data,
                        user_query=request.content,
                        api_keys=api_keys_dict
                    )
                    
                    request.provider = routing_result["provider"]
                    request.model = routing_result["model"]
                    if not request.reason:
                        request.reason = routing_result["reason"]
                    
                    logger.info(f"🖼️ Image analyzed: {routing_result.get('image_type', 'unknown')} → {routing_result['provider'].value}/{routing_result['model']}")
                except Exception as e:
                    logger.error(f"Image analysis failed, defaulting to Gemini: {e}")
                    # Fallback to Gemini
                    request.provider = ProviderType.GEMINI
                    request.model = "gemini-2.5-flash"
                    if not request.reason:
                        request.reason = "Vision/image understanding (Gemini 2.5 Flash - multimodal)"
            else:
                # No image data, default to Gemini
                request.provider = ProviderType.GEMINI
                request.model = "gemini-2.5-flash"
                if not request.reason:
                    request.reason = "Vision/image understanding (Gemini 2.5 Flash - multimodal)"
        else:
            # No image attachment found, default to Gemini
            request.provider = ProviderType.GEMINI
            request.model = "gemini-2.5-flash"
            if not request.reason:
                request.reason = "Vision/image understanding (Gemini 2.5 Flash - multimodal)"
    elif not request.provider or not request.model:
        routing_decision = await intelligent_router.route(
            db=db,
            org_id=org_id,
            query=request.content,
            conversation_history=conversation_history,
            preferred_provider=request.provider,
            preferred_model=request.model
        )
        # Use router's decision
        request.provider = routing_decision.provider
        request.model = routing_decision.model
        if not request.reason:
            request.reason = routing_decision.reason
    else:
        # User specified provider/model, use default reason if not provided
        if not request.reason:
            request.reason = f"User-specified {request.provider.value} with {request.model}"

    # STEP 2: Retrieve memory context for cross-model context sharing
    # Feature flag to disable memory (for debugging/performance)
    memory_enabled = bool(int(os.getenv("MEMORY_ENABLED", "0")))  # Disabled by default for now

    memory_context = None
    if request.use_memory and memory_enabled and not memory_guard.disabled:
        try:
            # Add timeout to prevent hanging
            memory_context = await asyncio.wait_for(
                memory_service.retrieve_memory_context(
                    db=db,
                    org_id=org_id,
                    user_id=request.user_id,
                    query=request.content,
                    thread_id=thread_id,
                    top_k=3,
                    current_provider=request.provider  # Pass provider for access graph checks
                ),
                timeout=2.0  # 2 second timeout
            )
        except asyncio.TimeoutError:
            logger.warning("⚠️  Memory retrieval timeout, continuing without memory")
        except Exception as e:
            logger.warning(f"⚠️  Memory retrieval error: {e}, continuing without memory")

    # STEP 3: Use centralized context builder
    # This ensures ALL models get the same rich context (history + memory + rewritten query)
    from app.services.context_builder import context_builder
    from app.services.syntra_persona import SYNTRA_SYSTEM_PROMPT, inject_syntra_persona
    
    # Thread description doubles as a custom system prompt (Phase 3 QA, custom personas)
    custom_system_prompt = (thread.description or "").strip()
    
    # Check if QA mode is enabled via thread description
    qa_mode = custom_system_prompt == "PHASE3_QA_MODE" or "PHASE3_QA_MODE" in custom_system_prompt
    
    # Detect intent from routing decision reason for LaTeX math formatting
    from app.services.syntra_persona import detect_intent_from_reason
    detected_intent = None
    if routing_decision and routing_decision.reason:
        detected_intent = detect_intent_from_reason(routing_decision.reason)
    
    # Build base system prompt with DAC persona
    base_prompt_messages = [{"role": "system", "content": SYNTRA_SYSTEM_PROMPT}]
    if custom_system_prompt and not qa_mode:
        base_prompt_messages.insert(0, {
            "role": "system",
            "content": custom_system_prompt
        })
    base_prompt_messages = inject_syntra_persona(base_prompt_messages, qa_mode=qa_mode, intent=detected_intent, provider=request.provider.value if request.provider else None)

    base_system_prompt = base_prompt_messages[0]["content"] if base_prompt_messages else SYNTRA_SYSTEM_PROMPT
    
    # Use centralized context builder
    # This handles: short-term history + memory + query rewriting
    # Convert attachments to dict format if present
    attachments_dict = None
    if request.attachments:
        attachments_dict = [
            {
                "type": a.type,
                "name": a.name,
                "url": a.url,
                "data": a.data,
                "mimeType": a.mimeType
            }
            for a in request.attachments
        ]

    context_result = await context_builder.build_contextual_messages(
        db=db,
        thread_id=thread_id,
        user_id=request.user_id,
        org_id=org_id,
        latest_user_message=request.content,
        provider=request.provider,
        use_memory=request.use_memory if hasattr(request, 'use_memory') else True,
        use_query_rewriter=False,  # Non-streaming path doesn't use query rewriter currently
        base_system_prompt=base_system_prompt,
        attachments=attachments_dict
    )
    
    # Use the messages from context builder
    prompt_messages = context_result.messages
    
    # CRITICAL LOGGING: Log provider call with detailed context info
    # This matches the TypeScript blueprint format for debugging
    logger.info(f"\n{'='*80}")
    logger.info(f"📤 SENDING TO PROVIDER (non-streaming): {request.provider.value}/{request.model}")
    logger.info(f"{'='*80}")
    logger.info(f"Using centralized context builder ✓")
    logger.info(f"Total messages: {len(prompt_messages)}")
    logger.info(f"Conversation history turns: {len(context_result.short_term_history)}")
    logger.info(f"Memory snippet present: {context_result.memory_snippet is not None}")
    if context_result.memory_snippet:
        logger.info(f"Memory snippet length: {len(context_result.memory_snippet)} chars")
    logger.info(f"Query rewritten: {context_result.rewritten_query is not None}")
    
    # Detailed messages preview (matches TypeScript blueprint)
    logger.info(f"\nMessages preview (first 120 chars each):")
    for i, msg in enumerate(prompt_messages):
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')
        if isinstance(content, str):
            preview = content[:120]
            logger.info(f"  [{i}] {role}: {preview}{'...' if len(content) > 120 else ''}")
        else:
            logger.info(f"  [{i}] {role}: [non-string content]")
    
    if context_result.rewritten_query:
        logger.info(f"\nRewritten query (first 120 chars): {context_result.rewritten_query[:120]}{'...' if len(context_result.rewritten_query) > 120 else ''}")
    
    logger.info(f"{'='*80}\n")

    prompt_tokens_estimate = estimate_messages_tokens(prompt_messages)

    await enforce_limits(
        org_id,
        request.provider,
        prompt_tokens_estimate,
        request_limit,
        token_limit,
    )

    api_key = await get_api_key_for_org(db, org_id, request.provider)

    # Validate and potentially correct the model before calling
    validated_model = validate_and_get_model(request.provider, request.model)
    if validated_model != request.model:
        # Update the request model if it was corrected
        request.model = validated_model

    # Set current model before performance tracking
    current_model = validated_model

    # Guard non-idempotent operations (tool calls, attachments, etc.)
    # Skip coalescing for operations with side effects
    has_side_effects = False  # TODO: Check for tool_calls or attachments in request
    
    # Start performance tracking
    perf_metrics = performance_monitor.start_request(
        provider=request.provider.value,
        model=current_model,
        thread_id=thread_id,
        user_id=request.user_id,
        streaming=False,
    )

    # Generate coalesce key from provider, model, thread, and new message
    # Using thread_id + new message ensures coalescing works even if conversation state changes
    coal_key = coalesce_key(
        request.provider.value,
        current_model,
        prompt_messages,
        thread_id=thread_id
    )

    # Leader function: makes provider call and writes to DB once
    async def leader_make():
        """Leader: call provider and save to DB. Returns normalized response for followers."""
        start_time = time.perf_counter()
        queue_wait_ms = 0
        
        # Retry logic
        max_retries = 2
        base_delay = 1.0
        provider_response = None
        current_attempt_model = current_model
        
        for attempt in range(max_retries):
            try:
                # Use pacer to manage rate limits
                pacer = build_pacer(request.provider.value)
                async with pacer as slot:
                    queue_wait_ms = slot.queue_wait_ms
                    provider_response = await call_provider_adapter(
                        request.provider,
                        current_attempt_model,
                        prompt_messages,
                        api_key,
                    )
                # Mark TTFT
                perf_metrics.mark_ttft()
                break  # Success
                
            except ProviderAdapterError as exc:
                perf_metrics.retry_count = attempt + 1
                error_str = str(exc).lower()
                
                is_model_error = any(
                    keyword in error_str 
                    for keyword in ["invalid model", "model not found", "no endpoints", "model unavailable", "permitted models"]
                )
                
                is_rate_limit = any(
                    keyword in error_str
                    for keyword in ["rate limit", "429", "too many requests", "quota"]
                )
                
                # Rate limit - exponential backoff
                if is_rate_limit and attempt < max_retries - 1:
                    delay = min(base_delay * (2 ** attempt), 8.0)
                    await asyncio.sleep(delay)
                    continue
                
                # Model error - try fallback
                if is_model_error and attempt < max_retries - 1:
                    fallback_model = get_fallback_model(request.provider, current_attempt_model)
                    if fallback_model and fallback_model != current_attempt_model:
                        from app.services.model_registry import is_valid_model
                        if is_valid_model(request.provider, fallback_model):
                            current_attempt_model = fallback_model
                            await asyncio.sleep(0.5)
                            continue
                
                # No more retries
                perf_metrics.error = str(exc)
                perf_metrics.mark_end()
                await performance_monitor.record_metrics(perf_metrics)

                # Record failure for intelligent router
                intelligent_router.record_performance(
                    provider=request.provider,
                    model=current_attempt_model,
                    latency_ms=0,
                    success=False,
                    error=str(exc)
                )

                status_code = status.HTTP_429_TOO_MANY_REQUESTS if is_rate_limit else status.HTTP_502_BAD_GATEWAY
                raise HTTPException(status_code=status_code, detail=str(exc)) from exc
        
        if provider_response is None:
            perf_metrics.error = "No response after retries"
            perf_metrics.mark_end()
            await performance_monitor.record_metrics(perf_metrics)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to get response from {request.provider.value} after {max_retries} attempts",
            )
        
        # Calculate tokens
        actual_prompt_tokens = provider_response.prompt_tokens or prompt_tokens_estimate
        completion_tokens = provider_response.completion_tokens or estimate_text_tokens(provider_response.content)
        total_tokens = (actual_prompt_tokens or 0) + (completion_tokens or 0)

        # DEBUG: log finish_reason and token usage for normal mode
        finish_reason = getattr(provider_response, "finish_reason", None)
        try:
            logger.debug(
                f"[NORMAL MODE] provider={request.provider.value} "
                f"model={current_attempt_model} "
                f"finish_reason={finish_reason} "
                f"prompt_tokens={actual_prompt_tokens} "
                f"completion_tokens={completion_tokens} "
                f"total_tokens={total_tokens} "
                f"content_length={len(provider_response.content)}"
            )
        except Exception:
            # Don't let logging break the request
            pass
        
        # Record additional tokens if needed
        additional_tokens = max(total_tokens - prompt_tokens_estimate, 0)
        if additional_tokens:
            await record_additional_tokens(org_id, request.provider, additional_tokens)
        
        # Sanitize response to maintain DAC persona
        sanitized_content = sanitize_response(
            provider_response.content,
            request.provider.value
        )
        
        # Prepend thinking preamble for UI display - DISABLED
        # from app.services.thinking_preamble import generate_thinking_preamble
        # preamble = generate_thinking_preamble(request.content)
        # sanitized_content = preamble + sanitized_content

        # Save messages to DB (LEADER ONLY)
        user_msg, assistant_msg = await _save_turn_to_db(
            db=db,
            thread_id=thread_id,
            user_id=request.user_id,
            user_content=request.content,
            assistant_content=sanitized_content,  # Use sanitized content
            provider=request.provider.value,
            model=current_attempt_model,
            reason=request.reason,
            scope=request.scope.value,
            prompt_messages=prompt_messages,
            provider_response=provider_response,
            request=request,
            prompt_tokens_estimate=prompt_tokens_estimate,
        )

        # STEP 4: Save memory from this turn (enables cross-model context sharing)
        if request.use_memory and memory_enabled and not memory_guard.disabled:
            try:
                # Save memory asynchronously, don't block response
                # Add timeout to prevent hanging
                fragments_saved = await asyncio.wait_for(
                    memory_service.save_memory_from_turn(
                        db=db,
                        org_id=org_id,
                        user_id=request.user_id,
                        thread_id=thread_id,
                        user_message=request.content,
                        assistant_message=provider_response.content,
                        provider=request.provider,
                        model=current_attempt_model,
                        scope=request.scope.value
                    ),
                    timeout=3.0  # 3 second timeout
                )
                if fragments_saved > 0:
                    logger.info(f"✅ Saved {fragments_saved} memory fragments from turn")
            except asyncio.TimeoutError:
                logger.warning(f"⚠️  Memory save timeout, continuing without saving")
            except Exception as e:
                # Don't fail the request if memory saving fails
                logger.warning(f"⚠️  Memory save error: {e}, continuing without saving")

        # Complete performance tracking
        perf_metrics.mark_end()
        perf_metrics.prompt_tokens = actual_prompt_tokens
        perf_metrics.completion_tokens = completion_tokens
        perf_metrics.total_tokens = total_tokens
        perf_metrics.queue_wait_ms = queue_wait_ms
        await performance_monitor.record_metrics(perf_metrics)

        # Record performance for intelligent router
        intelligent_router.record_performance(
            provider=request.provider,
            model=current_attempt_model,
            latency_ms=provider_response.latency_ms,
            success=True
        )
        
        # Return normalized response (followers will reuse this)
        # Hide provider/model info to maintain unified DAC persona
        return {
            "user_message": _to_message_response(user_msg, hide_provider=False),
            "assistant_message": _to_message_response(assistant_msg, hide_provider=False),
            "routing_meta": {
                "provider": request.provider,
                "model": current_attempt_model,
                "route_reason": request.reason,
                "context": "full_history",
                "repair_attempts": 0,
                "fallback_used": "yes" if current_attempt_model != current_model else "no",
            },
        }
    
    # Feature flag check
    coalesce_enabled = bool(int(os.getenv("COALESCE_ENABLED", "1")))
    
    # Run with coalescing - only leader does the work
    try:
        if coalesce_enabled and not has_side_effects:
            response_data = await coalescer.run(coal_key, leader_make)
        else:
            # Legacy path (no coalescing) or side-effect operations
            response_data = await leader_make()
    except HTTPException:
        raise
    except Exception as e:
        perf_metrics.error = str(e)
        perf_metrics.mark_end()
        await performance_monitor.record_metrics(perf_metrics)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )
    
    # Both leader and followers return the same response
    # Router decision is now hidden from end users to maintain DAC persona
    if transparent_routing:
        from app.services.routing_header import RoutingHeaderInfo, build_routing_header, provider_name
        routing_meta = response_data.get("routing_meta") or {}
        header = build_routing_header(
            RoutingHeaderInfo(
                provider=provider_name(routing_meta.get("provider")),
                model=routing_meta.get("model") or "unknown",
                route_reason=routing_meta.get("route_reason") or "unknown",
                context=routing_meta.get("context") or "full_history",
                repair_attempts=int(routing_meta.get("repair_attempts") or 0),
                fallback_used=routing_meta.get("fallback_used") or "no",
            )
        )
        response_data["assistant_message"].content = f"{header}{response_data['assistant_message'].content}"
    return AddMessageResponse(
        user_message=response_data["user_message"],
        assistant_message=response_data["assistant_message"],
    )


@router.post("/{thread_id}/messages/raw", response_model=SaveRawMessageResponse)
async def save_raw_message(
    thread_id: str,
    request: SaveRawMessageRequest,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Save a message directly to the database without triggering AI processing.

    Use this endpoint for:
    - Saving council orchestration messages
    - Saving messages from external sources
    - Manually adding context to a conversation
    """
    from app.models.message import Message, MessageRole
    from sqlalchemy import select, func

    user_id = current_user.id if current_user else None
    await set_rls_context(db, org_id, user_id)

    # Verify thread exists
    thread = await _get_thread(db, thread_id, org_id, user_id)

    try:
        # Get next sequence number
        sequence_stmt = select(func.max(Message.sequence)).where(Message.thread_id == thread_id)
        sequence_result = await db.execute(sequence_stmt)
        max_sequence = sequence_result.scalar()
        next_sequence = (max_sequence or -1) + 1

        # Determine message role
        role = MessageRole.USER if request.role.lower() == "user" else MessageRole.ASSISTANT

        # Create message with meta if provided
        message = Message(
            thread_id=thread_id,
            role=role,
            content=request.content,
            sequence=next_sequence,
            provider=request.provider,
            model=request.model,
            meta=request.meta,
        )
        db.add(message)
        await db.flush()
        await db.refresh(message)
        await db.commit()

        logger.info(f"💾 Saved raw message to thread {thread_id}: role={request.role}, sequence={next_sequence}")

        return SaveRawMessageResponse(
            id=str(message.id),
            role=message.role.value,
            content=message.content,
            sequence=message.sequence,
            created_at=message.created_at,
        )

    except Exception as e:
        await db.rollback()
        logger.warning(f"❌ Failed to save raw message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save message: {str(e)}")


@router.post("/{thread_id}/messages/stream")
async def add_message_streaming(
    thread_id: str,
    request: AddMessageRequest,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Add a message to a thread with streaming response (fan-out to multiple clients)."""
    # AGGRESSIVE OPTIMIZATION: Start streaming immediately, defer non-critical work
    
    # Step 1: Fast safety check (no DB, no network)
    sanitized_content, safety_flags = sanitize_user_input(request.content)
    should_refuse_request, refusal_reason = should_refuse(safety_flags)
    if should_refuse_request:
        turn_id = str(uuid.uuid4())
        asyncio.create_task(log_turn(
            thread_id=thread_id,
            turn_id=turn_id,
            intent="safety_refusal",
            router_decision={"provider": "none", "model": "none", "reason": "Safety guardrail"},
            provider="none",
            model="none",
            latency_ms=0,
            safety_flags={
                "has_pii": safety_flags.has_pii,
                "pii_types": safety_flags.pii_types,
                "prompt_injection_risk": safety_flags.prompt_injection_risk,
                "refusal_reason": refusal_reason,
            }
        ))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=refusal_reason or "Request cannot be processed"
        )
    
    user_content = sanitized_content
    
    # Step 1.4: Check for media generation intent (images/graphs)
    from app.services.media_intent_detector import media_intent_detector
    from app.services.media_generation import media_generation_service
    
    # Get previous assistant message for context (in case user says "just generate")
    previous_ai_message = None
    try:
        from app.services.threads_store import get_history
        history_turns = get_history(thread_id, max_turns=5)
        logger.debug(f"🔍 Checking history for previous AI message. Found {len(history_turns)} turns")
        # Find the last assistant message (skip the current user message which was just added)
        for turn in reversed(history_turns):
            role_str = str(turn.role).lower() if hasattr(turn, 'role') else ''
            logger.info(f"  Turn role: {role_str}, content: {turn.content[:50] if turn.content else 'empty'}...")
            if role_str == 'assistant':
                previous_ai_message = turn.content
                logger.info(f"✅ Found previous AI message: {previous_ai_message[:100]}...")
                break
        if not previous_ai_message:
            logger.warning(f"⚠️  No previous assistant message found in history")
    except Exception as e:
        logger.warning(f"⚠️  Could not get previous message for context: {e}")
        import traceback
        logger.info(traceback.format_exc())
    
    media_intent, media_metadata = media_intent_detector.detect_intent(user_content, previous_ai_message)
    should_generate_media = media_intent != "none"
    
    # Log intent detection for debugging
    if should_generate_media:
        logger.info(f"🎨 Media generation intent detected: {media_intent}, metadata: {media_metadata}")
        if media_metadata and media_metadata.get("use_previous"):
            logger.info(f"📝 Using previous AI message as prompt: {previous_ai_message[:100] if previous_ai_message else 'None'}...")
    else:
        logger.info(f"ℹ️  No media generation intent detected for: {user_content[:50]}...")
    
    # Step 1.5: Query Rewriter (if enabled)
    # Feature flag for query rewriting
    FEATURE_COREWRITE = settings.feature_corewrite

    rewritten_content = user_content
    is_ambiguous = False
    disambiguation_data = None

    if FEATURE_COREWRITE:
        try:
            # Get recent messages from in-memory turn storage (fast, no DB)
            # CRITICAL: Use threads_store (read-only) for context building
            from app.services.threads_store import get_history
            history_turns = get_history(thread_id, max_turns=8)
            recent_turns = [
                {
                    "role": turn.role if isinstance(turn.role, str) else turn.role.value if hasattr(turn.role, 'value') else str(turn.role),
                    "content": turn.content
                }
                for turn in history_turns
            ]

            # LLM-based context extraction with coreference resolution (works for ANY topic)
            from app.services.llm_context_extractor import resolve_references_in_query

            # Use comprehensive coreference resolution
            # This combines entity extraction, tracking, and query rewriting
            resolved_query, is_ambiguous, disambiguation_data = await resolve_references_in_query(
                thread_id=thread_id,
                user_message=user_content,
                conversation_history=recent_turns
            )

            # Map to existing format for backward compatibility
            rewrite_result = {
                "rewritten": resolved_query,
                "needs_clarification": is_ambiguous,
                "reasoning": disambiguation_data.get("reasoning", "") if disambiguation_data else ""
            }

            if disambiguation_data:
                rewrite_result["clarification_question"] = disambiguation_data.get("question", "Which did you mean?")
                rewrite_result["options"] = disambiguation_data.get("options", [])

            # Check if LLM needs clarification
            if rewrite_result.get("needs_clarification", False):
                is_ambiguous = True

                # Log for debugging
                logger.debug(f"🔍 LLM detected ambiguity: {user_content[:50]}...")
                logger.info(f"   Reason: {rewrite_result.get('reasoning', 'unknown')}")

                # Return disambiguation as SSE event
                async def disambiguation_source():
                    clarification_data = {
                        'type': 'clarification',
                        'question': rewrite_result.get('clarification_question', 'Which did you mean?'),
                        'options': rewrite_result.get('options', []),
                        'originalMessage': user_content
                    }
                    yield "event: clarification\n"
                    yield f"data: {json.dumps(clarification_data)}\n\n"
                    yield "event: done\n"
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"

                HEADERS_SSE = {
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-store, no-transform",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                }
                return StreamingResponse(disambiguation_source(), headers=HEADERS_SSE, media_type="text/event-stream")
            else:
                # Use LLM-rewritten content
                rewritten_content = rewrite_result.get("rewritten", user_content)

                # Log for debugging
                if rewritten_content != user_content:
                    logger.info(f"✏️  LLM rewrite: {user_content[:50]}... → {rewritten_content[:50]}...")
                    logger.info(f"   Reasoning: {rewrite_result.get('reasoning', 'N/A')}")
        except Exception as e:
            # If rewriter fails, fall back to original content
            import traceback
            logger.warning(f"⚠️  LLM context error: {e}")
            logger.info(traceback.format_exc())
            rewritten_content = user_content
    
    # Step 2: ULTRA-FAST PATH - Route and stream immediately, validate in background
    import time as perf_time
    start_routing = perf_time.perf_counter()

    # Detect if the user attached any images (forces Gemini vision models)
    has_image_attachments = bool(
        request.attachments and any((getattr(a, "type", "") or "").lower() == "image" for a in request.attachments)
    )
    forced_reason = "Vision/image understanding (Gemini 2.5 Flash - multimodal)"

    # Start DB operations early for dynamic router
    start_db = perf_time.perf_counter()
    rls_task = set_rls_context(db, org_id)
    await rls_task  # Need RLS for router to query available providers
    
    if has_image_attachments:
        # Analyze image and route to best AI model
        from app.services.image_analyzer import analyze_image_and_route
        
        # Get first image attachment for analysis
        image_attachment = next((a for a in request.attachments if (getattr(a, "type", "") or "").lower() == "image"), None)
        
        if image_attachment:
            # Extract image data (base64)
            image_data = getattr(image_attachment, "data", None) or getattr(image_attachment, "url", None)
            
            if image_data:
                # Get API keys for analysis
                api_keys_dict = {}
                for provider_type in [ProviderType.GEMINI, ProviderType.OPENAI]:
                    try:
                        key = await get_api_key_for_org(db, org_id, provider_type)
                        if key:
                            api_keys_dict[provider_type.value] = key
                    except Exception:
                        continue
                
                # Analyze image and get routing decision
                try:
                    routing_result = await analyze_image_and_route(
                        image_data=image_data,
                        user_query=rewritten_content or user_content,
                        api_keys=api_keys_dict
                    )
                    
                    provider_enum = routing_result["provider"]
                    model = routing_result["model"]
                    reason = routing_result["reason"]
                    validated_model = validate_and_get_model(provider_enum, model)
                    router_decision = None
                    
                    logger.info(f"🖼️ Image analyzed: {routing_result.get('image_type', 'unknown')} → {provider_enum.value}/{model}")
                except Exception as e:
                    logger.error(f"Image analysis failed, defaulting to Gemini: {e}")
                    # Fallback to Gemini
                    provider_enum = ProviderType.GEMINI
                    model = "gemini-2.5-flash"
                    reason = forced_reason
                    validated_model = validate_and_get_model(provider_enum, model)
                    router_decision = None
            else:
                # No image data, default to Gemini
                provider_enum = ProviderType.GEMINI
                model = "gemini-2.5-flash"
                reason = forced_reason
                validated_model = validate_and_get_model(provider_enum, model)
                router_decision = None
        else:
            # No image attachment found, default to Gemini
            provider_enum = ProviderType.GEMINI
            model = "gemini-2.5-flash"
            reason = forced_reason
            validated_model = validate_and_get_model(provider_enum, model)
            router_decision = None
    else:
        # PERFORMANCE OPTIMIZATION: Use fast keyword-based routing (10-30ms, no LLM blocking)
        # This unblocks streaming while still routing to the correct specialist model
        from app.api.router import analyze_content
        provider_str, model, reason = analyze_content(rewritten_content, 0, has_image_attachments)
        provider_enum = ProviderType(provider_str)
        validated_model = validate_and_get_model(provider_enum, model)
        router_decision = None

        # Optionally schedule dynamic router in background for future ML-based refinement
        # (Currently not needed - legacy router works well, but kept for future)
        # async def run_dynamic_router_in_background():
        #     try:
        #         router_decision = await route_with_dynamic_router(...)
        #     except: pass
        # asyncio.create_task(run_dynamic_router_in_background())

    logger.info(f"⚡ Provider selected in {(perf_time.perf_counter() - start_routing)*1000:.0f}ms -> {provider_enum.value}/{validated_model}")

    # Log LLM rewrite if it happened
    if FEATURE_COREWRITE and rewritten_content != user_content:
        logger.info(f"📝 LLM context-aware rewrite: '{user_content[:80]}...' → '{rewritten_content[:80]}...'")

    # Ensure downstream components see the actual provider/model we plan to call
    request.provider = provider_enum
    request.model = validated_model
    if not request.reason:
        request.reason = forced_reason if has_image_attachments else reason

    # Transparent routing header flag (per request, falling back to per-thread setting)
    transparent_routing = bool(request.transparent_routing) if request.transparent_routing is not None else False
    if request.transparent_routing is None:
        try:
            settings_stmt = select(Thread.settings).where(Thread.id == thread_id, Thread.org_id == org_id)
            if current_user and current_user.id:
                settings_stmt = settings_stmt.where(Thread.creator_id == current_user.id)
            settings_result = await db.execute(settings_stmt)
            settings_value = settings_result.scalar_one_or_none() or {}
            transparent_routing = bool((settings_value or {}).get("transparent_routing", False))
        except Exception:
            transparent_routing = False

    routing_header_text = None
    if transparent_routing:
        from app.services.routing_header import RoutingHeaderInfo, build_routing_header, provider_name
        routing_header_text = build_routing_header(
            RoutingHeaderInfo(
                provider=provider_name(provider_enum),
                model=validated_model or "unknown",
                route_reason=request.reason or "unknown",
                context="full_history",
                repair_attempts=0,
                fallback_used="no",
            )
        )
    
    # Detect intent from routing reason for LaTeX math formatting
    from app.services.syntra_persona import detect_intent_from_reason
    detected_intent = detect_intent_from_reason(reason) if reason else None
    
    # Get API key for chosen provider
    api_key_task = get_api_key_for_org(db, org_id, provider_enum)
    
    # CRITICAL: Use centralized context builder
    # This ensures ALL models get the same rich context (history + memory + rewritten query)
    # Note: RLS context is already set on line 1355, no need to await again
    
    from app.services.context_builder import context_builder
    from app.services.syntra_persona import SYNTRA_SYSTEM_PROMPT, inject_syntra_persona
    
    # Build base system prompt with DAC persona
    base_prompt_messages = [{"role": "system", "content": SYNTRA_SYSTEM_PROMPT}]
    base_prompt_messages = inject_syntra_persona(base_prompt_messages, qa_mode=False, intent=detected_intent, provider=provider_enum.value)

    base_system_prompt = base_prompt_messages[0]["content"] if base_prompt_messages else SYNTRA_SYSTEM_PROMPT
    
    # Use centralized context builder
    # This handles: short-term history + memory + query rewriting
    # Convert attachments to dict format if present
    attachments_dict_streaming = None
    if request.attachments:
        attachments_dict_streaming = [
            {
                "type": a.type,
                "name": a.name,
                "url": a.url,
                "data": a.data,
                "mimeType": a.mimeType
            }
            for a in request.attachments
        ]

    context_result = await context_builder.build_contextual_messages(
        db=db,
        thread_id=thread_id,
        user_id=request.user_id,
        org_id=org_id,
        latest_user_message=rewritten_content,  # Use rewritten content if available
        provider=provider_enum,
        use_memory=request.use_memory if hasattr(request, 'use_memory') else True,
        use_query_rewriter=FEATURE_COREWRITE,
        base_system_prompt=base_system_prompt,
        attachments=attachments_dict_streaming
    )
    
    # Check for disambiguation needed
    if context_result.is_ambiguous and context_result.disambiguation_data:
        # Return disambiguation as SSE event
        async def disambiguation_source():
            clarification_data = {
                'type': 'clarification',
                'question': context_result.disambiguation_data.get('question', 'Which did you mean?'),
                'options': context_result.disambiguation_data.get('options', []),
                'originalMessage': user_content
            }
            yield "event: clarification\n"
            yield f"data: {json.dumps(clarification_data)}\n\n"
            yield "event: done\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
        HEADERS_SSE = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-store, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
        return StreamingResponse(disambiguation_source(), headers=HEADERS_SSE, media_type="text/event-stream")
    
    # Use the messages from context builder
    prompt_messages = context_result.messages
    
    # CRITICAL LOGGING: Log provider call with detailed context info
    # This matches the TypeScript blueprint format for debugging
    logger.info(f"\n{'='*80}")
    logger.info(f"📤 SENDING TO PROVIDER: {provider_enum.value}/{validated_model}")
    logger.info(f"{'='*80}")
    logger.info(f"Using centralized context builder ✓")
    logger.info(f"Total messages: {len(prompt_messages)}")
    logger.info(f"Conversation history turns: {len(context_result.short_term_history)}")
    logger.info(f"Memory snippet present: {context_result.memory_snippet is not None}")
    if context_result.memory_snippet:
        logger.info(f"Memory snippet length: {len(context_result.memory_snippet)} chars")
    logger.info(f"Query rewritten: {context_result.rewritten_query is not None}")
    
    # Detailed messages preview (matches TypeScript blueprint)
    logger.info(f"\nMessages preview (first 120 chars each):")
    for i, msg in enumerate(prompt_messages):
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')
        if isinstance(content, str):
            preview = content[:120]
            logger.info(f"  [{i}] {role}: {preview}{'...' if len(content) > 120 else ''}")
        else:
            logger.info(f"  [{i}] {role}: [non-string content]")
    
    if context_result.rewritten_query:
        logger.info(f"\nRewritten query (first 120 chars): {context_result.rewritten_query[:120]}{'...' if len(context_result.rewritten_query) > 120 else ''}")
    
    logger.info(f"{'='*80}\n")
    
    # NOTE: User message is added to in-memory storage AFTER context building
    # This is correct - we don't want to include the current message in its own history
    # The context builder should see PREVIOUS turns (from prior requests)
    # This will be added later after streaming completes (see background_cleanup)
    
    logger.info(f"⚡ Memory + prompt built in {(perf_time.perf_counter() - start_db)*1000:.0f}ms")
    
    # EXTREME OPTIMIZATION: Skip RLS, get API key from cache/env instead of DB
    # This is the fastest possible path - stream immediately

    # Try to get API key from environment (bypass DB entirely for speed)
    api_key = None
    
    # Check environment variables for API keys (fastest path)
    if provider_enum == ProviderType.OPENAI:
        api_key = os.getenv("OPENAI_API_KEY") or settings.openai_api_key
    elif provider_enum == ProviderType.GEMINI:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or settings.google_api_key
    elif provider_enum == ProviderType.PERPLEXITY:
        api_key = os.getenv("PERPLEXITY_API_KEY") or settings.perplexity_api_key
    elif provider_enum == ProviderType.KIMI:
        api_key = os.getenv("KIMI_API_KEY")  # No fallback in settings yet
    elif provider_enum == ProviderType.OPENROUTER:
        api_key = os.getenv("OPENROUTER_API_KEY") or settings.openrouter_api_key
    
    # If not in env or settings, fall back to DB
    if not api_key:
        logger.warning(f"⚠️  No env var for {provider_enum.value}, fetching from DB...")
        start_wait = perf_time.perf_counter()
        # RLS context is already set on line 1355, just await the API key task
        api_key = await api_key_task
        logger.info(f"⚡ DB fetch done in {(perf_time.perf_counter() - start_wait)*1000:.0f}ms")
    else:
        logger.info(f"⚡ Using cached API key from env for {provider_enum.value}")
        # Don't await RLS if we have API key - it's only needed for DB operations
        # RLS will be set in background cleanup if needed
    
    logger.info(f"⚡ TOTAL SETUP TIME: {(perf_time.perf_counter() - start_routing)*1000:.0f}ms - Starting provider stream NOW...")
    
    # CRITICAL FIX: Save user message to database BEFORE streaming starts
    # This ensures it's available when frontend navigates immediately after stream completes
    # Without this, navigation happens before background_cleanup commits the message
    user_message_saved = False
    try:
        # Check if user message already exists in DB (avoid duplicates)
        user_msg_exists = await db.execute(
            select(Message).where(
                Message.thread_id == thread_id,
                Message.role == MessageRole.USER,
                Message.content == user_content
            ).order_by(Message.created_at.desc()).limit(1)
        )
        existing_user_msg = user_msg_exists.scalar_one_or_none()

        if not existing_user_msg:
            # Save user message to database BEFORE streaming
            message_user_id = current_user.id if current_user else request.user_id
            user_sequence = await _get_next_sequence(db, thread_id)
            user_msg = Message(
                thread_id=thread_id,
                user_id=message_user_id,
                role=MessageRole.USER,
                content=user_content,
                sequence=user_sequence,
            )
            db.add(user_msg)
            await db.commit()  # Commit immediately so it's available for queries
            user_message_saved = True
            logger.info(f"💾✅ Saved user message to database BEFORE streaming (sequence: {user_sequence}, user_id: {message_user_id}, thread_id: {thread_id})")
            # Re-set RLS context after commit since SET LOCAL is transaction-scoped
            user_id = current_user.id if current_user else None
            await set_rls_context(db, org_id, user_id)
            # Verify it was saved
            verify_stmt = select(Message).where(Message.thread_id == thread_id, Message.sequence == user_sequence)
            verify_result = await db.execute(verify_stmt)
            verify_msg = verify_result.scalar_one_or_none()
            if verify_msg:
                logger.info(f"✅✅ Verification: User message confirmed in database (id: {verify_msg.id})")
            else:
                logger.warning(f"❌❌ Verification FAILED: User message NOT found in database after commit!")
        else:
            logger.info(f"ℹ️  User message already exists in database, skipping duplicate save")
            user_message_saved = True
    except Exception as save_error:
        logger.warning(f"⚠️  Failed to save user message to database before streaming: {save_error}")
        import traceback
        logger.info(traceback.format_exc())
        await db.rollback()
        # Continue anyway - background_cleanup will try again
    
    # Start provider streaming IMMEDIATELY (don't wait for DB validation)
    from app.services.provider_dispatch import call_provider_adapter_streaming
    
    async def stream_with_background_validation():
        nonlocal cleanup_task  # Access the cleanup_task variable from outer scope
        # Collect response for memory/observability
        response_content = ""
        usage_data = {}

        # CRITICAL: Save user message to in-memory storage IMMEDIATELY
        # This ensures it's available for the next request even if background task is slow
        # This is essential for follow-up questions to have context
        # CRITICAL: Use threads_store API (write path) - this uses get_or_create_thread safely
        try:
            from app.services.threads_store import add_turn, Turn
            add_turn(thread_id, Turn(role=request.role.value, content=user_content))
            logger.info(f"💾 Added user message to in-memory thread storage IMMEDIATELY (for next request context)")
        except Exception as e:
            logger.warning(f"⚠️  Failed to save user message to in-memory storage: {e}")
            import traceback
            logger.info(traceback.format_exc())

        # Stream directly from provider (THIS STARTS IMMEDIATELY)
        logger.info(f"⚡ Starting provider stream for {provider_enum.value}/{validated_model}...")
        stream_start = perf_time.perf_counter()
        first_chunk = True

        # Send model info to frontend IMMEDIATELY (before any content)
        yield {
            "type": "model_info",
            "provider": provider_enum.value,
            "model": validated_model,
        }

        # If enabled, prepend the transparent routing header as the first visible content.
        # Do NOT append this to `response_content` (keeps stored assistant message clean).
        if routing_header_text:
            yield {"type": "delta", "delta": routing_header_text}
        
        try:
            async for chunk in call_provider_adapter_streaming(
                provider_enum,
                validated_model,
                prompt_messages,
                api_key
            ):
                if first_chunk:
                    logger.info(f"🚀 FIRST CHUNK received in {(perf_time.perf_counter() - stream_start)*1000:.0f}ms from provider!")
                    first_chunk = False
                # Collect content for memory
                if chunk.get("type") == "delta" and "delta" in chunk:
                    response_content += chunk["delta"]
                elif chunk.get("type") == "meta":
                    if "usage" in chunk:
                        usage_data.update(chunk["usage"])
                    finish_reason = chunk.get("finish_reason")
                    if finish_reason and finish_reason == "length":
                        logger.warning(f"⚠️  Provider {provider_enum.value} reported finish_reason=length (likely hit max output tokens)")
                elif chunk.get("type") == "done":
                    if "usage" in chunk and isinstance(chunk["usage"], dict):
                        usage_data.update(chunk["usage"])
                    finish_reason = chunk.get("finish_reason")
                    if finish_reason == "length":
                        # Show the configured completion budget for this provider
                        try:
                            from app.services.provider_dispatch import _completion_budget
                            budget = _completion_budget(provider_enum)
                        except Exception:
                            budget = "unknown"
                        logger.warning(
                            f"⚠️  Provider {provider_enum.value} terminated due to length "
                            f"(response truncated at {len(response_content)} chars, "
                            f"budget={budget})"
                        )
                
                yield chunk
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"❌ Provider adapter error: {e}\n{error_trace}")
            # Yield error chunk so frontend can handle it
            yield {"type": "error", "error": str(e)}
            raise  # Re-raise to be caught by outer handler
        
        # CRITICAL: Save assistant message to in-memory storage IMMEDIATELY after streaming completes
        # This ensures the complete conversation turn is available for the next request
        # Do this BEFORE background cleanup to ensure it's available ASAP
        # CRITICAL: Use threads_store API (write path) - this uses get_or_create_thread safely
        try:
            if response_content:
                from app.services.threads_store import add_turn, Turn
                add_turn(thread_id, Turn(role="assistant", content=response_content))
                logger.info(f"💾 Added assistant message to in-memory thread storage IMMEDIATELY (for next request context)")
        except Exception as e:
            logger.warning(f"⚠️  Failed to save assistant message to in-memory storage: {e}")
            import traceback
            logger.info(traceback.format_exc())
        
        # Post-stream: Background validation and logging (non-blocking)
        async def background_cleanup():
            try:
                # Now do DB validation (non-blocking for streaming)
                # Note: user_id not available in background task, but thread access already validated
                thread = await _get_thread(db, thread_id, org_id, None)
                org = await _get_org(db, org_id)
                request_limit = org.requests_per_day or settings.default_requests_per_day
                token_limit = org.tokens_per_day or settings.default_tokens_per_day

                # Persist transparent routing preference (if explicitly set), and honor user "hide routing" requests.
                try:
                    from app.services.routing_header import user_requested_hide_routing
                    thread_settings = thread.settings or {}
                    if request.transparent_routing is not None:
                        thread_settings["transparent_routing"] = bool(request.transparent_routing)
                    if user_requested_hide_routing(user_content):
                        thread_settings["transparent_routing"] = False
                    thread.settings = thread_settings
                except Exception:
                    pass

                # CRITICAL: Save messages to database for persistence
                # This ensures messages survive server restarts and can be loaded later
                # NOTE: User message is already saved before streaming starts (see above)
                # This check is just for safety in case the pre-stream save failed
                try:
                    # Check if user message already exists in DB
                    user_msg_exists = await db.execute(
                        select(Message).where(
                            Message.thread_id == thread_id,
                            Message.role == MessageRole.USER,
                            Message.content == user_content
                        ).order_by(Message.created_at.desc()).limit(1)
                    )
                    existing_user_msg = user_msg_exists.scalar_one_or_none()

                    if not existing_user_msg:
                        # Save user message to database (fallback - should already be saved before streaming)
                        # CRITICAL: Use authenticated user's ID from JWT, fallback to request.user_id
                        message_user_id = current_user.id if current_user else request.user_id
                        user_sequence = await _get_next_sequence(db, thread_id)
                        user_msg = Message(
                            thread_id=thread_id,
                            user_id=message_user_id,
                            role=MessageRole.USER,
                            content=user_content,
                            sequence=user_sequence,
                        )
                        db.add(user_msg)
                        logger.info(f"💾 Saved user message to database in background_cleanup (fallback, sequence: {user_sequence}, user_id: {message_user_id})")
                    else:
                        logger.info(f"ℹ️  User message already exists in database (saved before streaming)")

                    # Save assistant message to database if we have content
                    if response_content:
                        # CRITICAL: Use authenticated user's ID from JWT, fallback to request.user_id
                        message_user_id = current_user.id if current_user else request.user_id
                        assistant_sequence = await _get_next_sequence(db, thread_id)
                        assistant_msg = Message(
                            thread_id=thread_id,
                            user_id=message_user_id,
                            role=MessageRole.ASSISTANT,
                            content=response_content,
                            sequence=assistant_sequence,
                            provider=provider_enum.value,
                            model=validated_model,
                            prompt_tokens=usage_data.get("input_tokens"),
                            completion_tokens=usage_data.get("output_tokens"),
                            meta={
                                "provider": provider_enum.value,
                                "model": validated_model,
                                "reason": reason,
                            }
                        )
                        db.add(assistant_msg)
                        logger.info(f"💾 Saved assistant message to database (sequence: {assistant_sequence}, user_id: {message_user_id})")

                    # Commit both messages to database
                    await db.commit()
                    logger.info(f"✅ Messages persisted to database for thread {thread_id}")
                    # Re-set RLS context after commit since SET LOCAL is transaction-scoped
                    user_id = current_user.id if current_user else None
                    await set_rls_context(db, org_id, user_id)

                except Exception as save_error:
                    logger.warning(f"⚠️  Failed to save messages to database: {save_error}")
                    import traceback
                    logger.info(traceback.format_exc())
                    await db.rollback()

                # Auto-generate title if this is the first message
                message_count = await db.execute(
                    select(func.count(Message.id)).where(Message.thread_id == thread_id)
                )
                count = message_count.scalar() or 0
                if should_auto_title(thread.title, count):
                    thread.title = generate_thread_title(user_content)
                    await db.commit()
                    # Re-set RLS context after commit since SET LOCAL is transaction-scoped
                    user_id = current_user.id if current_user else None
                    await set_rls_context(db, org_id, user_id)

                # Load messages for next time (sync DB to in-memory if needed)
                prior_messages = await _get_recent_messages(db, thread_id)
                if prior_messages:
                    db_messages = [
                        {"role": msg.role.value, "content": msg.content}
                        for msg in prior_messages
                    ]
                    # Only sync if in-memory is empty (don't overwrite existing turns)
                    from app.services.threads_store import get_thread, add_turn, Turn
                    thread_mem = get_thread(thread_id)
                    # Only sync if thread doesn't exist or has no turns (don't overwrite existing turns)
                    if thread_mem is None or not thread_mem.turns:
                        # Sync DB messages to in-memory storage
                        for msg in prior_messages:
                            add_turn(thread_id, Turn(role=msg.role.value, content=msg.content))
                        logger.info(f"💾 Synced DB messages to in-memory storage ({len(prior_messages)} messages)")
                
                # Log observability
                from app.services.token_track import normalize_usage
                from app.services.observability import log_turn
                usage = normalize_usage(usage_data, provider_enum.value)
                latency_ms = int((perf_time.perf_counter() - stream_start) * 1000)
                await log_turn(
                    thread_id=thread_id,
                    turn_id=str(uuid.uuid4()),
                    intent="auto",
                    router_decision={"provider": provider_enum.value, "model": validated_model, "reason": reason},
                    provider=provider_enum.value,
                    model=validated_model,
                    latency_ms=latency_ms,
                    input_tokens=usage.get("input_tokens"),
                    output_tokens=usage.get("output_tokens"),
                    cost_est=usage.get("cost_est", 0.0),
                    cache_hit=False,
                    fallback_used=False,
                    safety_flags={
                        "has_pii": safety_flags.has_pii,
                        "pii_types": safety_flags.pii_types,
                        "prompt_injection_risk": safety_flags.prompt_injection_risk,
                    },
                    truncated=usage.get("truncated", False),
                )
                
                # Log router run for dynamic routing analytics (if router decision exists)
                if router_decision:
                    try:
                        router_run = RouterRun(
                            user_id=request.user_id,
                            session_id=thread_id,
                            thread_id=thread_id,
                            task_type=router_decision.intent.task_type,
                            requires_web=router_decision.intent.requires_web,
                            requires_tools=router_decision.intent.requires_tools,
                            priority=router_decision.intent.priority,
                            estimated_input_tokens=router_decision.intent.estimated_input_tokens,
                            chosen_model_id=router_decision.chosen_model.id,
                            chosen_provider=router_decision.chosen_model.provider.value,
                            chosen_provider_model=router_decision.chosen_model.provider_model,
                            scores_json=router_decision.scores,
                            latency_ms=latency_ms,
                            input_tokens=usage.get("input_tokens"),
                            output_tokens=usage.get("output_tokens"),
                            estimated_cost=usage.get("cost_est", 0.0),
                        )
                        db.add(router_run)
                        await db.commit()
                        logger.info(f"📊 Logged router run: {router_decision.chosen_model.display_name} (task: {router_decision.intent.task_type})")
                    except Exception as router_log_error:
                        logger.warning(f"⚠️  Failed to log router run: {router_log_error}")
                        import traceback
                        logger.info(traceback.format_exc())
                        await db.rollback()
            except Exception as e:
                # Log but don't fail - streaming already completed
                logger.error(f"Background cleanup error: {e}")
        
        # Run cleanup but track it so we can ensure it completes
        # This will be awaited by event_source() after streaming ends
        cleanup_task = asyncio.create_task(background_cleanup())  # noqa: This uses nonlocal cleanup_task
        # Store task reference to allow frontend to verify persistence if needed
        logger.info(f"📝 Background cleanup task created for thread {thread_id}")

    # Return streaming response immediately (starts streaming ASAP)
    cleanup_task = None  # Will be set by stream_with_background_validation

    async def event_source():
        nonlocal cleanup_task
        start = time.perf_counter()
        ttft_emitted = False

        # Early heartbeat to open the pipe immediately
        yield "event: ping\ndata: {}\n\n"

        # Emit router decision immediately so UI can show provider badge
        # CRITICAL: Include thread_id in router event so frontend can maintain conversation continuity
        router_data = {
            'provider': provider_enum.value,
            'model': validated_model,
            'reason': reason,
            'thread_id': thread_id  # CRITICAL: Frontend needs this to reuse thread for follow-up messages
        }
        yield f"event: router\n"
        yield f"data: {json.dumps(router_data)}\n\n"

        try:
            async for chunk in stream_with_background_validation():
                chunk_type = chunk.get("type", "delta")

                if chunk_type == "model_info":
                    # Send model information to frontend immediately
                    yield f"event: model_info\n"
                    yield f"data: {json.dumps(chunk)}\n\n"
                elif chunk_type == "meta":
                    if "ttft_ms" in chunk and not ttft_emitted:
                        ttft_emitted = True
                    yield f"event: meta\n"
                    yield f"data: {json.dumps(chunk)}\n\n"
                elif chunk_type == "delta":
                    if not ttft_emitted:
                        ttft_ms = int((time.perf_counter() - start) * 1000)
                        yield f"event: meta\n"
                        yield f"data: {json.dumps({'type': 'meta', 'ttft_ms': ttft_ms})}\n\n"
                        ttft_emitted = True
                    yield f"event: delta\n"
                    yield f"data: {json.dumps(chunk)}\n\n"
                elif chunk_type == "done":
                    yield f"event: done\n"
                    yield f"data: {json.dumps(chunk)}\n\n"
                    
                    # Generate media if requested (after text response completes)
                    if should_generate_media and media_metadata:
                        try:
                            if media_intent == "image":
                                # Generate image
                                prompt = media_metadata.get("prompt", user_content)
                                
                                # Log prompt being used
                                logger.info(f"📝 Image generation prompt: '{prompt[:200]}...'")
                                
                                # Get API keys for image generation
                                api_keys_dict = {}
                                
                                # Try to get key from current provider first
                                if provider_enum == ProviderType.GEMINI and api_key:
                                    api_keys_dict["gemini"] = api_key
                                    api_keys_dict["google"] = api_key  # Alias
                                elif provider_enum == ProviderType.OPENAI and api_key:
                                    api_keys_dict["openai"] = api_key
                                
                                # Fallback to settings/env - prioritize Gemini
                                from app.config import get_settings
                                settings = get_settings()
                                
                                if "gemini" not in api_keys_dict and settings.google_api_key:
                                    api_keys_dict["gemini"] = settings.google_api_key
                                    api_keys_dict["google"] = settings.google_api_key
                                
                                if "openai" not in api_keys_dict and settings.openai_api_key:
                                    api_keys_dict["openai"] = settings.openai_api_key
                                
                                # Also try to get from DB if available
                                if org_id:
                                    try:
                                        from app.services.provider_keys import get_api_key_for_org
                                        # RLS context is already set at the start of the request (line 1355)
                                        
                                        # Try Gemini first
                                        if "gemini" not in api_keys_dict:
                                            gemini_key = await get_api_key_for_org(db, org_id, ProviderType.GEMINI)
                                            if gemini_key:
                                                api_keys_dict["gemini"] = gemini_key
                                                api_keys_dict["google"] = gemini_key
                                        
                                        # Then OpenAI
                                        if "openai" not in api_keys_dict:
                                            openai_key = await get_api_key_for_org(db, org_id, ProviderType.OPENAI)
                                            if openai_key:
                                                api_keys_dict["openai"] = openai_key
                                    except Exception:
                                        pass  # Ignore errors, continue with what we have
                                
                                # Check if we have any image generation provider
                                from app.services.collaborate.image_generation_service import select_image_provider
                                selected_provider, selected_key = select_image_provider(api_keys_dict)
                                
                                logger.debug(f"🔍 Image generation check - Provider: {selected_provider}, Has key: {bool(selected_key)}, Available keys: {list(api_keys_dict.keys())}")
                                
                                if selected_provider and selected_key:
                                    logger.info(f"🎨 Generating image with {selected_provider} using prompt: '{prompt}'")
                                    # Create a temporary API keys dict with just the selected provider
                                    temp_api_keys = {selected_provider: selected_key}
                                    
                                    try:
                                        generated_image = await media_generation_service.generate_image_from_prompt(
                                            prompt, temp_api_keys
                                        )
                                        
                                        if generated_image:
                                            # Send image as SSE event
                                            image_data = {
                                                "type": "image",
                                                "url": generated_image.url,
                                                "alt": generated_image.alt or prompt[:100],
                                                "mime_type": generated_image.mime_type or "image/png"
                                            }
                                            yield f"event: media\n"
                                            yield f"data: {json.dumps(image_data)}\n\n"
                                            logger.info(f"✅ Image generated and sent to client: {generated_image.url[:100] if len(generated_image.url) > 100 else generated_image.url}")
                                        else:
                                            logger.warning(f"⚠️  Image generation returned no result (generated_image is None)")
                                    except Exception as img_gen_error:
                                        import traceback
                                        logger.error(f"❌ Image generation error: {img_gen_error}")
                                        logger.info(traceback.format_exc())
                                else:
                                    logger.warning(f"⚠️  No image generation provider available. Available providers: {list(api_keys_dict.keys())}")
                                    
                            elif media_intent == "graph":
                                # Generate graph
                                graph_request = media_metadata.get("request", user_content)
                                logger.info(f"📊 Generating graph from request: {graph_request[:100]}...")
                                
                                graph_data_uri = await media_generation_service.generate_graph_from_request(
                                    graph_request
                                )
                                
                                if graph_data_uri:
                                    # Send graph as SSE event
                                    graph_data = {
                                        "type": "graph",
                                        "url": graph_data_uri,
                                        "alt": f"Graph visualization: {graph_request[:100]}",
                                        "mime_type": "image/png"
                                    }
                                    yield f"event: media\n"
                                    yield f"data: {json.dumps(graph_data)}\n\n"
                                    logger.info(f"✅ Graph generated and sent to client")
                                else:
                                    logger.warning(f"⚠️  Graph generation returned no result")
                        except Exception as media_error:
                            import traceback
                            logger.warning(f"⚠️  Media generation error: {media_error}")
                            logger.info(traceback.format_exc())
                            # Don't fail the request if media generation fails
                            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"❌ Streaming error: {e}\n{error_trace}")
            yield f"event: error\n"
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

        # CRITICAL FIX: Wait for database persistence before stream ends
        # This prevents chat history from being empty when user navigates away during generation
        if cleanup_task:
            try:
                logger.info(f"⏳ Waiting for database persistence (cleanup task)...")
                await cleanup_task
                logger.info(f"✅ Database persistence confirmed for thread {thread_id}")
                # Emit final "persisted" event so frontend knows messages are safe in database
                yield "event: persisted\n"
                yield f"data: {json.dumps({'type': 'persisted', 'thread_id': thread_id})}\n\n"
            except Exception as e:
                logger.warning(f"⚠️  Cleanup task error: {e}")
                # Still emit persisted event - cleanup may have partially succeeded
                yield "event: persisted\n"
                yield f"data: {json.dumps({'type': 'persisted', 'thread_id': thread_id, 'error': str(e)})}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")


async def get_thread_audit(
    thread_id: str,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Return the latest audit entries for a thread."""
    user_id = current_user.id if current_user else None
    await set_rls_context(db, org_id, user_id)
    await _get_thread(db, thread_id, org_id, user_id)

    stmt = (
        select(AuditLog)
        .where(AuditLog.thread_id == thread_id)
        .order_by(AuditLog.created_at.desc())
        .limit(25)
    )
    result = await db.execute(stmt)
    entries = result.scalars().all()

    return [
        AuditEntry(
            id=entry.id,
            provider=entry.provider,
            model=entry.model,
            reason=entry.reason,
            scope=entry.scope,
            package_hash=entry.package_hash,
            response_hash=entry.response_hash,
            prompt_tokens=entry.prompt_tokens,
            completion_tokens=entry.completion_tokens,
            total_tokens=entry.total_tokens,
            created_at=entry.created_at,
        )
        for entry in entries
    ]


@router.post("/cancel/{request_id}")
async def cancel_request(request_id: str, org_id: str = Depends(require_org_id)):
    """Cancel an ongoing streaming request."""
    cancelled = cancellation_registry.cancel(request_id)
    if cancelled:
        return {"status": "cancelled", "request_id": request_id}
    else:
        return {"status": "not_found", "request_id": request_id, "message": "Request not found or already completed"}


async def _get_thread(db: AsyncSession, thread_id: str, org_id: str, user_id: Optional[str] = None) -> Thread:
    stmt = select(Thread).where(
        Thread.id == thread_id,
        Thread.org_id == org_id,
    )
    # CRITICAL FIX: Filter by creator_id to prevent cross-user data access
    if user_id:
        stmt = stmt.where(Thread.creator_id == user_id)
    
    result = await db.execute(stmt)
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thread {thread_id} not found",
        )
    return thread


async def _get_org(db: AsyncSession, org_id: str) -> Org:
    stmt = select(Org).where(Org.id == org_id)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Org {org_id} not found",
        )
    return org


async def _get_recent_messages(db: AsyncSession, thread_id: str) -> List[Message]:
    stmt = (
        select(Message)
        .where(Message.thread_id == thread_id)
        .order_by(Message.sequence.desc())
        .limit(MAX_CONTEXT_MESSAGES)
    )
    result = await db.execute(stmt)
    records = list(result.scalars().all())
    records.reverse()
    return records


async def _get_next_sequence(db: AsyncSession, thread_id: str) -> int:
    stmt = select(func.max(Message.sequence)).where(Message.thread_id == thread_id)
    result = await db.execute(stmt)
    max_sequence = result.scalar()
    return (max_sequence or -1) + 1


def _package_hash(messages: List[Dict[str, str]], request: AddMessageRequest) -> str:
    payload = {
        "messages": messages,
        "router": {
            "provider": request.provider.value if request.provider else None,
            "model": request.model,
            "reason": request.reason,
        },
        "scope": request.scope.value if request.scope else None,
    }
    serialized = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _response_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _to_message_response(message: Message, hide_provider: bool = False) -> MessageResponse:
    """
    Convert Message to MessageResponse.

    Args:
        message: Message model
        hide_provider: If True, hide provider/model info to maintain DAC persona

    Returns:
        MessageResponse with optionally hidden provider info
    """
    return MessageResponse(
        id=message.id,
        role=message.role.value,
        content=message.content,
        provider=None if hide_provider else message.provider,
        model=None if hide_provider else message.model,
        sequence=message.sequence,
        created_at=message.created_at,
        citations=message.citations,
        meta=message.meta,
    )


# ============== COLLABORATE STREAMING (SSE) ==============

@router.post("/{thread_id}/collaborate-stream")
async def collaborate_thread_streaming(
    thread_id: str,
    body: CollaborateRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Run collaborate mode with streaming events (Server-Sent Events).

    Emits real-time events as the pipeline progresses:
    - stage_start, stage_delta, stage_end
    - council_progress
    - final_answer_delta, final_answer_end
    - error (if something fails)

    Frontend receives these events and animates the thinking UI in real-time.
    """
    # Set RLS context
    await set_rls_context(db, org_id)

    # Import collaborate service
    from app.services.collaborate.streaming import run_collaborate_streaming
    from app.services.collaborate.models import ModelInfo

    # Validate thread exists
    result = await db.execute(select(Thread).where(Thread.id == thread_id, Thread.org_id == org_id))
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Model configuration (same as non-streaming endpoint)
    inner_models = {
        "analyst": ModelInfo(
            provider="google",
            model_slug="gemini-2.0-pro-exp-02-05",
            display_name="Gemini 2.0 Pro (Analyst)",
        ),
        "researcher": ModelInfo(
            provider="perplexity",
            model_slug="sonar-reasoning",
            display_name="Perplexity Sonar (Researcher)",
        ),
        "creator": ModelInfo(
            provider="openai",
            model_slug="gpt-4o-mini",
            display_name="GPT-4o Mini (Creator)",
        ),
        "critic": ModelInfo(
            provider="kimi",
            model_slug="moonshot-v1-8k",
            display_name="Kimi K1 (Critic)",
        ),
        "internal_synth": ModelInfo(
            provider="openai",
            model_slug="gpt-4o",
            display_name="GPT-4o (Internal Synth)",
        ),
    }

    compression_model = ModelInfo(
        provider="openrouter",
        model_slug="deepseek/deepseek-chat",
        display_name="DeepSeek Chat (Compression)",
    )

    council_models = {
        "perplexity": ModelInfo(
            provider="perplexity",
            model_slug="sonar-reasoning",
            display_name="Perplexity Sonar",
        ),
        "gemini": ModelInfo(
            provider="google",
            model_slug="gemini-2.0-pro-exp-02-05",
            display_name="Gemini 2.0 Pro",
        ),
        "gpt": ModelInfo(
            provider="openai",
            model_slug="gpt-4o",
            display_name="GPT-4o",
        ),
        "kimi": ModelInfo(
            provider="kimi",
            model_slug="moonshot-v1-8k",
            display_name="Kimi K1",
        ),
        "openrouter": ModelInfo(
            provider="openrouter",
            model_slug="deepseek/deepseek-chat",
            display_name="DeepSeek Chat",
        ),
    }

    director_model = ModelInfo(
        provider="openai",
        model_slug="gpt-4o",
        display_name="GPT-4o (Director)",
    )

    # Collect API keys for all providers
    api_keys: Dict[str, str] = {}
    for provider in ["openai", "google", "perplexity", "kimi", "openrouter"]:
        try:
            provider_type = {
                "openai": ProviderType.OPENAI,
                "google": ProviderType.GEMINI,
                "perplexity": ProviderType.PERPLEXITY,
                "kimi": ProviderType.KIMI,
                "openrouter": ProviderType.OPENROUTER,
            }.get(provider)
            if provider_type:
                key = await get_api_key_for_org(db, org_id, provider_type)
                if key:
                    api_keys[provider] = key
        except Exception as e:
            logger.info(f"Could not get API key for {provider}: {e}")
            continue

    if not api_keys:
        raise HTTPException(
            status_code=500,
            detail="No API keys configured for organization",
        )

    # Return SSE stream
    async def event_generator():
        try:
            async for event in run_collaborate_streaming(
                user_query=body.message,
                mode=body.mode,
                inner_models=inner_models,
                compression_model=compression_model,
                council_models=council_models,
                director_model=director_model,
                api_keys=api_keys,
            ):
                yield event
        except Exception as e:
            # Emit error event on failure
            error_event = {
                "type": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/cancel/{request_id}")
async def cancel_request(request_id: str, org_id: str = Depends(require_org_id)):
    """Cancel an ongoing streaming request."""
    cancelled = cancellation_registry.cancel(request_id)
    if cancelled:
        return {"status": "cancelled", "request_id": request_id}
    else:
        return {"status": "not_found", "request_id": request_id, "message": "Request not found or already completed"}


@router.post("/{thread_id}/forward")
async def forward_thread(thread_id: str, db: AsyncSession = Depends(get_db)):
    """Forward thread to another provider."""
    # TODO: Implement in Phase 2
    return {"message": "Forward thread - to be implemented"}


# ============== COLLABORATE (LLM Council) ==============

class CollaborateRequest(BaseModel):
    """Request for collaborate mode."""
    message: str = Field(..., description="User's message or question")
    mode: str = Field(default="auto", description="'auto' or 'manual'")


@router.post("/{thread_id}/collaborate")
async def collaborate_thread(
    thread_id: str,
    body: CollaborateRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Run collaborate mode: multi-stage inner team + LLM council + director.

    Returns CollaborateResponse with:
    - final_answer: Director's synthesized response
    - internal_pipeline: Analyst → Researcher → Creator → Critic → Internal Synth
    - external_reviews: Council reviews from 5+ models
    - meta: Run metadata
    """
    # Set RLS context
    await set_rls_context(db, org_id)

    # Import collaborate service
    from app.services.collaborate import run_collaborate
    from app.services.collaborate.models import ModelInfo

    # Validate thread exists
    result = await db.execute(select(Thread).where(Thread.id == thread_id, Thread.org_id == org_id))
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # TODO: Load model configuration from org settings or use defaults
    # For now, use a sensible default configuration
    inner_models = {
        "analyst": ModelInfo(
            provider="google",
            model_slug="gemini-2.0-pro-exp-02-05",
            display_name="Gemini 2.0 Pro (Analyst)",
        ),
        "researcher": ModelInfo(
            provider="perplexity",
            model_slug="sonar-reasoning",
            display_name="Perplexity Sonar (Researcher)",
        ),
        "creator": ModelInfo(
            provider="openai",
            model_slug="gpt-4o-mini",
            display_name="GPT-4o Mini (Creator)",
        ),
        "critic": ModelInfo(
            provider="kimi",
            model_slug="moonshot-v1-8k",
            display_name="Kimi K1 (Critic)",
        ),
        "internal_synth": ModelInfo(
            provider="openai",
            model_slug="gpt-4o",
            display_name="GPT-4o (Internal Synth)",
        ),
    }

    compression_model = ModelInfo(
        provider="openrouter",
        model_slug="deepseek/deepseek-chat",
        display_name="DeepSeek Chat (Compression)",
    )

    council_models = {
        "perplexity": ModelInfo(
            provider="perplexity",
            model_slug="sonar-reasoning",
            display_name="Perplexity Sonar",
        ),
        "gemini": ModelInfo(
            provider="google",
            model_slug="gemini-2.0-pro-exp-02-05",
            display_name="Gemini 2.0 Pro",
        ),
        "gpt": ModelInfo(
            provider="openai",
            model_slug="gpt-4o",
            display_name="GPT-4o",
        ),
        "kimi": ModelInfo(
            provider="kimi",
            model_slug="moonshot-v1-8k",
            display_name="Kimi K1",
        ),
        "openrouter": ModelInfo(
            provider="openrouter",
            model_slug="deepseek/deepseek-chat",
            display_name="DeepSeek Chat",
        ),
    }

    director_model = ModelInfo(
        provider="openai",
        model_slug="gpt-4o",
        display_name="GPT-4o (Director)",
    )

    # Collect API keys for all providers
    api_keys: Dict[str, str] = {}
    for provider in ["openai", "google", "perplexity", "kimi", "openrouter"]:
        try:
            provider_type = {
                "openai": ProviderType.OPENAI,
                "google": ProviderType.GEMINI,
                "perplexity": ProviderType.PERPLEXITY,
                "kimi": ProviderType.KIMI,
                "openrouter": ProviderType.OPENROUTER,
            }.get(provider)
            if provider_type:
                key = await get_api_key_for_org(db, org_id, provider_type)
                if key:
                    api_keys[provider] = key
        except Exception as e:
            logger.info(f"Could not get API key for {provider}: {e}")
            continue

    if not api_keys:
        raise HTTPException(
            status_code=500,
            detail="No API keys configured for organization",
        )

    try:
        # Run the collaborate pipeline
        collaborate_response = await run_collaborate(
            user_query=body.message,
            mode=body.mode,
            inner_models=inner_models,
            compression_model=compression_model,
            council_models=council_models,
            director_model=director_model,
            api_keys=api_keys,
        )

        return collaborate_response

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Collaborate pipeline failed: {str(e)}",
        )


@router.get("/{thread_id}", response_model=ThreadDetailResponse)
async def get_thread(
    thread_id: str,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Get thread details with messages."""
    user_id = current_user.id if current_user else None
    await set_rls_context(db, org_id, user_id)

    # Get thread with messages - filter by creator_id if user is authenticated
    stmt = select(Thread).where(
        Thread.id == thread_id,
        Thread.org_id == org_id
    )
    if user_id:
        stmt = stmt.where(Thread.creator_id == user_id)
    
    result = await db.execute(stmt)
    thread = result.scalar_one_or_none()

    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thread {thread_id} not found"
        )

    # Get messages
    stmt = select(Message).where(Message.thread_id == thread_id).order_by(Message.sequence)
    result = await db.execute(stmt)
    messages = result.scalars().all()

    # Debug: Log message retrieval with detailed info
    logger.debug(f"🔍 DEBUG get_thread: thread_id={thread_id}, org_id={org_id}, user_id={user_id}, messages_retrieved={len(messages)}")
    if messages:
        for msg in messages:
            logger.info(f"  📨 Message: role={msg.role.value}, sequence={msg.sequence}, content_length={len(msg.content) if msg.content else 0}")
    if len(messages) == 0:
        # Try to debug why no messages are found
        # Check if there are ANY messages in this thread at all (without RLS filtering)
        count_stmt = select(func.count(Message.id)).where(Message.thread_id == thread_id)
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar() or 0
        logger.warning(f"⚠️  No messages retrieved but total_count in DB: {total_count}")
        if total_count > 0:
            # Try to get messages without sequence ordering to see what's there
            all_msgs_stmt = select(Message).where(Message.thread_id == thread_id)
            all_msgs_result = await db.execute(all_msgs_stmt)
            all_msgs = all_msgs_result.scalars().all()
            logger.warning(f"⚠️  Found {len(all_msgs)} messages without ordering:")
            for msg in all_msgs:
                logger.info(f"    - role={msg.role.value}, sequence={msg.sequence}, created_at={msg.created_at}")

    return ThreadDetailResponse(
        id=thread.id,
        org_id=thread.org_id,
        title=thread.title,
        description=thread.description,
        last_provider=None,  # Hide provider info
        last_model=None,  # Hide model info
        created_at=thread.created_at,
        messages=[_to_message_response(msg, hide_provider=False) for msg in messages]
    )


@router.get("/{thread_id}/audit", response_model=List[AuditEntry])
async def get_thread_audit(
    thread_id: str,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Return the latest audit entries for a thread."""
    user_id = current_user.id if current_user else None
    await set_rls_context(db, org_id, user_id)
    await _get_thread(db, thread_id, org_id, user_id)

    stmt = (
        select(AuditLog)
        .where(AuditLog.thread_id == thread_id)
        .order_by(AuditLog.created_at.desc())
        .limit(25)
    )
    result = await db.execute(stmt)
    entries = result.scalars().all()

    return [
        AuditEntry(
            id=entry.id,
            provider=entry.provider,
            model=entry.model,
            reason=entry.reason,
            scope=entry.scope,
            package_hash=entry.package_hash,
            response_hash=entry.response_hash,
            prompt_tokens=entry.prompt_tokens,
            completion_tokens=entry.completion_tokens,
            total_tokens=entry.total_tokens,
            created_at=entry.created_at,
        )
        for entry in entries
    ]


@router.post("/cancel/{request_id}")
async def cancel_request(request_id: str, org_id: str = Depends(require_org_id)):
    """Cancel an ongoing streaming request."""
    cancelled = cancellation_registry.cancel(request_id)
    if cancelled:
        return {"status": "cancelled", "request_id": request_id}
    else:
        return {"status": "not_found", "request_id": request_id, "message": "Request not found or already completed"}


async def _get_thread(db: AsyncSession, thread_id: str, org_id: str, user_id: Optional[str] = None) -> Thread:
    stmt = select(Thread).where(
        Thread.id == thread_id,
        Thread.org_id == org_id,
    )
    # CRITICAL FIX: Filter by creator_id to prevent cross-user data access
    if user_id:
        stmt = stmt.where(Thread.creator_id == user_id)
    
    result = await db.execute(stmt)
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thread {thread_id} not found",
        )
    return thread


async def _get_org(db: AsyncSession, org_id: str) -> Org:
    stmt = select(Org).where(Org.id == org_id)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Org {org_id} not found",
        )
    return org


async def _get_recent_messages(db: AsyncSession, thread_id: str) -> List[Message]:
    stmt = (
        select(Message)
        .where(Message.thread_id == thread_id)
        .order_by(Message.sequence.desc())
        .limit(MAX_CONTEXT_MESSAGES)
    )
    result = await db.execute(stmt)
    records = list(result.scalars().all())
    records.reverse()
    return records


async def _get_next_sequence(db: AsyncSession, thread_id: str) -> int:
    stmt = select(func.max(Message.sequence)).where(Message.thread_id == thread_id)
    result = await db.execute(stmt)
    max_sequence = result.scalar()
    return (max_sequence or -1) + 1


def _package_hash(messages: List[Dict[str, str]], request: AddMessageRequest) -> str:
    payload = {
        "messages": messages,
        "router": {
            "provider": request.provider.value if request.provider else None,
            "model": request.model,
            "reason": request.reason,
        },
        "scope": request.scope.value if request.scope else None,
    }
    serialized = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _response_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _to_message_response(message: Message, hide_provider: bool = False) -> MessageResponse:
    """
    Convert Message to MessageResponse.

    Args:
        message: Message model
        hide_provider: If True, hide provider/model info to maintain DAC persona

    Returns:
        MessageResponse with optionally hidden provider info
    """
    return MessageResponse(
        id=message.id,
        role=message.role.value,
        content=message.content,
        provider=None if hide_provider else message.provider,
        model=None if hide_provider else message.model,
        sequence=message.sequence,
        created_at=message.created_at,
        citations=message.citations,
        meta=message.meta,
    )


@router.post("/{thread_id}/forward")
async def forward_thread(thread_id: str, db: AsyncSession = Depends(get_db)):
    """Forward thread to another provider."""
    # TODO: Implement in Phase 2
    return {"message": "Forward thread - to be implemented"}


# ============== COLLABORATE (LLM Council) ==============

class CollaborateRequest(BaseModel):
    """Request for collaborate mode."""
    message: str = Field(..., description="User's message or question")
    mode: str = Field(default="auto", description="'auto' or 'manual'")


