"""Security utilities for RLS and encryption."""
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from config import get_settings

settings = get_settings()


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


async def set_rls_context(session: AsyncSession, org_id: str, user_id: str | None = None):
    """
    Set Row Level Security context for current session.

    This should be called at the start of each request with the
    authenticated user's org_id and user_id.

    Args:
        session: SQLAlchemy async session
        org_id: Organization ID
        user_id: Optional user ID (for private memory access)
    """
    await session.execute(f"SET LOCAL app.current_org_id = '{org_id}'")
    if user_id:
        await session.execute(f"SET LOCAL app.current_user_id = '{user_id}'")


# Singleton instance
encryption_service = EncryptionService()
