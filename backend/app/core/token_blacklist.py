"""
Token revocation/blacklist system for secure logout and session management.

Uses Redis to maintain a blacklist of revoked tokens. When a user logs out
or a security incident occurs, tokens can be immediately revoked.
"""

import logging
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from redis import Redis
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Redis key prefix for token blacklist
TOKEN_BLACKLIST_PREFIX = "token_blacklist:"
TOKEN_REVOCATION_PREFIX = "token_revoked_at:"


class TokenBlacklist:
    """Manages revoked token storage in Redis."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.enabled = True

    async def revoke_token(self, token: str, ttl_seconds: Optional[int] = None) -> bool:
        """
        Revoke a token (add it to blacklist).

        Args:
            token: JWT token to revoke
            ttl_seconds: Time to live in Redis (defaults to token expiration time)

        Returns:
            True if token was revoked, False if already revoked
        """
        try:
            token_id = self._get_token_id(token)

            # If TTL not specified, use a default (e.g., 24 hours)
            if ttl_seconds is None:
                ttl_seconds = 86400  # 24 hours

            key = f"{TOKEN_BLACKLIST_PREFIX}{token_id}"

            # Add to blacklist with TTL
            result = self.redis.setex(
                key,
                ttl_seconds,
                datetime.utcnow().isoformat()
            )

            if result:
                logger.info(
                    f"Token revoked",
                    extra={
                        "token_id": token_id,
                        "ttl_seconds": ttl_seconds,
                    }
                )
                return True
            return False

        except Exception as e:
            logger.error(
                f"Failed to revoke token: {str(e)}",
                exc_info=True
            )
            # If Redis fails, disable token revocation
            # (fail-open to prevent lockout, but log as critical)
            self.enabled = False
            logger.critical("Token revocation system unavailable - Redis connection failed")
            return False

    async def is_revoked(self, token: str) -> bool:
        """
        Check if a token is revoked.

        Args:
            token: JWT token to check

        Returns:
            True if token is revoked, False otherwise
        """
        try:
            if not self.enabled:
                # If revocation system is down, allow token (fail-open)
                logger.warning("Token revocation check skipped - system unavailable")
                return False

            token_id = self._get_token_id(token)
            key = f"{TOKEN_BLACKLIST_PREFIX}{token_id}"

            # Check if token is in blacklist
            exists = self.redis.exists(key)
            return exists == 1

        except Exception as e:
            logger.error(
                f"Failed to check token revocation: {str(e)}",
                exc_info=True
            )
            # If Redis fails, disable token revocation
            self.enabled = False
            return False

    async def revoke_user_tokens(self, user_id: str, ttl_seconds: int = 86400) -> int:
        """
        Revoke all tokens for a user (used for logout, security incidents, etc).

        Args:
            user_id: User to revoke all tokens for
            ttl_seconds: Time tokens remain in revocation list

        Returns:
            Number of tokens revoked
        """
        try:
            # This is a simplified implementation
            # In production, you'd maintain a per-user token list
            key = f"{TOKEN_REVOCATION_PREFIX}{user_id}"

            # Mark user as revoked until TTL expires
            self.redis.setex(
                key,
                ttl_seconds,
                datetime.utcnow().isoformat()
            )

            logger.warning(
                f"All user tokens revoked",
                extra={
                    "user_id": user_id,
                    "ttl_seconds": ttl_seconds,
                }
            )
            return 1  # Simplified count

        except Exception as e:
            logger.error(
                f"Failed to revoke user tokens: {str(e)}",
                exc_info=True
            )
            self.enabled = False
            return 0

    async def is_user_revoked(self, user_id: str) -> bool:
        """
        Check if all tokens for a user are revoked.

        Args:
            user_id: User to check

        Returns:
            True if user's tokens are revoked
        """
        try:
            if not self.enabled:
                return False

            key = f"{TOKEN_REVOCATION_PREFIX}{user_id}"
            exists = self.redis.exists(key)
            return exists == 1

        except Exception as e:
            logger.error(
                f"Failed to check user revocation: {str(e)}",
                exc_info=True
            )
            self.enabled = False
            return False

    def clear_blacklist(self) -> int:
        """
        Clear all tokens from blacklist (use with caution).

        Returns:
            Number of keys deleted
        """
        try:
            pattern = f"{TOKEN_BLACKLIST_PREFIX}*"
            cursor = 0
            deleted = 0

            while True:
                cursor, keys = self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted += self.redis.delete(*keys)
                if cursor == 0:
                    break

            logger.warning(f"Blacklist cleared: {deleted} tokens removed")
            return deleted

        except Exception as e:
            logger.error(f"Failed to clear blacklist: {str(e)}", exc_info=True)
            return 0

    def get_stats(self) -> dict:
        """Get statistics about the token blacklist."""
        try:
            pattern = f"{TOKEN_BLACKLIST_PREFIX}*"
            count = 0
            cursor = 0

            while True:
                cursor, keys = self.redis.scan(cursor, match=pattern, count=100)
                count += len(keys)
                if cursor == 0:
                    break

            return {
                "enabled": self.enabled,
                "total_revoked_tokens": count,
                "prefix": TOKEN_BLACKLIST_PREFIX,
            }

        except Exception as e:
            logger.error(f"Failed to get blacklist stats: {str(e)}", exc_info=True)
            return {
                "enabled": False,
                "error": str(e)
            }

    @staticmethod
    def _get_token_id(token: str) -> str:
        """
        Get a unique ID for a token.

        Uses SHA256 hash of token to avoid storing full tokens.
        """
        return hashlib.sha256(token.encode()).hexdigest()


# Global token blacklist instance
_blacklist: Optional[TokenBlacklist] = None


async def get_token_blacklist() -> TokenBlacklist:
    """Get or create the global token blacklist."""
    global _blacklist

    if _blacklist is None:
        try:
            # Connect to Redis (using Upstash Redis)
            redis_url = settings.upstash_redis_url
            if not redis_url:
                raise ValueError("Redis URL not configured")

            redis_client = Redis.from_url(
                redis_url,
                decode_responses=False,
                socket_connect_timeout=5
            )

            # Test connection
            redis_client.ping()
            _blacklist = TokenBlacklist(redis_client)
            logger.info("Token blacklist initialized with Redis")

        except Exception as e:
            logger.error(
                f"Failed to initialize token blacklist: {str(e)}",
                exc_info=True
            )
            logger.warning("Token revocation will be disabled - Redis unavailable")
            # Create a disabled blacklist instance
            _blacklist = TokenBlacklist(None)
            _blacklist.enabled = False

    return _blacklist
