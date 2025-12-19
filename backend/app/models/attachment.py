"""Attachment model for messages."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, LargeBinary, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class Attachment(Base):
    """File attachment in a message or thread."""

    __tablename__ = "attachments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Thread & message reference
    thread_id = Column(String, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(String, ForeignKey("messages.id", ondelete="CASCADE"), nullable=True, index=True)

    # File metadata
    filename = Column(String, nullable=False)
    mime_type = Column(String, nullable=True)  # e.g., image/png, application/pdf
    file_size = Column(Integer, nullable=False)  # Size in bytes

    # Storage
    file_data = Column(LargeBinary, nullable=False)  # Binary file content
    storage_path = Column(String, nullable=True)  # For future external storage (S3, GCS, etc.)

    # Attachment type
    attachment_type = Column(String, nullable=False, default="file")  # "image", "file", etc.

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    thread = relationship("Thread", back_populates="attachments")
    message = relationship("Message", back_populates="attachments")

    def __repr__(self):
        return f"<Attachment {self.id} ({self.filename})>"
