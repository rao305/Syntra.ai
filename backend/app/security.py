"""Security utilities for RLS and encryption."""
from typing import Optional
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import uuid
import logging
from config import get_settings

from app.core.database_utils import SafeQueryBuilder
from app.core.error_handlers import ValidationAPIError

settings = get_settings()
logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting/decrypting provider API keys."""

    def __init__(self):
        self.cipher = Fernet(settings.encryption_key.encode())

    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt a string."""
        return self.cipher.encrypt(plaintext.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        """Decrypt bytes to string."""
        return self.cipher.decrypt(ciphertext).decode()


class RowLevelSecurity:
    """
    Enforces row-level security for multi-tenant data access.
    All queries are parameterized to prevent SQL injection.
    """

    @staticmethod
    async def set_context(db: AsyncSession, org_id: str, user_id: Optional[str] = None) -> None:
        """
        Set Row Level Security context for current session.

        This should be called at the start of each request with the
        authenticated user's org_id and user_id.

        Args:
            db: SQLAlchemy async session
            org_id: Organization ID (must be valid UUID)
            user_id: Optional user ID (must be valid UUID)
        """
        # Validate org_id format (UUID)
        try:
            uuid.UUID(org_id)
        except ValueError:
            raise ValidationAPIError(
                "Invalid organization ID",
                details={"field": "org_id", "message": f"org_id must be a valid UUID, got: {org_id}"}
            )

        # SAFE: Using parameterized query
        await db.execute(
            text("SET LOCAL app.current_org_id = :org_id"),
            {"org_id": org_id}
        )

        if user_id:
            try:
                uuid.UUID(user_id)
            except ValueError:
                raise ValidationAPIError(
                    "Invalid user ID",
                    details={"field": "user_id", "message": f"user_id must be a valid UUID, got: {user_id}"}
                )

            await db.execute(
                text("SET LOCAL app.current_user_id = :user_id"),
                {"user_id": user_id}
            )

        logger.debug(f"RLS context set for org: {org_id[:8]}...")

    @staticmethod
    async def clear_context(db: AsyncSession) -> None:
        """Clear the organization context."""
        await db.execute(text("RESET app.current_org_id"))
        await db.execute(text("RESET app.current_user_id"))

    @staticmethod
    async def verify_access(
        db: AsyncSession,
        table: str,
        record_id: str,
        org_id: str
    ) -> bool:
        """
        Verify that a record belongs to the specified organization.
        """
        # Validate table name against allowlist
        safe_table = SafeQueryBuilder.validate_table(table)

        # Validate UUIDs
        try:
            uuid.UUID(record_id)
            uuid.UUID(org_id)
        except ValueError:
            return False

        query = f"SELECT 1 FROM {safe_table} WHERE id = :record_id AND org_id = :org_id LIMIT 1"
        result = await db.execute(
            text(query),
            {"record_id": record_id, "org_id": org_id}
        )
        return result.fetchone() is not None


# Backward compatibility
async def set_rls_context(session: AsyncSession, org_id: str, user_id: Optional[str] = None):
    """Legacy function - use RowLevelSecurity.set_context instead."""
    return await RowLevelSecurity.set_context(session, org_id, user_id)


# Singleton instance
encryption_service = EncryptionService()
