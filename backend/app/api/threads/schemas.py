"""
Pydantic models for the threads API.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime
import enum

from app.models.message import MessageRole
from app.models.provider_key import ProviderType


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


class CollaborateRequest(BaseModel):
    """Request for collaborate mode."""
    message: str = Field(..., description="User's message or question")
    mode: str = Field(default="auto", description="'auto' or 'manual'")