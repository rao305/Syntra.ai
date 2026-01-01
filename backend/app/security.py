"""Security utilities for RLS and encryption."""
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
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


class UserAPIKeyEncryptionService:
    """
    Secure encryption/decryption for user-provided API keys.
    Uses Fernet (symmetric encryption) with user-specific salts.
    """

    def __init__(self):
        # Master encryption key from environment
        # MUST be set in production and kept secret
        self.master_key = settings.encryption_key

        if not self.master_key:
            raise ValueError(
                "ENCRYPTION_KEY must be set in environment.  "
                "Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )

        if len(self.master_key) < 32:
            raise ValueError("ENCRYPTION_KEY must be at least 32 characters")

    def _derive_key(self, salt: bytes) -> bytes:
        """Derive encryption key from master key and salt."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
        return key

    def generate_salt(self) -> str:
        """Generate a random salt for a user."""
        return base64.urlsafe_b64encode(os.urandom(16)).decode()

    def encrypt(self, plaintext: str, salt: str) -> str:
        """
        Encrypt plaintext using master key and user salt.

        Args:
            plaintext: The data to encrypt (e.g., API key)
            salt: User-specific salt

        Returns:
            Base64-encoded encrypted data
        """
        try:
            salt_bytes = base64.urlsafe_b64decode(salt.encode())
            key = self._derive_key(salt_bytes)
            f = Fernet(key)

            encrypted = f.encrypt(plaintext.encode())
            return base64.urlsafe_b64encode(encrypted).decode()

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError("Failed to encrypt data")

    def decrypt(self, encrypted_data: str, salt: str) -> str:
        """
        Decrypt data using master key and user salt.

        Args:
            encrypted_data: Base64-encoded encrypted data
            salt: User-specific salt

        Returns:
            Decrypted plaintext
        """
        try:
            salt_bytes = base64.urlsafe_b64decode(salt.encode())
            key = self._derive_key(salt_bytes)
            f = Fernet(key)

            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = f.decrypt(encrypted_bytes)
            return decrypted.decode()

        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt data")

    def rotate_encryption(
        self,
        encrypted_data: str,
        old_salt: str,
        new_salt: str
    ) -> str:
        """
        Re-encrypt data with a new salt (for key rotation).
        """
        plaintext = self.decrypt(encrypted_data, old_salt)
        return self.encrypt(plaintext, new_salt)


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
        # Validate org_id format (UUID) - allow demo org
        if org_id != "org_demo":  # Special case for demo/development
            try:
                uuid.UUID(org_id)
            except ValueError:
                raise ValidationAPIError(
                    "Invalid organization ID",
                    details={"field": "org_id", "message": f"org_id must be a valid UUID, got: {org_id}"}
                )

        # SAFE: PostgreSQL SET doesn't support parameterized queries, but we've validated the UUID
        await db.execute(
            text(f"SET LOCAL app.current_org_id = '{org_id}'")
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
                text(f"SET LOCAL app.current_user_id = '{user_id}'")
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

        # Build query safely - table name is validated against allowlist
        base_query = "SELECT 1 FROM {} WHERE id = :record_id AND org_id = :org_id LIMIT 1"
        query = base_query.format(safe_table)
        result = await db.execute(
            text(query),
            {"record_id": record_id, "org_id": org_id}
        )
        return result.fetchone() is not None


# Backward compatibility
async def set_rls_context(session: AsyncSession, org_id: str, user_id: Optional[str] = None):
    """Legacy function - use RowLevelSecurity.set_context instead."""
    return await RowLevelSecurity.set_context(session, org_id, user_id)


# Singleton instances
encryption_service = EncryptionService()
user_api_key_encryption_service = UserAPIKeyEncryptionService()
