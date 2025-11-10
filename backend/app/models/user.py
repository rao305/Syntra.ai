"""User model."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.database import Base


class UserRole(str, enum.Enum):
    """User roles within an organization."""

    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class User(Base):
    """User model."""

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)

    # Organization
    org_id = Column(String, ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(SQLEnum(UserRole), default=UserRole.MEMBER, nullable=False)

    # Auth
    email_verified = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    org = relationship("Org", back_populates="users")
    threads = relationship("Thread", back_populates="creator", foreign_keys="Thread.creator_id")
    messages = relationship("Message", back_populates="user")
    user_agent_permissions = relationship("UserAgentPermission", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"
