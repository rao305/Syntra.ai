"""Service for managing user-provided API keys."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
import uuid

from app.models.user_api_key import UserAPIKey, APIKeyAuditLog
from app.security import user_api_key_encryption_service
from app.core.exceptions import ValidationError, NotFoundError

logger = logging.getLogger(__name__)


class APIKeyService:
    """
    Manages user-provided API keys for AI providers.
    """

    SUPPORTED_PROVIDERS = {
        'openai': {
            'name': 'OpenAI',
            'test_model': 'gpt-3.5-turbo',
            'test_prompt': 'Say "test" if you can read this.',
        },
        'gemini': {
            'name': 'Google Gemini',
            'test_model': 'gemini-pro',
            'test_prompt': 'Say "test" if you can read this.',
        },
        'anthropic': {
            'name': 'Anthropic Claude',
            'test_model': 'claude-3-haiku-20240307',
            'test_prompt': 'Say "test" if you can read this.',
        },
        'perplexity': {
            'name': 'Perplexity',
            'test_model': 'sonar-small-online',
            'test_prompt': 'Say "test" if you can read this.',
        },
        'kimi': {
            'name': 'Kimi (Moonshot)',
            'test_model': 'moonshot-v1-8k',
            'test_prompt': 'Say "test" if you can read this.',
        },
    }

    def __init__(self, db: AsyncSession, user_id: str):
        self.db = db
        self.user_id = user_id
        self.encryption = user_api_key_encryption_service

    async def add_api_key(
        self,
        provider: str,
        api_key: str,
        key_name: Optional[str] = None,
        validate: bool = True
    ) -> UserAPIKey:
        """
        Add a new API key for a provider.

        Args:
            provider: Provider name (openai, gemini, etc.)
            api_key: The actual API key from the provider
            key_name: User-friendly name for this key
            validate: Whether to validate the key by making a test API call

        Returns:
            Created UserAPIKey object
        """
        # Validate provider
        if provider not in self.SUPPORTED_PROVIDERS:
            raise ValidationError(
                f"Unsupported provider: {provider}. "
                f"Supported: {', '.join(self.SUPPORTED_PROVIDERS.keys())}"
            )

        # Generate encryption salt
        salt = self.encryption.generate_salt()

        # Encrypt the API key
        encrypted_key = self.encryption.encrypt(api_key, salt)

        # Set default key name
        if not key_name:
            key_name = f"{self.SUPPORTED_PROVIDERS[provider]['name']} Key"

        # Validate the key if requested
        validation_status = 'pending'
        if validate:
            is_valid = await self._validate_api_key(provider, api_key)
            validation_status = 'valid' if is_valid else 'invalid'

            if not is_valid:
                raise ValidationError(
                    f"Invalid API key for {provider}. "
                    "Please check your key and try again."
                )

        # Create database record
        user_api_key = UserAPIKey(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            provider=provider,
            encrypted_key=encrypted_key,
            encryption_salt=salt,
            key_name=key_name,
            validation_status=validation_status,
            last_validated_at=datetime.utcnow() if validate else None,
            is_active=True
        )

        self.db.add(user_api_key)
        await self.db.commit()
        await self.db.refresh(user_api_key)

        logger.info(f"Added API key for provider {provider}, user {self.user_id}")

        # Audit log
        await self._log_audit(
            user_api_key.id,
            'created',
            {'provider': provider, 'key_name': key_name}
        )

        return user_api_key

    async def get_api_keys(
        self,
        provider: Optional[str] = None,
        active_only: bool = True
    ) -> List[UserAPIKey]:
        """Get all API keys for the user."""
        query = select(UserAPIKey).where(UserAPIKey.user_id == self.user_id)

        if provider:
            query = query.where(UserAPIKey.provider == provider)

        if active_only:
            query = query.where(UserAPIKey.is_active == True)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_api_key(self, key_id: str) -> UserAPIKey:
        """Get a specific API key."""
        result = await self.db.execute(
            select(UserAPIKey).where(
                and_(
                    UserAPIKey.id == key_id,
                    UserAPIKey.user_id == self.user_id
                )
            )
        )
        key = result.scalar_one_or_none()

        if not key:
            raise NotFoundError("API key", key_id)

        return key

    async def get_decrypted_key(self, key_id: str) -> str:
        """
        Get decrypted API key for use in API calls.
        IMPORTANT: Only use this when actually making API calls.
        Do not store or log the decrypted key.
        """
        key = await self.get_api_key(key_id)

        if not key.is_active:
            raise ValidationError("API key is inactive")

        # Decrypt the key
        try:
            decrypted = self.encryption.decrypt(
                key.encrypted_key,
                key.encryption_salt
            )

            # Audit log
            await self._log_audit(key.id, 'decrypted')

            return decrypted

        except Exception as e:
            logger.error(f"Failed to decrypt API key {key_id}: {e}")
            raise ValidationError("Failed to decrypt API key")

    async def get_active_key_for_provider(
        self,
        provider: str
    ) -> Optional[UserAPIKey]:
        """Get the first active API key for a provider."""
        keys = await self.get_api_keys(provider=provider, active_only=True)
        return keys[0] if keys else None

    async def update_api_key(
        self,
        key_id: str,
        api_key: Optional[str] = None,
        key_name: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> UserAPIKey:
        """Update an API key."""
        key = await self.get_api_key(key_id)

        updates = {}

        if api_key is not None:
            # Re-encrypt with new API key value
            updates['encrypted_key'] = self.encryption.encrypt(
                api_key,
                key.encryption_salt
            )
            updates['validation_status'] = 'pending'

        if key_name is not None:
            updates['key_name'] = key_name

        if is_active is not None:
            updates['is_active'] = is_active

        if updates:
            updates['updated_at'] = datetime.utcnow()

            await self.db.execute(
                update(UserAPIKey)
                .where(UserAPIKey.id == key_id)
                .values(**updates)
            )
            await self.db.commit()
            await self.db.refresh(key)

            # Audit log
            await self._log_audit(key.id, 'updated', updates)

        return key

    async def delete_api_key(self, key_id: str) -> None:
        """Delete an API key."""
        key = await self.get_api_key(key_id)

        await self.db.delete(key)
        await self.db.commit()

        logger.info(f"Deleted API key {key_id} for user {self.user_id}")

        # Audit log
        await self._log_audit(key.id, 'deleted')

    async def validate_api_key(self, key_id: str) -> bool:
        """Validate an API key by making a test call."""
        key = await self.get_api_key(key_id)
        decrypted_key = self.encryption.decrypt(
            key.encrypted_key,
            key.encryption_salt
        )

        is_valid = await self._validate_api_key(key.provider, decrypted_key)

        # Update validation status
        await self.db.execute(
            update(UserAPIKey)
            .where(UserAPIKey.id == key_id)
            .values(
                validation_status='valid' if is_valid else 'invalid',
                last_validated_at=datetime.utcnow()
            )
        )
        await self.db.commit()

        # Audit log
        await self._log_audit(key.id, 'validated', {'is_valid': is_valid})

        return is_valid

    async def track_usage(
        self,
        key_id: str,
        tokens_used: int,
        request_type: str
    ) -> None:
        """Track usage of an API key."""
        await self.db.execute(
            update(UserAPIKey)
            .where(UserAPIKey.id == key_id)
            .values(
                total_requests=UserAPIKey.total_requests + 1,
                total_tokens_used=UserAPIKey.total_tokens_used + tokens_used,
                last_used_at=datetime.utcnow()
            )
        )
        await self.db.commit()

        # Audit log
        await self._log_audit(
            key_id,
            'used',
            {'tokens_used': tokens_used, 'request_type': request_type}
        )

    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================

    async def _validate_api_key(self, provider: str, api_key: str) -> bool:
        """
        Validate an API key by making a test API call.
        Returns True if valid, False otherwise.
        """
        provider_config = self.SUPPORTED_PROVIDERS.get(provider)
        if not provider_config:
            return False

        try:
            if provider == 'openai':
                return await self._validate_openai(api_key, provider_config)
            elif provider == 'gemini':
                return await self._validate_gemini(api_key, provider_config)
            elif provider == 'anthropic':
                return await self._validate_anthropic(api_key, provider_config)
            elif provider == 'perplexity':
                return await self._validate_perplexity(api_key, provider_config)
            elif provider == 'kimi':
                return await self._validate_kimi(api_key, provider_config)
            else:
                return False

        except Exception as e:
            logger.warning(f"API key validation failed for {provider}: {e}")
            return False

    async def _validate_openai(self, api_key: str, config: dict) -> bool:
        """Validate OpenAI API key."""
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=api_key)
            response = await client.chat.completions.create(
                model=config['test_model'],
                messages=[{"role": "user", "content": config['test_prompt']}],
                max_tokens=10
            )
            return bool(response.choices)
        except Exception:
            return False

    async def _validate_gemini(self, api_key: str, config: dict) -> bool:
        """Validate Gemini API key."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(config['test_model'])
            response = await model.generate_content_async(config['test_prompt'])
            return bool(response.text)
        except Exception:
            return False

    async def _validate_anthropic(self, api_key: str, config: dict) -> bool:
        """Validate Anthropic API key."""
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=api_key)
            response = await client.messages.create(
                model=config['test_model'],
                max_tokens=10,
                messages=[{"role": "user", "content": config['test_prompt']}]
            )
            return bool(response.content)
        except Exception:
            return False

    async def _validate_perplexity(self, api_key: str, config: dict) -> bool:
        """Validate Perplexity API key."""
        try:
            import openai
            client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.perplexity.ai"
            )
            response = await client.chat.completions.create(
                model=config['test_model'],
                messages=[{"role": "user", "content": config['test_prompt']}],
                max_tokens=10
            )
            return bool(response.choices)
        except Exception:
            return False

    async def _validate_kimi(self, api_key: str, config: dict) -> bool:
        """Validate Kimi API key."""
        try:
            import openai
            client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.moonshot.cn/v1"
            )
            response = await client.chat.completions.create(
                model=config['test_model'],
                messages=[{"role": "user", "content": config['test_prompt']}],
                max_tokens=10
            )
            return bool(response.choices)
        except Exception:
            return False

    async def _log_audit(
        self,
        key_id: str,
        action: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log API key access to audit table."""
        audit_log = APIKeyAuditLog(
            id=str(uuid.uuid4()),
            user_api_key_id=key_id,
            user_id=self.user_id,
            action=action,
            audit_metadata=metadata or {}
        )

        self.db.add(audit_log)
        # Don't commit here - let the calling function handle commits
