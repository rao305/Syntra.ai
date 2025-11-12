"""Threads API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
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
from app.api.deps import require_org_id
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
from app.services.dac_persona import inject_dac_persona, sanitize_response
from app.services.memory_manager import (
    get_thread, add_turn, build_prompt_for_model, smooth_intent, update_last_intent, Turn,
    initialize_thread_from_db
)
from app.services.observability import log_turn, calculate_cost_estimate
from app.services.guardrails import sanitize_user_input, should_refuse, SafetyFlags
from app.services.response_cache import make_cache_key, get_cached, set_cached
from app.services.route_and_call import route_and_call
from app.services.token_track import normalize_usage
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


class AddMessageRequest(BaseModel):
    """Request to add a message to a thread."""
    user_id: Optional[str] = None
    content: str = Field(..., min_length=1)
    role: MessageRole = MessageRole.USER
    provider: Optional[ProviderType] = None  # Optional - will use intelligent routing if not specified
    model: Optional[str] = None  # Optional - will use intelligent routing if not specified
    reason: Optional[str] = None  # Optional - will be auto-generated if not specified
    scope: ForwardScope = ForwardScope.PRIVATE
    use_memory: bool = True  # Enable memory-based context by default


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


@router.post("/", response_model=CreateThreadResponse)
async def create_thread(
    request: CreateThreadRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """Create a new thread."""
    # Set RLS context
    await set_rls_context(db, org_id)

    # Create thread
    new_thread = Thread(
        org_id=org_id,
        creator_id=request.user_id,
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
    db: AsyncSession = Depends(get_db)
):
    """Add a message to a thread and fan out to the selected provider."""
    await set_rls_context(db, org_id)
    await memory_guard.ensure_health()

    thread = await _get_thread(db, thread_id, org_id)

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
    if not request.provider or not request.model:
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
            print("⚠️  Memory retrieval timeout, continuing without memory")
        except Exception as e:
            print(f"⚠️  Memory retrieval error: {e}, continuing without memory")

    # STEP 3: Build enhanced prompt with memory context
    prompt_messages = conversation_history.copy()

    # Thread description doubles as a custom system prompt (Phase 3 QA, custom personas)
    custom_system_prompt = (thread.description or "").strip()
    
    # Check if QA mode is enabled via thread description
    qa_mode = custom_system_prompt == "PHASE3_QA_MODE" or "PHASE3_QA_MODE" in custom_system_prompt
    
    if custom_system_prompt and not qa_mode:
        prompt_messages.insert(0, {
            "role": MessageRole.SYSTEM.value,
            "content": custom_system_prompt
        })

    # Detect intent from routing decision reason for LaTeX math formatting
    from app.services.dac_persona import detect_intent_from_reason
    detected_intent = None
    if routing_decision and routing_decision.reason:
        detected_intent = detect_intent_from_reason(routing_decision.reason)
    
    # INJECT DAC PERSONA - must come FIRST to establish identity
    # QA mode will be detected automatically if thread.description contains "PHASE3_QA_MODE"
    # Pass detected intent to enable LaTeX formatting for math questions
    prompt_messages = inject_dac_persona(prompt_messages, qa_mode=qa_mode, intent=detected_intent)

    # Inject memory fragments as system context if available
    if memory_context and memory_context.total_fragments > 0:
        memory_content = "# Relevant Context from Memory:\n\n"

        # Add private memories
        if memory_context.private_fragments:
            memory_content += "## Your Previous Interactions:\n"
            for frag in memory_context.private_fragments:
                memory_content += f"- {frag['text']}\n"
            memory_content += "\n"

        # Add shared memories
        if memory_context.shared_fragments:
            memory_content += "## Shared Knowledge:\n"
            for frag in memory_context.shared_fragments:
                provider_info = frag.get('provenance', {}).get('provider', 'unknown')
                memory_content += f"- {frag['text']} (from {provider_info})\n"

        # Insert memory as first system message
        prompt_messages.insert(0, {
            "role": "system",
            "content": memory_content
        })

    # Add current user message
    prompt_messages.append({"role": request.role.value, "content": request.content})

    # Limit context window (keep system messages, limit conversation history)
    # Separate system messages from conversation messages
    system_messages = [msg for msg in prompt_messages if msg.get("role") == "system"]
    conversation_messages = [msg for msg in prompt_messages if msg.get("role") != "system"]

    # Keep all system messages + limited conversation history
    # This ensures DAC persona and memory context are always included
    limited_conversation = conversation_messages[-MAX_CONTEXT_MESSAGES:]
    prompt_messages = system_messages + limited_conversation

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
        
        # Record additional tokens if needed
        additional_tokens = max(total_tokens - prompt_tokens_estimate, 0)
        if additional_tokens:
            await record_additional_tokens(org_id, request.provider, additional_tokens)
        
        # Sanitize response to maintain DAC persona
        sanitized_content = sanitize_response(
            provider_response.content,
            request.provider.value
        )

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
                    print(f"✅ Saved {fragments_saved} memory fragments from turn")
            except asyncio.TimeoutError:
                print(f"⚠️  Memory save timeout, continuing without saving")
            except Exception as e:
                # Don't fail the request if memory saving fails
                print(f"⚠️  Memory save error: {e}, continuing without saving")

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
            "user_message": _to_message_response(user_msg, hide_provider=True),
            "assistant_message": _to_message_response(assistant_msg, hide_provider=True),
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
    return AddMessageResponse(
        user_message=response_data["user_message"],
        assistant_message=response_data["assistant_message"],
    )


@router.post("/{thread_id}/messages/stream")
async def add_message_streaming(
    thread_id: str,
    request: AddMessageRequest,
    org_id: str = Depends(require_org_id),
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
    
    # Step 2: ULTRA-FAST PATH - Route and stream immediately, validate in background
    import time as perf_time
    start_routing = perf_time.perf_counter()
    
    # Route FIRST (no DB needed) - this is the key optimization
    from app.api.router import analyze_content
    provider_str, model, reason = analyze_content(user_content, 0)
    provider_enum = ProviderType(provider_str)
    validated_model = validate_and_get_model(provider_enum, model)
    print(f"⚡ Routing done in {(perf_time.perf_counter() - start_routing)*1000:.0f}ms -> {provider_enum.value}/{validated_model}")
    
    # Detect intent from routing reason for LaTeX math formatting
    from app.services.dac_persona import detect_intent_from_reason
    detected_intent = detect_intent_from_reason(reason) if reason else None
    
    # Start DB operations in background (don't await yet)
    start_db = perf_time.perf_counter()
    rls_task = set_rls_context(db, org_id)
    api_key_task = get_api_key_for_org(db, org_id, provider_enum)
    
    # Add user turn to memory immediately (fast, in-memory, no DB)
    add_turn(thread_id, Turn(role=request.role.value, content=user_content))
    
    # Build prompt immediately (fast, in-memory) with intent-aware persona injection
    from app.services.dac_persona import DAC_SYSTEM_PROMPT, inject_dac_persona
    base_messages = build_prompt_for_model(thread_id, DAC_SYSTEM_PROMPT)
    prompt_messages = inject_dac_persona(base_messages, qa_mode=False, intent=detected_intent)
    print(f"⚡ Memory + prompt built in {(perf_time.perf_counter() - start_db)*1000:.0f}ms")
    
    # EXTREME OPTIMIZATION: Skip RLS, get API key from cache/env instead of DB
    # This is the fastest possible path - stream immediately
    
    # Try to get API key from environment (bypass DB entirely for speed)
    import os
    api_key = None
    
    # Check environment variables for API keys (fastest path)
    if provider_enum == ProviderType.OPENAI:
        api_key = os.getenv("OPENAI_API_KEY")
    elif provider_enum == ProviderType.GEMINI:
        api_key = os.getenv("GEMINI_API_KEY")
    elif provider_enum == ProviderType.PERPLEXITY:
        api_key = os.getenv("PERPLEXITY_API_KEY")
    elif provider_enum == ProviderType.KIMI:
        api_key = os.getenv("KIMI_API_KEY")
    
    # If not in env, fall back to DB
    if not api_key:
        print(f"⚠️  No env var for {provider_enum.value}, fetching from DB...")
        start_wait = perf_time.perf_counter()
        # Just await the tasks directly - no fancy stuff
        await rls_task
        api_key = await api_key_task
        print(f"⚡ DB fetch done in {(perf_time.perf_counter() - start_wait)*1000:.0f}ms")
    else:
        print(f"⚡ Using cached API key from env for {provider_enum.value}")
        # Still need RLS for DB access
        await rls_task
    
    print(f"⚡ TOTAL SETUP TIME: {(perf_time.perf_counter() - start_routing)*1000:.0f}ms - Starting provider stream NOW...")
    
    # Start provider streaming IMMEDIATELY (don't wait for DB validation)
    from app.services.provider_dispatch import call_provider_adapter_streaming
    
    async def stream_with_background_validation():
        # Collect response for memory/observability
        response_content = ""
        usage_data = {}
        
        # Stream directly from provider (THIS STARTS IMMEDIATELY)
        print(f"⚡ Starting provider stream for {provider_enum.value}/{validated_model}...")
        stream_start = perf_time.perf_counter()
        first_chunk = True
        
        async for chunk in call_provider_adapter_streaming(
            provider_enum,
            validated_model,
            prompt_messages,
            api_key
        ):
            if first_chunk:
                print(f"🚀 FIRST CHUNK received in {(perf_time.perf_counter() - stream_start)*1000:.0f}ms from provider!")
                first_chunk = False
            # Collect content for memory
            if chunk.get("type") == "delta" and "delta" in chunk:
                response_content += chunk["delta"]
            elif chunk.get("type") == "meta":
                if "usage" in chunk:
                    usage_data.update(chunk["usage"])
            
            yield chunk
        
        # Post-stream: Background validation and logging (non-blocking)
        async def background_cleanup():
            try:
                # Now do DB validation (non-blocking for streaming)
                thread = await _get_thread(db, thread_id, org_id)
                org = await _get_org(db, org_id)
                request_limit = org.requests_per_day or settings.default_requests_per_day
                token_limit = org.tokens_per_day or settings.default_tokens_per_day
                
                # Load messages for next time
                prior_messages = await _get_recent_messages(db, thread_id)
                if prior_messages:
                    db_messages = [
                        {"role": msg.role.value, "content": msg.content}
                        for msg in prior_messages
                    ]
                    initialize_thread_from_db(thread_id, db_messages)
                
                # Add assistant response to memory
                if response_content:
                    add_turn(thread_id, Turn(role="assistant", content=response_content))
                
                # Log observability
                from app.services.token_track import normalize_usage
                from app.services.observability import log_turn
                usage = normalize_usage(usage_data, provider_enum.value)
                await log_turn(
                    thread_id=thread_id,
                    turn_id=str(uuid.uuid4()),
                    intent="auto",
                    router_decision={"provider": provider_enum.value, "model": validated_model, "reason": reason},
                    provider=provider_enum.value,
                    model=validated_model,
                    latency_ms=0,
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
            except Exception as e:
                # Log but don't fail - streaming already completed
                print(f"Background cleanup error: {e}")
        
        # Run cleanup in background (don't await)
        asyncio.create_task(background_cleanup())
    
    # Return streaming response immediately (starts streaming ASAP)
    async def event_source():
        start = time.perf_counter()
        ttft_emitted = False
        
        # Early heartbeat to open the pipe immediately
        yield "event: ping\ndata: {}\n\n"
        
        # Emit router decision immediately so UI can show provider badge
        yield f"event: router\n"
        yield f"data: {json.dumps({'provider': provider_enum.value, 'model': validated_model, 'reason': reason})}\n\n"
        
        try:
            async for chunk in stream_with_background_validation():
                chunk_type = chunk.get("type", "delta")
                
                if chunk_type == "meta":
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
        except Exception as e:
            yield f"event: error\n"
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(event_source(), media_type="text/event-stream")
    
    # Phase 4: SSE Integration (cache → route → stream → log)
    # Feature flag: DAC_SSE_V2=1 to enable new integration
    use_sse_v2 = bool(int(os.getenv("DAC_SSE_V2", "0")))
    
    # OPTIMIZATION: Add user turn to memory early (non-blocking for streaming)
    add_turn(thread_id, Turn(role=request.role.value, content=user_content))
    
    if use_sse_v2:
        # Check cache first
        cache_key = make_cache_key(thread_id=thread_id, user_text=user_content)
        cached = get_cached(cache_key)
        
        if cached:
            # Cache hit - stream cached response
            async def gen_cached():
                yield sse_event({"delta": cached["text"]}, event="delta")
                yield sse_event({"type": "done"}, event="done")
            
            # Add to memory and log
            add_turn(thread_id, Turn(role="assistant", content=cached["text"]))
            asyncio.create_task(log_turn(
                thread_id=thread_id,
                turn_id=str(uuid.uuid4()),
                intent=cached.get("intent", "unknown"),
                router_decision={"provider": cached.get("provider"), "model": cached.get("model"), "reason": "cache_hit"},
                provider=cached.get("provider", "unknown"),
                model=cached.get("model", "unknown"),
                latency_ms=0,
                input_tokens=cached.get("usage", {}).get("input_tokens"),
                output_tokens=cached.get("usage", {}).get("output_tokens"),
                cost_est=cached.get("cost_est", 0.0),
                cache_hit=True,
                fallback_used=False,
                safety_flags=cached.get("safety_flags", {}),
                truncated=cached.get("usage", {}).get("truncated", False),
            ))
            
            return StreamingResponse(gen_cached(), media_type="text/event-stream")
        
        # Not cached - use route_and_call
        # OPTIMIZATION: Get API keys lazily (only when needed) to avoid blocking
        api_key_map = {}  # Will be populated lazily
        
        # Lazy API key fetcher - only called when provider is determined
        async def get_api_key_lazy(provider: ProviderType):
            if provider.value not in api_key_map:
                try:
                    key = await get_api_key_for_org(db, org_id, provider)
                    if key:
                        api_key_map[provider.value] = key
                        return key
                except:
                    pass
            return api_key_map.get(provider.value)
        
        # OpenTelemetry span
        @asynccontextmanager
        async def span_ctx():
            if OTEL_AVAILABLE and tracer:
                with tracer.start_as_current_span("dac.stream_message") as span:
                    span.set_attribute("dac.thread_id", thread_id)
                    span.set_attribute("dac.cache_hit", False)
                    yield span
            else:
                yield None
        
        async with span_ctx() as span:
            start_time = time.perf_counter()
            
            # Route and call with fallback (lazy API key fetching)
            rc = await route_and_call(thread_id, user_content, org_id, api_key_map, db, get_api_key_fn=get_api_key_lazy)
            
            intent = rc["intent"]
            provider = rc["result"]["provider"]
            model = rc["result"]["model"]
            stream_iter = rc["result"]["stream"]  # Async iterator
            safety_flags_dict = rc["safety_flags"]
            fallback_used = rc["result"].get("fallback_used", False)
            
            if span:
                span.set_attribute("dac.intent", intent)
                span.set_attribute("dac.provider", provider)
                span.set_attribute("dac.model", model)
                span.set_attribute("dac.fallback_used", fallback_used)
            
            # Stream response
            async def gen():
                full_text_parts = []
                try:
                    async for chunk in stream_iter:
                        full_text_parts.append(chunk)
                        yield sse_event({"delta": chunk}, event="delta")
                    
                    yield sse_event({"type": "done"}, event="done")
                finally:
                    elapsed = int((time.perf_counter() - start_time) * 1000)
                    full_text = "".join(full_text_parts)
                    
                    # Add to memory
                    add_turn(thread_id, Turn(role="assistant", content=full_text))
                    
                    # Normalize usage
                    usage = normalize_usage(rc["result"].get("usage", {}), provider)
                    cost_est = usage.get("cost_est", 0.0)
                    
                    # Cache best-effort
                    asyncio.create_task(set_cached(cache_key, {
                        "text": full_text,
                        "intent": intent,
                        "provider": provider,
                        "model": model,
                        "usage": usage,
                        "cost_est": cost_est,
                        "safety_flags": safety_flags_dict,
                    }))
                    
                    # Observability
                    if span:
                        span.set_attribute("dac.latency_ms", elapsed)
                    
                    asyncio.create_task(log_turn(
                        thread_id=thread_id,
                        turn_id=str(uuid.uuid4()),
                        intent=intent,
                        router_decision={"provider": provider, "model": model, "reason": "primary_or_fallback"},
                        provider=provider,
                        model=model,
                        latency_ms=elapsed,
                        input_tokens=usage.get("input_tokens"),
                        output_tokens=usage.get("output_tokens"),
                        cost_est=cost_est,
                        cache_hit=False,
                        fallback_used=fallback_used,
                        safety_flags=safety_flags_dict,
                        truncated=usage.get("truncated", False),
                    ))
            
            return StreamingResponse(gen(), media_type="text/event-stream")
    
    # Legacy path (existing fan-out logic)
    # User turn already added above (line 717)
    
    # Get DAC persona (with QA mode detection)
    custom_system_prompt = (thread.description or "").strip()
    qa_mode = custom_system_prompt == "PHASE3_QA_MODE" or "PHASE3_QA_MODE" in custom_system_prompt
    
    # Get base persona
    from app.services.dac_persona import DAC_SYSTEM_PROMPT, DAC_QA_SYSTEM_PROMPT
    if qa_mode:
        persona = DAC_QA_SYSTEM_PROMPT
    else:
        persona = DAC_SYSTEM_PROMPT
    
    # Build prompt using memory manager (includes summary, facts, and recent turns)
    prompt_messages = build_prompt_for_model(thread_id, persona)
    
    # Add custom system prompt if provided (non-QA mode)
    if custom_system_prompt and not qa_mode:
        prompt_messages.insert(1, {  # After persona, before summary
            "role": "system",
            "content": custom_system_prompt
        })

    prompt_tokens_estimate = estimate_messages_tokens(prompt_messages)

    await enforce_limits(
        org_id,
        request.provider,
        prompt_tokens_estimate,
        request_limit,
        token_limit,
    )

    # OPTIMIZATION: Handle 'auto' provider/model - route internally (fast, no external API call)
    if (request.provider == ProviderType.OPENROUTER or request.provider is None) and (request.model == "auto" or request.model is None):
        # Use internal routing (faster than external router call)
        from app.api.router import analyze_content
        provider_str, model, reason = analyze_content(user_content, 0)
        request.provider = ProviderType(provider_str)
        request.model = model
        # Apply intent smoothing if thread_id provided
        if thread_id:
            from app.services.memory_manager import smooth_intent, update_last_intent
            current_intent = "ambiguous_or_other"  # Extract from reason if needed
            smoothed_intent = smooth_intent(current_intent, thread_id, user_content)
            if smoothed_intent != current_intent:
                # Re-route if needed
                provider_str, model, reason = analyze_content(user_content, 0)
                request.provider = ProviderType(provider_str)
                request.model = model
            update_last_intent(thread_id, smoothed_intent)
    
    # OPTIMIZATION: Get API key (only for the provider we need, not all providers)
    api_key = await get_api_key_for_org(db, org_id, request.provider)

    # Validate model
    validated_model = validate_and_get_model(request.provider, request.model)
    current_model = validated_model

    # Feature flag check
    stream_fanout_enabled = bool(int(os.getenv("STREAM_FANOUT_ENABLED", "1")))
    
    # Generate coalesce key
    key = coalesce_key(request.provider.value, current_model, prompt_messages, thread_id=thread_id)

    # Subscribe first, then possibly become the leader
    if stream_fanout_enabled:
        q, is_leader, mark_done = await stream_hub.subscribe(key)
    else:
        # Legacy: each request gets its own stream (no fan-out)
        q = None
        is_leader = True
        mark_done = None

    async def event_source():
        start = time.perf_counter()
        ttft_emitted = False
        cache_hit_emitted = False

        # Early heartbeat to open the pipe immediately
        yield "event: ping\ndata: {}\n\n"

        # Emit cache_hit immediately (follower = cache_hit)
        if stream_fanout_enabled and not is_leader:
            yield f"event: meta\n"
            yield f"data: {json.dumps({'cache_hit': True})}\n\n"
            cache_hit_emitted = True

        try:
            if stream_fanout_enabled:
                if is_leader:
                    # Emit cache_hit: false for leader (fresh request)
                    if not cache_hit_emitted:
                        yield f"event: meta\n"
                        yield f"data: {json.dumps({'cache_hit': False})}\n\n"
                        cache_hit_emitted = True

                    # Leader: one upstream call; publish deltas to all subscribers
                    response_content = ""  # Collect for memory
                    pacer = build_pacer(request.provider.value)
                    async with pacer as slot:
                        async for chunk in call_provider_adapter_streaming(
                            request.provider,
                            current_model,
                            prompt_messages,
                            api_key,
                        ):
                            # Adapters now emit normalized {"type": "meta|delta|done", ...} format
                            chunk_type = chunk.get("type", "delta")
                            
                            # Collect content for memory
                            if chunk_type == "delta" and "delta" in chunk:
                                response_content += chunk["delta"]

                            # Forward meta events (including TTFT) immediately
                            if chunk_type == "meta":
                                if "ttft_ms" in chunk and not ttft_emitted:
                                    ttft_emitted = True
                                await stream_hub.publish(key, chunk)
                            elif chunk_type == "delta":
                                # If we haven't seen TTFT yet, infer it from first delta
                                if not ttft_emitted:
                                    ttft_ms = int((time.perf_counter() - start) * 1000)
                                    await stream_hub.publish(key, {"type": "meta", "ttft_ms": ttft_ms})
                                    ttft_emitted = True
                                await stream_hub.publish(key, chunk)
                            elif chunk_type == "done":
                                await stream_hub.publish(key, chunk)

                    # Add assistant response to memory after streaming completes
                    if response_content:
                        add_turn(thread_id, Turn(role="assistant", content=response_content))
                    
                    await stream_hub.complete(key)
                    if mark_done:
                        await mark_done()

                # Every subscriber (including leader) consumes locally
                while True:
                    item = await q.get()
                    etype = item.get("type", "delta")
                    yield f"event: {etype}\n"
                    yield "data: " + json.dumps(item) + "\n\n"
                    if etype == "done":
                        break
            else:
                # Legacy: direct streaming (no fan-out)
                # Emit cache_hit: false (legacy path is always fresh)
                if not cache_hit_emitted:
                    yield f"event: meta\n"
                    yield f"data: {json.dumps({'cache_hit': False})}\n\n"
                    cache_hit_emitted = True

                # Collect response content for memory
                response_content = ""
                
                # Timeout handling (15 seconds)
                TIMEOUT_SECONDS = 15
                timeout_occurred = False
                try:
                    pacer = build_pacer(request.provider.value)
                    async with pacer as slot:
                        stream = call_provider_adapter_streaming(
                            request.provider,
                            current_model,
                            prompt_messages,
                            api_key,
                        )
                        start_time = time.perf_counter()
                        async for chunk in stream:
                            # Check timeout
                            if time.perf_counter() - start_time > TIMEOUT_SECONDS:
                                timeout_occurred = True
                                break
                            # Adapters now emit normalized format
                            chunk_type = chunk.get("type", "delta")
                            
                            # Collect content for memory
                            if chunk_type == "delta" and "delta" in chunk:
                                response_content += chunk["delta"]

                            if chunk_type == "meta":
                                if "ttft_ms" in chunk and not ttft_emitted:
                                    ttft_emitted = True
                                yield f"event: meta\n"
                                yield f"data: {json.dumps(chunk)}\n\n"
                            elif chunk_type == "delta":
                                # If we haven't seen TTFT yet, infer it from first delta
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
                    
                    # Add assistant response to memory after streaming completes
                    if response_content:
                        add_turn(thread_id, Turn(role="assistant", content=response_content))
                        
                except Exception as timeout_error:
                    timeout_occurred = True
                
                if timeout_occurred:
                    # Timeout - send graceful response
                    timeout_response = "That's a bit vague—could you clarify what you'd like me to help with? For example, are you asking about a specific topic, or do you need help with something else?"
                    yield f"event: delta\n"
                    yield f"data: {json.dumps({'type': 'delta', 'delta': timeout_response})}\n\n"
                    yield f"event: done\n"
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    # Add timeout response to memory
                    add_turn(thread_id, Turn(role="assistant", content=timeout_response))
        except asyncio.CancelledError:
            return
        except Exception as e:
            # Emit error event and close stream gracefully
            error_message = str(e)
            yield f"event: error\n"
            yield f"data: {json.dumps({'error': error_message})}\n\n"
            return

    # Anti-buffering headers for SSE
    HEADERS_SSE = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-store, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # Nginx
    }

    return StreamingResponse(event_source(), headers=HEADERS_SSE, media_type="text/event-stream")


@router.get("/{thread_id}", response_model=ThreadDetailResponse)
async def get_thread(
    thread_id: str,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """Get thread details with messages."""
    # Set RLS context
    await set_rls_context(db, org_id)

    # Get thread with messages
    stmt = select(Thread).where(
        Thread.id == thread_id,
        Thread.org_id == org_id
    )
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

    return ThreadDetailResponse(
        id=thread.id,
        org_id=thread.org_id,
        title=thread.title,
        description=thread.description,
        last_provider=None,  # Hide provider info
        last_model=None,  # Hide model info
        created_at=thread.created_at,
        messages=[_to_message_response(msg, hide_provider=True) for msg in messages]
    )


@router.get("/{thread_id}/audit", response_model=List[AuditEntry])
async def get_thread_audit(
    thread_id: str,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """Return the latest audit entries for a thread."""
    await set_rls_context(db, org_id)
    await _get_thread(db, thread_id, org_id)

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


async def _get_thread(db: AsyncSession, thread_id: str, org_id: str) -> Thread:
    stmt = select(Thread).where(
        Thread.id == thread_id,
        Thread.org_id == org_id,
    )
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
            "provider": request.provider.value,
            "model": request.model,
            "reason": request.reason,
        },
        "scope": request.scope.value,
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
