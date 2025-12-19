"""
File upload/download endpoints for thread attachments.

Supports dual-mode storage during migration:
- New uploads → Supabase Storage
- Legacy files → Database BLOBs (fallback)
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import logging
import io
import uuid

from app.database import get_db
from app.security import set_rls_context
from app.api.deps import require_org_id, get_current_user_optional, CurrentUser
from app.core.exceptions import handle_exceptions
from app.models.attachment import Attachment
from app.models.thread import Thread
from app.services.storage_service import storage_service
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
    """Upload a file attachment to a thread via Supabase Storage."""
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

    # Generate attachment ID
    attachment_id = str(uuid.uuid4())

    # Determine attachment type
    attachment_type = "image" if file.content_type and file.content_type.startswith("image/") else "file"

    try:
        # Upload to Supabase Storage
        storage_path = await storage_service.upload_file(
            org_id=org_id,
            thread_id=thread_id,
            attachment_id=attachment_id,
            filename=file.filename,
            file_data=file_content,
            mime_type=file.content_type
        )

        # Create attachment record (NO BLOB storage)
        attachment = Attachment(
            id=attachment_id,
            thread_id=thread_id,
            filename=file.filename,
            mime_type=file.content_type,
            file_size=len(file_content),
            storage_path=storage_path,
            storage_bucket="attachments",
            file_data=None,  # Don't store in database
            attachment_type=attachment_type
        )
        db.add(attachment)
        await db.commit()
        await db.refresh(attachment)

        logger.info(f"✅ Uploaded attachment {attachment_id} to Supabase Storage")

        return AttachmentResponse(
            id=attachment.id,
            filename=attachment.filename,
            mime_type=attachment.mime_type,
            file_size=attachment.file_size,
            attachment_type=attachment.attachment_type,
            created_at=attachment.created_at.isoformat() if attachment.created_at else None
        )

    except Exception as e:
        logger.error(f"❌ Failed to upload attachment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
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
    """Download an attachment from a thread (supports Storage + BLOB fallback)."""
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

    # Determine file source and download
    file_data = None

    if attachment.is_in_storage:
        # Download from Supabase Storage
        try:
            file_data = await storage_service.download_file(
                attachment.storage_path,
                attachment.storage_bucket or "attachments"
            )
            logger.info(f"✅ Downloaded attachment {attachment_id} from Supabase Storage")
        except Exception as e:
            logger.error(f"❌ Failed to download from Storage: {e}")
            # Fall through to BLOB fallback
            file_data = None

    # Fallback to legacy BLOB storage
    if file_data is None:
        if attachment.file_data:
            file_data = attachment.file_data
            logger.info(f"Using legacy BLOB storage for attachment {attachment_id}")
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="File not found in Storage or Database"
            )

    # Return file as stream
    return StreamingResponse(
        iter([file_data]),
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
    """Delete an attachment from a thread (cleans up Storage and Database)."""
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

    # Delete from Supabase Storage if exists
    if attachment.is_in_storage:
        try:
            await storage_service.delete_file(
                attachment.storage_path,
                attachment.storage_bucket or "attachments"
            )
            logger.info(f"✅ Deleted attachment {attachment_id} from Supabase Storage")
        except Exception as e:
            logger.warning(f"⚠️ Failed to delete from Storage (continuing): {e}")

    # Delete database record
    await db.delete(attachment)
    await db.commit()

    logger.info(f"✅ Deleted attachment {attachment_id} from database")
