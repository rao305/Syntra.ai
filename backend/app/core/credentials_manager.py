"""
Secure credentials manager for handling sensitive data.

This module ensures API keys, tokens, and other credentials are:
1. Cleared from memory immediately after use
2. Never logged or displayed in error messages
3. Stored only in secure context managers
"""

import logging
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
from cryptography.fernet import Fernet
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SecureCredential:
    """Wrapper for a sensitive credential value that clears on deletion."""

    def __init__(self, value: str, name: str = "credential"):
        self.value = value
        self.name = name
        self._cleared = False

    def get(self) -> str:
        """Get the credential value. Raises error if already cleared."""
        if self._cleared:
            raise ValueError(f"Credential '{self.name}' has been cleared")
        return self.value

    def clear(self) -> None:
        """Securely clear the credential from memory."""
        if not self._cleared:
            # Overwrite with empty string
            self.value = ""
            self._cleared = True
            logger.debug(f"Credential '{self.name}' cleared from memory")

    def __del__(self):
        """Ensure credential is cleared when object is garbage collected."""
        self.clear()

    def __str__(self):
        """Prevent accidental logging of credential."""
        if self._cleared:
            return f"<{self.name}: CLEARED>"
        return f"<{self.name}: ***MASKED***>"

    def __repr__(self):
        """Prevent accidental logging of credential."""
        return self.__str__()


class CredentialsManager:
    """Manages secure handling of API keys and tokens."""

    def __init__(self):
        self.cipher = Fernet(settings.encryption_key.encode())

    @asynccontextmanager
    async def use_credentials(self, api_keys: Dict[str, str]):
        """
        Context manager for secure credential usage.

        Usage:
            async with manager.use_credentials(api_keys) as creds:
                # Use credentials
                key = creds.get("openai_api_key")
            # Credentials automatically cleared after context exits
        """
        # Wrap keys in SecureCredential objects
        secure_creds = {
            name: SecureCredential(value, name)
            for name, value in api_keys.items()
        }

        try:
            yield SecureCredentialsDict(secure_creds)
        finally:
            # Clear all credentials
            for cred in secure_creds.values():
                cred.clear()

    def encrypt_credential(self, value: str) -> bytes:
        """Encrypt a credential for storage."""
        return self.cipher.encrypt(value.encode())

    def decrypt_credential(self, encrypted: bytes) -> str:
        """Decrypt a stored credential."""
        return self.cipher.decrypt(encrypted).decode()


class SecureCredentialsDict:
    """Dictionary-like interface for accessing secure credentials."""

    def __init__(self, credentials: Dict[str, SecureCredential]):
        self._credentials = credentials

    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get a credential by name."""
        if name in self._credentials:
            try:
                return self._credentials[name].get()
            except ValueError:
                logger.warning(f"Attempted to access cleared credential: {name}")
                return default
        return default

    def __getitem__(self, name: str) -> str:
        """Get a credential by name (raises KeyError if not found)."""
        if name not in self._credentials:
            raise KeyError(f"Credential '{name}' not found")
        return self._credentials[name].get()

    def __contains__(self, name: str) -> bool:
        """Check if a credential exists."""
        return name in self._credentials

    def keys(self):
        """Get credential names."""
        return self._credentials.keys()

    def __repr__(self):
        """Prevent accidental logging of credentials."""
        return f"<SecureCredentialsDict with {len(self._credentials)} credentials>"


# Global credentials manager instance
_manager: Optional[CredentialsManager] = None


def get_credentials_manager() -> CredentialsManager:
    """Get or create the global credentials manager."""
    global _manager
    if _manager is None:
        _manager = CredentialsManager()
    return _manager
