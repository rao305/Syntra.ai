"""Audit API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter()


@router.get("/threads/{thread_id}")
async def get_thread_audit(thread_id: str, db: AsyncSession = Depends(get_db)):
    """Get audit trail for a thread."""
    # TODO: Implement audit retrieval
    return {"audit_logs": []}
