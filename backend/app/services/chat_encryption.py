"""E2E encryption service for chat messages."""
from typing import Optional, Dict
from cryptography.fernet import Fernet
import hashlib
import base64
from config import get_settings

settings = get_settings()


class ChatEncryptionService:
    """Service for encrypting/decrypting chat messages with per-user keys."""

    def __init__(self):
        self.base_key = settings.encryption_key

    def derive_user_key(self, user_id: str) -> str:
        """
        Derive a unique encryption key for a user from the base key and user_id.

        This ensures each user has their own encryption key while being deterministic.
        The key is derived using HMAC-based key derivation.
        """
        # Create a deterministic key for this user
        hmac_result = hashlib.pbkdf2_hmac(
            'sha256',
            self.base_key.encode(),
            user_id.encode(),
            100000,  # iterations
            dklen=32  # 32 bytes for Fernet key
        )
        # Fernet requires URL-safe base64 encoded 32-byte key
        fernet_key = base64.urlsafe_b64encode(hmac_result)
        return fernet_key.decode()

    def encrypt_message(self, content: str, user_id: str) -> bytes:
        """
        Encrypt message content with user-specific key.

        Args:
            content: The message text to encrypt
            user_id: The user ID for key derivation

        Returns:
            Encrypted bytes
        """
        try:
            key = self.derive_user_key(user_id)
            cipher = Fernet(key)
            return cipher.encrypt(content.encode())
        except Exception as e:
            raise ValueError(f"Encryption failed: {str(e)}")

    def decrypt_message(self, encrypted_content: bytes, user_id: str) -> str:
        """
        Decrypt message content with user-specific key.

        Args:
            encrypted_content: The encrypted bytes
            user_id: The user ID for key derivation

        Returns:
            Decrypted message text
        """
        try:
            key = self.derive_user_key(user_id)
            cipher = Fernet(key)
            return cipher.decrypt(encrypted_content).decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")

    def encrypt_message_for_thread(self, content: str, thread_id: str) -> bytes:
        """
        Encrypt message for a thread (thread-level encryption).

        Args:
            content: The message text to encrypt
            thread_id: The thread ID for key derivation

        Returns:
            Encrypted bytes
        """
        try:
            key = self.derive_user_key(thread_id)
            cipher = Fernet(key)
            return cipher.encrypt(content.encode())
        except Exception as e:
            raise ValueError(f"Encryption failed: {str(e)}")

    def decrypt_message_from_thread(self, encrypted_content: bytes, thread_id: str) -> str:
        """
        Decrypt message from a thread (thread-level encryption).

        Args:
            encrypted_content: The encrypted bytes
            thread_id: The thread ID for key derivation

        Returns:
            Decrypted message text
        """
        try:
            key = self.derive_user_key(thread_id)
            cipher = Fernet(key)
            return cipher.decrypt(encrypted_content).decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")


# Singleton instance
chat_encryption_service = ChatEncryptionService()
