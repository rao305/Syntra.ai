"""
Thread CRUD operations.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import logging

from app.database import get_db
from app.security import set_rls_context
from app.api.deps import require_org_id, get_current_user_optional, CurrentUser
from app.core.exceptions import handle_exceptions
from .schemas import (
    CreateThreadRequest,
    CreateThreadResponse,
    ThreadListItem,
    ThreadDetailResponse,
    UpdateThreadRequest,
    UpdateThreadSettingsRequest,
    AuditEntry
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[ThreadListItem])
@handle_exceptions()
async def list_threads(
    limit: int = Query(50, le=200),
    archived: Optional[bool] = Query(None, description="Filter by archived status"),
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """List all threads for the organization."""
    from app.models.thread import Thread
    from app.models.message import Message
    from sqlalchemy import select, or_, exists, and_
    
    # Set RLS context
    user_id = current_user.id if current_user else None
    await set_rls_context(db, org_id, user_id)
    
    logger.info(f"🔍 list_threads called - org_id: {org_id}, user_id: {user_id}, current_user: {current_user}")
    
    # Build query - filter by org_id and creator_id if user is authenticated
    query = select(Thread).where(Thread.org_id == org_id)
    
    # CRITICAL FIX: Filter threads by creator_id to prevent cross-user data leaks
    # Also handle legacy threads with creator_id: null - show them only if user has messages in that thread
    if user_id:
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
    
    # CRITICAL FIX: For threads with null creator_id, check if user has messages and update creator_id
    # This fixes threads that were created before the fix
    updated_threads = False
    if user_id:
        for thread in threads:
            if thread.creator_id is None:
                # Check if user has messages in this thread
                msg_check = await db.execute(
                    select(Message).where(
                        Message.thread_id == thread.id,
                        Message.user_id == user_id
                    ).limit(1)
                )
                if msg_check.scalar_one_or_none():
                    # Update creator_id to fix the association
                    thread.creator_id = user_id
                    updated_threads = True
                    logger.info(f"✅ Fixed thread {thread.id} creator_id to {user_id}")
        # Commit any updates
        if updated_threads:
            await db.commit()
            await set_rls_context(db, org_id, user_id)
    
    logger.info(f"✅ Returning {len(threads)} threads for user {user_id}")
    
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
@handle_exceptions()
async def search_threads(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(20, le=100),
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Search threads by title and content."""
    logger.info(f"Searching threads for org {org_id[:8]} with query: {q}")
    # TODO: Implement thread search logic
    return []


@router.post("/", response_model=CreateThreadResponse, status_code=status.HTTP_201_CREATED)
@handle_exceptions()
async def create_thread(
    request: CreateThreadRequest,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Create a new conversation thread."""
    from app.models.thread import Thread
    from app.models.user import User
    import logging
    logger = logging.getLogger(__name__)

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
        from sqlalchemy import select
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


@router.get("/{thread_id}", response_model=ThreadDetailResponse)
@handle_exceptions()
async def get_thread(
    thread_id: str,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Get thread details with messages."""
    from app.models.thread import Thread
    from app.models.message import Message
    from sqlalchemy import select, func
    import logging
    logger = logging.getLogger(__name__)

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

    # Import the helper function (it should be available in the schemas or we can define it locally)
    def _to_message_response(message, hide_provider=False):
        from .schemas import MessageResponse
        return MessageResponse(
            id=message.id,
            role=message.role.value,
            content=message.content,
            provider=None if hide_provider else message.provider,
            model=None if hide_provider else message.model,
            sequence=message.sequence,
            created_at=message.created_at,
            citations=message.citations,
            meta=message.meta
        )

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


@router.patch("/{thread_id}", response_model=ThreadDetailResponse)
@handle_exceptions()
async def update_thread(
    thread_id: str,
    thread_data: UpdateThreadRequest,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Update thread title."""
    logger.info(f"Updating thread {thread_id[:8]} for org {org_id[:8]}")
    # TODO: Implement thread update logic
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.patch("/{thread_id}/settings")
@handle_exceptions()
async def update_thread_settings(
    thread_id: str,
    settings: UpdateThreadSettingsRequest,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Update thread settings."""
    logger.info(f"Updating settings for thread {thread_id[:8]}")
    # TODO: Implement thread settings update logic
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.patch("/{thread_id}/archive")
@handle_exceptions()
async def archive_thread(
    thread_id: str,
    archived: bool = True,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Archive or unarchive a thread."""
    logger.info(f"{'Archiving' if archived else 'Unarchiving'} thread {thread_id[:8]}")
    # TODO: Implement thread archive logic
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_exceptions()
async def delete_thread(
    thread_id: str,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Delete a thread."""
    logger.info(f"Deleting thread {thread_id[:8]} for org {org_id[:8]}")
    # TODO: Implement thread deletion logic
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
@handle_exceptions()
async def bulk_delete_threads(
    thread_ids: List[str],
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Bulk delete threads."""
    logger.info(f"Bulk deleting {len(thread_ids)} threads for org {org_id[:8]}")
    # TODO: Implement bulk delete logic
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/{thread_id}/audit", response_model=List[AuditEntry])
@handle_exceptions()
async def get_thread_audit(
    thread_id: str,
    limit: int = Query(100, le=500),
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Get audit log for a thread."""
    logger.info(f"Getting audit log for thread {thread_id[:8]}")
    # TODO: Implement audit log retrieval logic
    return []
