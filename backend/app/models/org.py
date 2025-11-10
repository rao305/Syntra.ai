"""Organization model."""
from sqlalchemy import Column, String, DateTime, Integer, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class Org(Base):
    """Organization/tenant model."""

    __tablename__ = "orgs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)

    # Billing
    stripe_customer_id = Column(String, unique=True, nullable=True)
    stripe_subscription_id = Column(String, unique=True, nullable=True)
    subscription_status = Column(String, nullable=True)  # active, canceled, past_due, etc.
    seats_licensed = Column(Integer, default=0)
    seats_used = Column(Integer, default=0)

    # Rate limits (per org overrides)
    requests_per_day = Column(Integer, nullable=True)  # NULL = use default
    tokens_per_day = Column(Integer, nullable=True)

    # SSO (Phase 2)
    sso_enabled = Column(Boolean, default=False)
    saml_metadata_url = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="org", cascade="all, delete-orphan")
    threads = relationship("Thread", back_populates="org", cascade="all, delete-orphan")
    provider_keys = relationship("ProviderKey", back_populates="org", cascade="all, delete-orphan")
    memory_fragments = relationship("MemoryFragment", back_populates="org", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Org {self.slug}>"
