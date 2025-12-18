"""SuperMemory API client for long-term episodic memory storage.

This client provides async access to SuperMemory's API for storing and retrieving
episodic (user-centric) memories. Key responsibilities:
- Search user memories by query
- Add memories with tags for organization
- Get user preferences and interaction history
- Cache results to avoid redundant API calls
- Graceful error handling with fallback behavior
"""

import asyncio
import hashlib
import json
import time
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

import httpx

from config import get_settings

import logging
logger = logging.getLogger(__name__)

settings = get_settings()


class CacheEntry:
    """Cache entry with TTL support."""

    def __init__(self, value: Any, ttl_seconds: int = 300):
        self.value = value
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.created_at > self.ttl_seconds


class SuperMemoryClient:
    """Async client for SuperMemory API."""

    def __init__(self):
        self.api_key = settings.supermemory_api_key
        self.api_base_url = getattr(settings, "supermemory_api_base_url", "https://api.supermemory.ai")
        self._cache: Dict[str, CacheEntry] = {}
        self._timeout = 10.0

    async def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 8,
        cache_ttl: int = 300
    ) -> List[Dict[str, Any]]:
        """
        Search user's episodic memories for a given query.

        Args:
            user_id: User identifier for scoping memories
            query: Search query
            limit: Maximum number of memories to return
            cache_ttl: Cache TTL in seconds

        Returns:
            List of memory fragments with metadata
        """
        try:
            # Check cache first
            cache_key = self._make_cache_key("search", user_id, query)
            cached = self._get_cached(cache_key)
            if cached is not None:
                logger.info("[SuperMemory] Cache hit for search: {user_id}")
                return cached

            # Make API call
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self.api_base_url}/api/memories/search",
                    headers=self._get_headers(),
                    json={
                        "containerTags": [user_id],  # SuperMemory uses containerTags for scoping
                        "query": query,
                        "limit": limit
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    memories = data.get("memories", [])

                    # Format response
                    formatted = [
                        {
                            "text": m.get("content", ""),
                            "id": m.get("id", ""),
                            "tags": m.get("tags", []),
                            "created_at": m.get("createdAt", ""),
                            "relevance_score": m.get("relevanceScore", 0.5)
                        }
                        for m in memories
                    ]

                    # Cache result
                    self._set_cache(cache_key, formatted, ttl_seconds=cache_ttl)

                    logger.info("[SuperMemory] Found {len(formatted)} memories for {user_id}")
                    return formatted
                else:
                    logger.error("[SuperMemory] Search error {response.status_code}: {response.text}")
                    return []

        except asyncio.TimeoutError:
            logger.info("[SuperMemory] Search timeout for {user_id}")
            return []
        except Exception as e:
            logger.error("[SuperMemory] Search error: {e}")
            return []

    async def add_memory(
        self,
        user_id: str,
        memory_text: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a new episodic memory for a user.

        Args:
            user_id: User identifier
            memory_text: The memory content
            tags: Optional tags for organization
            metadata: Optional metadata (context, source, etc.)

        Returns:
            True if memory was saved, False otherwise
        """
        try:
            tags = tags or []
            metadata = metadata or {}

            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self.api_base_url}/api/memories/add",
                    headers=self._get_headers(),
                    json={
                        "containerTags": [user_id],
                        "content": memory_text,
                        "tags": tags,
                        "metadata": metadata,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

                if response.status_code in (200, 201):
                    # Invalidate search cache for this user since we added new memory
                    self._invalidate_cache_prefix(f"search:{user_id}")
                    logger.info("[SuperMemory] Added memory for {user_id}")
                    return True
                else:
                    logger.error("[SuperMemory] Add memory error {response.status_code}: {response.text}")
                    return False

        except asyncio.TimeoutError:
            logger.info("[SuperMemory] Add memory timeout for {user_id}")
            return False
        except Exception as e:
            logger.error("[SuperMemory] Add memory error: {e}")
            return False

    async def get_user_preferences(
        self,
        user_id: str,
        cache_ttl: int = 3600  # Longer cache for preferences
    ) -> Dict[str, Any]:
        """
        Get cached user preferences and context from SuperMemory.

        Args:
            user_id: User identifier
            cache_ttl: Cache TTL in seconds (default 1 hour)

        Returns:
            Dictionary with user preferences
        """
        try:
            # Check cache first
            cache_key = self._make_cache_key("prefs", user_id)
            cached = self._get_cached(cache_key)
            if cached is not None:
                logger.info("[SuperMemory] Cache hit for preferences: {user_id}")
                return cached

            # Make API call
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    f"{self.api_base_url}/api/users/{user_id}/preferences",
                    headers=self._get_headers()
                )

                if response.status_code == 200:
                    prefs = response.json().get("preferences", {})
                    self._set_cache(cache_key, prefs, ttl_seconds=cache_ttl)
                    logger.info("[SuperMemory] Retrieved preferences for {user_id}")
                    return prefs
                else:
                    logger.error("[SuperMemory] Preferences error {response.status_code}")
                    return {}

        except asyncio.TimeoutError:
            logger.info("[SuperMemory] Preferences timeout for {user_id}")
            return {}
        except Exception as e:
            logger.error("[SuperMemory] Preferences error: {e}")
            return {}

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for SuperMemory API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Syntra/1.0"
        }

    def _make_cache_key(self, *args: str) -> str:
        """Create cache key from multiple parts."""
        combined = ":".join(str(arg) for arg in args)
        return hashlib.md5(combined.encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            entry = self._cache[key]
            if not entry.is_expired():
                return entry.value
            else:
                del self._cache[key]
        return None

    def _set_cache(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """Set cache entry."""
        self._cache[key] = CacheEntry(value, ttl_seconds=ttl_seconds)

    def _invalidate_cache_prefix(self, prefix: str) -> None:
        """Invalidate all cache entries matching a prefix."""
        keys_to_delete = [k for k in self._cache.keys() if k.startswith(prefix)]
        for key in keys_to_delete:
            del self._cache[key]

    def clear_cache(self) -> None:
        """Clear entire cache."""
        self._cache.clear()


# Singleton instance
supermemory_client = SuperMemoryClient()
