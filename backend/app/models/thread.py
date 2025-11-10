"""Thread model."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class Thread(Base):
    """Conversation thread model."""

    __tablename__ = "threads"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Organization & creator
    org_id = Column(String, ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True)
    creator_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Thread metadata
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    # Current provider context (for UI display)
    last_provider = Column(String, nullable=True)  # perplexity, openai, gemini, openrouter
    last_model = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    org = relationship("Org", back_populates="threads")
    creator = relationship("User", back_populates="threads", foreign_keys=[creator_id])
    messages = relationship("Message", back_populates="thread", cascade="all, delete-orphan", order_by="Message.created_at")
    audit_logs = relationship("AuditLog", back_populates="thread", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Thread {self.id} ({self.title or 'Untitled'})>"
