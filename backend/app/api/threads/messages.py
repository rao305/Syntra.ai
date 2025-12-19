"""
Message operations within threads.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import logging

from app.database import get_db
from app.security import set_rls_context
from app.api.deps import require_org_id, get_current_user_optional, CurrentUser
from app.core.exceptions import handle_exceptions
from app.models.thread import Thread
from app.models.message import Message, MessageRole
from .schemas import (
    AddMessageRequest,
    AddMessageResponse,
    SaveRawMessageRequest,
    SaveRawMessageResponse,
    MessageResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_next_sequence(db: AsyncSession, thread_id: str) -> int:
    """Get the next message sequence number for a thread."""
    stmt = select(func.max(Message.sequence)).where(Message.thread_id == thread_id)
    result = await db.execute(stmt)
    max_sequence = result.scalar()
    return (max_sequence or -1) + 1


@router.post("/{thread_id}/messages", response_model=AddMessageResponse)
@handle_exceptions()
async def send_message(
    thread_id: str,
    request: AddMessageRequest,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Send a message in a thread and get AI response."""
    logger.info(f"Sending message to thread {thread_id[:8]} for org {org_id[:8]}")

    # Set RLS context
    user_id = current_user.id if current_user else None
    await set_rls_context(db, org_id, user_id)

    # Verify thread exists
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

    # Get next sequence
    next_sequence = await _get_next_sequence(db, thread_id)

    # Create user message
    user_message = Message(
        thread_id=thread_id,
        user_id=user_id,
        role=MessageRole.USER,
        content=request.content,
        sequence=next_sequence,
    )
    db.add(user_message)
    await db.flush()

    # For now, create a simple assistant response (in a real implementation, this would call an LLM)
    assistant_message = Message(
        thread_id=thread_id,
        role=MessageRole.ASSISTANT,
        content="I acknowledge your message. Full AI integration coming soon.",
        provider=request.provider.value if request.provider else "default",
        model=request.model or "default",
        sequence=next_sequence + 1,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        meta={}
    )
    db.add(assistant_message)

    # Update thread
    thread.last_message_preview = request.content[:120] if len(request.content) > 120 else request.content

    await db.commit()
    await db.refresh(user_message)
    await db.refresh(assistant_message)

    return AddMessageResponse(
        user_message=MessageResponse(
            id=user_message.id,
            role=user_message.role.value,
            content=user_message.content,
            provider=user_message.provider,
            model=user_message.model,
            sequence=user_message.sequence,
            created_at=user_message.created_at,
            citations=user_message.citations,
            meta=user_message.meta
        ),
        assistant_message=MessageResponse(
            id=assistant_message.id,
            role=assistant_message.role.value,
            content=assistant_message.content,
            provider=assistant_message.provider,
            model=assistant_message.model,
            sequence=assistant_message.sequence,
            created_at=assistant_message.created_at,
            citations=assistant_message.citations,
            meta=assistant_message.meta
        )
    )


@router.post("/{thread_id}/messages/raw", response_model=SaveRawMessageResponse)
@handle_exceptions()
async def save_raw_message(
    thread_id: str,
    request: SaveRawMessageRequest,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Save a message directly without AI processing."""
    logger.info(f"Saving raw message to thread {thread_id[:8]} for org {org_id[:8]}")

    # Set RLS context
    user_id = current_user.id if current_user else None
    await set_rls_context(db, org_id, user_id)

    # Verify thread exists
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

    # Get next sequence
    next_sequence = await _get_next_sequence(db, thread_id)

    # Determine role
    try:
        role = MessageRole(request.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {request.role}"
        )

    # Create message
    message = Message(
        thread_id=thread_id,
        user_id=user_id if role == MessageRole.USER else None,
        role=role,
        content=request.content,
        provider=request.provider,
        model=request.model,
        sequence=next_sequence,
        meta=request.meta
    )
    db.add(message)

    # Update thread
    if role == MessageRole.USER:
        thread.last_message_preview = request.content[:120] if len(request.content) > 120 else request.content

    await db.commit()
    await db.refresh(message)

    return SaveRawMessageResponse(
        id=message.id,
        role=message.role.value,
        content=message.content,
        sequence=message.sequence,
        created_at=message.created_at
    )


@router.get("/{thread_id}/messages", response_model=List[MessageResponse])
@handle_exceptions()
async def get_messages(
    thread_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Get messages in a thread."""
    logger.info(f"Getting messages for thread {thread_id[:8]}")

    # Set RLS context
    user_id = current_user.id if current_user else None
    await set_rls_context(db, org_id, user_id)

    # Verify thread exists
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
    stmt = select(Message).where(
        Message.thread_id == thread_id
    ).order_by(Message.sequence).offset(skip).limit(limit)
    result = await db.execute(stmt)
    messages = result.scalars().all()

    return [
        MessageResponse(
            id=msg.id,
            role=msg.role.value,
            content=msg.content,
            provider=msg.provider,
            model=msg.model,
            sequence=msg.sequence,
            created_at=msg.created_at,
            citations=msg.citations,
            meta=msg.meta
        )
        for msg in messages
    ]

