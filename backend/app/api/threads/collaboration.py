"""
Multi-model collaboration endpoints.
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging
import json

from app.database import get_db
from app.security import set_rls_context
from app.api.deps import require_org_id, get_current_user_optional, CurrentUser
from app.core.exceptions import handle_exceptions
from .schemas import CollaborateRequest

logger = logging.getLogger(__name__)

router = APIRouter()


def sse_event(data: dict) -> str:
    """Format data as SSE event."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/{thread_id}/collaborate")
@handle_exceptions()
async def run_collaboration(
    thread_id: str,
    request: CollaborateRequest,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Run multi-model collaboration."""
    logger.info(f"Starting collaboration for thread {thread_id[:8]} in org {org_id[:8]}")
    # TODO: Implement collaboration logic
    # This should be migrated from the original threads.py
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/{thread_id}/collaborate/stream")
async def stream_collaboration(
    thread_id: str,
    request: CollaborateRequest,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Stream collaboration results."""
    logger.info(f"Streaming collaboration for thread {thread_id[:8]}")

    async def event_generator():
        try:
            # TODO: Implement streaming collaboration logic
            yield sse_event({"type": "error", "message": "Not implemented yet"})
        except Exception as e:
            logger.exception(f"Collaboration streaming error in thread {thread_id}")
            yield sse_event({"type": "error", "message": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/{thread_id}/forward")
@handle_exceptions()
async def forward_message(
    thread_id: str,
    request: CollaborateRequest,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Forward message to collaboration mode."""
    logger.info(f"Forwarding message in thread {thread_id[:8]}")
    # TODO: Implement forward logic
    raise HTTPException(status_code=501, detail="Not implemented yet")
