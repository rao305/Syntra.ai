"""Provider API key model (encrypted)."""
from sqlalchemy import Column, String, DateTime, ForeignKey, LargeBinary, Enum as SQLEnum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.database import Base


class ProviderType(str, enum.Enum):
    """LLM provider types."""

    PERPLEXITY = "perplexity"
    OPENAI = "openai"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"


class ProviderKey(Base):
    """Encrypted provider API keys (BYOK per org)."""

    __tablename__ = "provider_keys"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Organization
    org_id = Column(String, ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True)

    # Provider
    provider = Column(SQLEnum(ProviderType), nullable=False)

    # Encrypted key (using Fernet encryption)
    encrypted_key = Column(LargeBinary, nullable=False)

    # Metadata
    key_name = Column(String, nullable=True)  # Optional friendly name
    last_used = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(String, default="true", nullable=False)  # For rotation

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    org = relationship("Org", back_populates="provider_keys")

    __table_args__ = (
        Index('ix_provider_keys_org_provider', 'org_id', 'provider'),
    )

    def __repr__(self):
        return f"<ProviderKey {self.provider} for org {self.org_id}>"
