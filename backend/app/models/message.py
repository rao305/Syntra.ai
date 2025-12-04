"""Message model."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum as SQLEnum, Integer, JSON, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.database import Base


class MessageRole(str, enum.Enum):
    """Message role (OpenAI-style)."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(Base):
    """Message in a thread."""

    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Thread & user
    thread_id = Column(String, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Message content
    role = Column(
        SQLEnum(
            MessageRole,
            name="message_role",
            create_type=False,
            values_callable=lambda x: [e.value for e in x]
        ),
        nullable=False
    )
    content = Column(Text, nullable=False)

    # E2E Encryption fields
    encrypted_content = Column(LargeBinary, nullable=True)  # Encrypted message content
    encryption_key_id = Column(String, nullable=True)  # Reference to encryption key version

    # Provider metadata
    provider = Column(String, nullable=True)  # Which provider generated this (for assistant messages)
    model = Column(String, nullable=True)
    provider_message_id = Column(String, nullable=True)  # External ID from provider
    meta = Column(JSON, nullable=True)  # Provider-specific metadata (latency, request IDs)

    # Token usage
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)

    # Citations (for Perplexity)
    citations = Column(JSON, nullable=True)  # Array of citation objects

    # Sequence
    sequence = Column(Integer, nullable=False)  # Order within thread

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    thread = relationship("Thread", back_populates="messages")
    user = relationship("User", back_populates="messages")

    def __repr__(self):
        return f"<Message {self.id} ({self.role})>"
