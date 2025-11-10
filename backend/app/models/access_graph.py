"""Access graph models for dynamic permissions."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class UserAgentPermission(Base):
    """User permission to invoke an agent/provider."""

    __tablename__ = "user_agent_permissions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # User
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Agent (provider key: perplexity, openai, gemini, etc.)
    agent_key = Column(String, nullable=False, index=True)

    # Permission
    can_invoke = Column(Boolean, default=True, nullable=False)

    # Temporal validity
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="user_agent_permissions")

    __table_args__ = (
        Index('ix_user_agent_perm', 'user_id', 'agent_key'),
    )

    def __repr__(self):
        return f"<UserAgentPermission user={self.user_id} agent={self.agent_key}>"


class AgentResourcePermission(Base):
    """Agent permission to access a resource (memory, document, etc.)."""

    __tablename__ = "agent_resource_permissions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Organization (for RLS)
    org_id = Column(String, ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True)

    # Agent
    agent_key = Column(String, nullable=False, index=True)

    # Resource (memory fragment ID, document ID, etc.)
    resource_key = Column(String, nullable=False, index=True)

    # Permission
    can_access = Column(Boolean, default=True, nullable=False)

    # Temporal validity
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    org = relationship("Org")

    __table_args__ = (
        Index('ix_agent_resource_perm', 'agent_key', 'resource_key'),
    )

    def __repr__(self):
        return f"<AgentResourcePermission agent={self.agent_key} resource={self.resource_key}>"
