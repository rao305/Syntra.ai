"""Helpers for resolving provider API keys."""
from __future__ import annotations

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.provider_key import ProviderKey, ProviderType
from app.security import encryption_service
from config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


async def get_api_key_for_org(
    db: AsyncSession,
    org_id: str,
    provider: ProviderType
) -> str:
    """
    Fetch the decrypted API key for an org/provider pair.

    Falls back to global settings if the org has not configured a key,
    or if decryption fails due to encryption key mismatch.
    """
    stmt = select(ProviderKey).where(
        ProviderKey.org_id == org_id,
        ProviderKey.provider == provider,
        ProviderKey.is_active == "true",
    )
    result = await db.execute(stmt)
    record: Optional[ProviderKey] = result.scalar_one_or_none()

    if record:
        try:
            return encryption_service.decrypt(record.encrypted_key)
        except Exception as e:
            # Decryption failed (likely encryption key mismatch)
            # Fall back to environment variable API keys
            logger.warning(f"Failed to decrypt API key for {provider.value} in org {org_id}: {e}. Falling back to environment variables.")

    # Fallback to environment variable API keys
    fallback = _get_fallback_key(provider)
    if fallback:
        return fallback

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"{provider.value} is not configured for this organization",
    )


def _get_fallback_key(provider: ProviderType) -> Optional[str]:
    """Return optional fallback key from global settings."""
    if provider == ProviderType.PERPLEXITY:
        return settings.perplexity_api_key
    if provider == ProviderType.OPENAI:
        return settings.openai_api_key
    if provider == ProviderType.GEMINI:
        return settings.google_api_key
    if provider == ProviderType.OPENROUTER:
        return settings.openrouter_api_key
    if provider == ProviderType.KIMI:
        return settings.kimi_api_key
    return None
