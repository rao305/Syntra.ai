"""
Thread API routes - split into focused modules.
"""

from fastapi import APIRouter

from .router import router as thread_router
from .messages import router as message_router
from .streaming import router as streaming_router
from .collaboration import router as collaboration_router
from .attachments import router as attachment_router

# Aggregate all routers
router = APIRouter(prefix="/threads", tags=["threads"])

router.include_router(thread_router)
router.include_router(message_router)
router.include_router(streaming_router)
router.include_router(collaboration_router)
router.include_router(attachment_router)