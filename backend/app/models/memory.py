"""Memory fragment model."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum as SQLEnum, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.database import Base


class MemoryTier(str, enum.Enum):
    """Memory visibility tier."""

    PRIVATE = "private"  # Only accessible to creator
    SHARED = "shared"    # Accessible to org (after PII scrubbing)


class MemoryFragment(Base):
    """Memory fragment with provenance and embeddings."""

    __tablename__ = "memory_fragments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Organization & creator
    org_id = Column(String, ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Memory content
    text = Column(Text, nullable=False)
    tier = Column(SQLEnum(MemoryTier), default=MemoryTier.PRIVATE, nullable=False, index=True)

    # Vector embedding (store vector ID from Qdrant)
    vector_id = Column(String, nullable=True, index=True)

    # Provenance (immutable audit trail)
    provenance = Column(JSON, nullable=False)
    # Structure: {
    #   "agent_key": "perplexity",
    #   "resources": ["doc_123", "web_search"],
    #   "timestamp": "2024-01-01T00:00:00Z",
    #   "hash": "sha256:..."
    # }

    # Content hash for deduplication
    content_hash = Column(String, nullable=False, index=True)

    # Timestamps (append-only, no updates)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    org = relationship("Org", back_populates="memory_fragments")
    user = relationship("User")

    __table_args__ = (
        Index('ix_memory_org_tier', 'org_id', 'tier'),
    )

    def __repr__(self):
        return f"<MemoryFragment {self.id} ({self.tier})>"
