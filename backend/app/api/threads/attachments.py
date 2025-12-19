"""
File upload/download endpoints for thread attachments.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import logging
import io

from app.database import get_db
from app.security import set_rls_context
from app.api.deps import require_org_id, get_current_user_optional, CurrentUser
from app.core.exceptions import handle_exceptions
from app.models.attachment import Attachment
from app.models.thread import Thread
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class AttachmentResponse(BaseModel):
    """Response for attachment operations."""
    id: str
    filename: str
    mime_type: Optional[str]
    file_size: int
    attachment_type: str
    created_at: str

    class Config:
        from_attributes = True


@router.post("/{thread_id}/attachments", response_model=AttachmentResponse)
@handle_exceptions()
async def upload_attachment(
    thread_id: str,
    file: UploadFile = File(...),
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Upload a file attachment to a thread."""
    logger.info(f"Uploading attachment {file.filename} to thread {thread_id[:8]}")

    # Set RLS context
    user_id = current_user.id if current_user else None
    await set_rls_context(db, org_id, user_id)

    # Verify thread exists and belongs to org
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

    # Read file content
    file_content = await file.read()

    # Determine attachment type
    attachment_type = "image" if file.content_type and file.content_type.startswith("image/") else "file"

    # Create attachment record
    attachment = Attachment(
        thread_id=thread_id,
        filename=file.filename,
        mime_type=file.content_type,
        file_size=len(file_content),
        file_data=file_content,
        attachment_type=attachment_type
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)

    return AttachmentResponse(
        id=attachment.id,
        filename=attachment.filename,
        mime_type=attachment.mime_type,
        file_size=attachment.file_size,
        attachment_type=attachment.attachment_type,
        created_at=attachment.created_at.isoformat() if attachment.created_at else None
    )


@router.get("/{thread_id}/attachments/{attachment_id}")
@handle_exceptions()
async def download_attachment(
    thread_id: str,
    attachment_id: str,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Download an attachment from a thread."""
    logger.info(f"Downloading attachment {attachment_id} from thread {thread_id[:8]}")

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

    # Get attachment
    stmt = select(Attachment).where(
        Attachment.id == attachment_id,
        Attachment.thread_id == thread_id
    )
    result = await db.execute(stmt)
    attachment = result.scalar_one_or_none()

    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attachment {attachment_id} not found"
        )

    # Return file as stream
    return StreamingResponse(
        iter([attachment.file_data]),
        media_type=attachment.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={attachment.filename}"
        }
    )


@router.delete("/{thread_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_exceptions()
async def delete_attachment(
    thread_id: str,
    attachment_id: str,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Delete an attachment from a thread."""
    logger.info(f"Deleting attachment {attachment_id} from thread {thread_id[:8]}")

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

    # Get and delete attachment
    stmt = select(Attachment).where(
        Attachment.id == attachment_id,
        Attachment.thread_id == thread_id
    )
    result = await db.execute(stmt)
    attachment = result.scalar_one_or_none()

    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attachment {attachment_id} not found"
        )

    await db.delete(attachment)
    await db.commit()
