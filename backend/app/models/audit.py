"""Audit log model."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class AuditLog(Base):
    """Immutable audit log for routing decisions and memory access."""

    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Thread & turn
    thread_id = Column(String, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(String, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Routing decision
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    reason = Column(Text, nullable=False)  # "why routed" explanation

    # Memory access
    fragments_included = Column(JSON, nullable=False)  # Array of fragment IDs
    fragments_excluded = Column(JSON, nullable=False)  # Array of {id, reason} objects
    scope = Column(String, nullable=False)  # auto, strict_private, allow_shared

    # Hashes (for verification)
    package_hash = Column(String, nullable=False)  # SHA-256 of outbound prompt + fragments
    response_hash = Column(String, nullable=True)  # SHA-256 of response

    # Token usage
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)

    # Timestamps (immutable)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    thread = relationship("Thread", back_populates="audit_logs")
    message = relationship("Message")
    user = relationship("User")

    def __repr__(self):
        return f"<AuditLog {self.id} ({self.provider}/{self.model})>"
