"""User API key model."""

from sqlalchemy import Column, String, Boolean, Integer, BigInteger, DateTime, Text, CheckConstraint, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.database import Base


class UserAPIKey(Base):
    """User-provided API keys for AI providers."""

    __tablename__ = "user_api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)

    # Encrypted data
    encrypted_key = Column(Text, nullable=False)
    encryption_salt = Column(Text, nullable=False)

    # Metadata
    key_name = Column(String(100))
    is_active = Column(Boolean, default=True, index=True)
    last_validated_at = Column(DateTime(timezone=True))
    validation_status = Column(String(20), default='pending')

    # Usage tracking
    total_requests = Column(Integer, default=0)
    total_tokens_used = Column(BigInteger, default=0)
    last_used_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "provider IN ('openai', 'gemini', 'anthropic', 'perplexity', 'kimi')",
            name='valid_provider'
        ),
    )

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert to dictionary, optionally excluding sensitive data."""
        data = {
            'id': str(self.id),
            'provider': self.provider,
            'key_name': self.key_name,
            'is_active': self.is_active,
            'validation_status': self.validation_status,
            'last_validated_at': self.last_validated_at.isoformat() if self.last_validated_at else None,
            'total_requests': self.total_requests,
            'total_tokens_used': self.total_tokens_used,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        if include_sensitive:
            # Never include the actual encrypted key in API responses
            # This is just for internal use if needed
            pass

        return data


class APIKeyAuditLog(Base):
    """Audit log for API key access and usage."""

    __tablename__ = "api_key_audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_api_key_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)

    action = Column(String(50), nullable=False)
    ip_address = Column(String)
    user_agent = Column(Text)

    # Additional metadata
    audit_metadata = Column(JSON, default={})

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
