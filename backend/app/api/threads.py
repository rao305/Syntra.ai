"""Threads API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.thread import Thread
from app.models.message import Message, MessageRole
from app.security import set_rls_context

router = APIRouter()


class CreateThreadRequest(BaseModel):
    """Request to create a new thread."""
    org_id: str
    user_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class CreateThreadResponse(BaseModel):
    """Response from creating a thread."""
    thread_id: str
    created_at: datetime


class AddMessageRequest(BaseModel):
    """Request to add a message to a thread."""
    org_id: str
    user_id: Optional[str] = None
    content: str = Field(..., min_length=1)
    role: MessageRole = MessageRole.USER


class MessageResponse(BaseModel):
    """Message response."""
    id: str
    role: str
    content: str
    provider: Optional[str] = None
    model: Optional[str] = None
    sequence: int
    created_at: datetime


class AddMessageResponse(BaseModel):
    """Response from adding a message."""
    message_id: str
    thread_id: str
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


@router.post("/", response_model=CreateThreadResponse)
async def create_thread(request: CreateThreadRequest, db: AsyncSession = Depends(get_db)):
    """Create a new thread."""
    # Set RLS context
    await set_rls_context(db, request.org_id)

    # Create thread
    new_thread = Thread(
        org_id=request.org_id,
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
    db: AsyncSession = Depends(get_db)
):
    """Add a message to a thread."""
    # Set RLS context
    await set_rls_context(db, request.org_id)

    # Verify thread exists and belongs to org
    stmt = select(Thread).where(
        Thread.id == thread_id,
        Thread.org_id == request.org_id
    )
    result = await db.execute(stmt)
    thread = result.scalar_one_or_none()

    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thread {thread_id} not found"
        )

    # Get next sequence number
    stmt = select(func.max(Message.sequence)).where(Message.thread_id == thread_id)
    result = await db.execute(stmt)
    max_sequence = result.scalar()
    next_sequence = (max_sequence or -1) + 1

    # Create message
    new_message = Message(
        thread_id=thread_id,
        user_id=request.user_id,
        role=request.role,
        content=request.content,
        sequence=next_sequence
    )
    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)

    return AddMessageResponse(
        message_id=new_message.id,
        thread_id=thread_id,
        sequence=new_message.sequence,
        created_at=new_message.created_at
    )


@router.get("/{thread_id}", response_model=ThreadDetailResponse)
async def get_thread(thread_id: str, org_id: str, db: AsyncSession = Depends(get_db)):
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
        last_provider=thread.last_provider,
        last_model=thread.last_model,
        created_at=thread.created_at,
        messages=[
            MessageResponse(
                id=msg.id,
                role=msg.role.value,
                content=msg.content,
                provider=msg.provider,
                model=msg.model,
                sequence=msg.sequence,
                created_at=msg.created_at
            )
            for msg in messages
        ]
    )


@router.post("/{thread_id}/forward")
async def forward_thread(thread_id: str, db: AsyncSession = Depends(get_db)):
    """Forward thread to another provider."""
    # TODO: Implement in Phase 2
    return {"message": "Forward thread - to be implemented"}
