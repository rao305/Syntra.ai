"""Memory integration service for cross-model context sharing.

This is the KEY service that enables the Collaborative Memory concept:
- Memory fragments are model-agnostic
- A fragment created by Perplexity can be read by OpenAI
- A fragment created by OpenAI can be read by Gemini
- This creates a shared memory layer across all models

When User sends: Query1 → Perplexity → Query2 → OpenAI → Query3 → Perplexity
Each model sees memory fragments from ALL previous interactions, regardless of which model created them.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.models.memory import MemoryFragment, MemoryTier
from app.models.provider_key import ProviderType
from app.models.access_graph import AgentResourcePermission
from config import get_settings

settings = get_settings()


@dataclass
class MemoryContext:
    """Context retrieved from memory for a query."""

    private_fragments: List[Dict[str, Any]]
    shared_fragments: List[Dict[str, Any]]
    total_fragments: int
    retrieval_time_ms: float


@dataclass
class ExtractedInsight:
    """An insight extracted from a conversation turn."""

    text: str
    tier: MemoryTier
    importance: float  # 0.0 to 1.0


class MemoryService:
    """
    Service for managing collaborative memory across models.

    This implements the two-tier memory system from the Collaborative Memory paper:
    - PRIVATE memory: User-specific, not shared
    - SHARED memory: Org-wide, shared across users (after scrubbing PII)
    """

    COLLECTION_NAME = "dac_memory"

    def __init__(self):
        self._client: Optional[AsyncQdrantClient] = None
        self._embedding_cache = {}  # Simple cache for embeddings

    async def _get_client(self) -> AsyncQdrantClient:
        """Get or create Qdrant client."""
        if self._client is None:
            self._client = AsyncQdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
                timeout=10.0
            )
            # Ensure collection exists
            await self._ensure_collection()
        return self._client

    async def _ensure_collection(self):
        """Ensure Qdrant collection exists."""
        try:
            collections = await self._client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.COLLECTION_NAME not in collection_names:
                # Create collection with 1536 dimensions (OpenAI embedding size)
                await self._client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=1536,
                        distance=Distance.COSINE
                    )
                )
        except Exception as e:
            print(f"Error ensuring collection: {e}")
            # Continue without memory if Qdrant is unavailable

    async def retrieve_memory_context(
        self,
        db: AsyncSession,
        org_id: str,
        user_id: Optional[str],
        query: str,
        thread_id: str,
        top_k: int = 5,
        current_provider: Optional[ProviderType] = None
    ) -> MemoryContext:
        """
        Retrieve relevant memory fragments for a query.

        This is the READ operation that enables cross-model context sharing.
        It retrieves memory fragments created by ANY model, not just the current one.
        
        Now includes access graph permission checks for fine-grained control.

        Args:
            db: Database session
            org_id: Organization ID
            user_id: User ID
            query: Current user query
            thread_id: Thread ID
            top_k: Number of fragments to retrieve per tier
            current_provider: Current provider/agent making the request (for access graph checks)

        Returns:
            MemoryContext with private and shared fragments
        """
        start_time = time.perf_counter()

        try:
            # Get query embedding
            query_vector = await self._get_embedding(query)

            # Retrieve from both tiers
            private_fragments = await self._retrieve_from_tier(
                db, org_id, user_id, query_vector, MemoryTier.PRIVATE, top_k, current_provider
            )

            shared_fragments = await self._retrieve_from_tier(
                db, org_id, user_id, query_vector, MemoryTier.SHARED, top_k, current_provider
            )

            retrieval_time_ms = (time.perf_counter() - start_time) * 1000

            return MemoryContext(
                private_fragments=private_fragments,
                shared_fragments=shared_fragments,
                total_fragments=len(private_fragments) + len(shared_fragments),
                retrieval_time_ms=retrieval_time_ms
            )

        except Exception as e:
            print(f"Error retrieving memory context: {e}")
            # Return empty context on error
            return MemoryContext(
                private_fragments=[],
                shared_fragments=[],
                total_fragments=0,
                retrieval_time_ms=0
            )

    async def _retrieve_from_tier(
        self,
        db: AsyncSession,
        org_id: str,
        user_id: Optional[str],
        query_vector: List[float],
        tier: MemoryTier,
        top_k: int,
        current_provider: Optional[ProviderType] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve fragments from a specific tier with access graph permission checks.
        
        Now includes fine-grained access control via AgentResourcePermission.
        """
        try:
            client = await self._get_client()

            # Build filter
            must_conditions = [
                {"key": "org_id", "match": {"value": org_id}},
                {"key": "tier", "match": {"value": tier.value}}
            ]

            # For private tier, filter by user
            if tier == MemoryTier.PRIVATE and user_id:
                must_conditions.append(
                    {"key": "user_id", "match": {"value": user_id}}
                )

            # Search in Qdrant (get more results to filter by permissions)
            search_result = await client.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=query_vector,
                query_filter={
                    "must": must_conditions
                },
                limit=top_k * 2,  # Get more to filter by permissions
                score_threshold=0.7  # Only return relevant matches
            )

            # Convert to dict format and apply access graph permissions
            fragments = []
            for hit in search_result:
                fragment_id = hit.id
                
                # Check access graph permissions if provider is specified
                if current_provider:
                    has_access = await self._check_fragment_access(
                        db, org_id, current_provider.value, fragment_id
                    )
                    if not has_access:
                        continue  # Skip fragments this agent cannot access
                
                fragment = {
                    "id": fragment_id,
                    "text": hit.payload.get("text", ""),
                    "tier": hit.payload.get("tier", ""),
                    "score": hit.score,
                    "provenance": hit.payload.get("provenance", {}),
                    "created_at": hit.payload.get("created_at", "")
                }
                fragments.append(fragment)
                
                # Stop when we have enough fragments
                if len(fragments) >= top_k:
                    break

            return fragments

        except Exception as e:
            print(f"Error retrieving from tier {tier}: {e}")
            return []
    
    async def _check_fragment_access(
        self,
        db: AsyncSession,
        org_id: str,
        agent_key: str,
        fragment_id: str
    ) -> bool:
        """
        Check if an agent has permission to access a specific memory fragment.
        
        Returns True if:
        - No explicit permission record exists (default allow)
        - Permission exists and can_access=True and not revoked
        Returns False if:
        - Permission exists and can_access=False
        - Permission exists and revoked_at is set
        """
        try:
            from sqlalchemy import and_
            from datetime import datetime, timezone
            
            # Check for explicit permission
            stmt = select(AgentResourcePermission).where(
                and_(
                    AgentResourcePermission.org_id == org_id,
                    AgentResourcePermission.agent_key == agent_key,
                    AgentResourcePermission.resource_key == fragment_id
                )
            )
            result = await db.execute(stmt)
            permission = result.scalar_one_or_none()
            
            if permission is None:
                # No explicit permission = default allow (backward compatible)
                return True
            
            # Check if revoked
            if permission.revoked_at is not None:
                return False
            
            # Return permission value
            return permission.can_access
            
        except Exception as e:
            print(f"Error checking fragment access: {e}")
            # Default to allow on error (fail open for availability)
            return True

    async def save_memory_from_turn(
        self,
        db: AsyncSession,
        org_id: str,
        user_id: Optional[str],
        thread_id: str,
        user_message: str,
        assistant_message: str,
        provider: ProviderType,
        model: str,
        scope: str
    ) -> int:
        """
        Extract and save memory fragments from a conversation turn.

        This is the WRITE operation that creates model-agnostic memory fragments.

        Args:
            db: Database session
            org_id: Organization ID
            user_id: User ID
            thread_id: Thread ID
            user_message: User's message
            assistant_message: Assistant's response
            provider: Provider that generated the response
            model: Model that generated the response
            scope: "private" or "shared"

        Returns:
            Number of fragments saved
        """
        try:
            # Extract insights from the turn
            insights = await self._extract_insights(
                user_message, assistant_message, provider, model
            )

            if not insights:
                return 0

            # Determine tier based on scope
            default_tier = MemoryTier.PRIVATE if scope == "private" else MemoryTier.SHARED

            saved_count = 0

            for insight in insights:
                # Use insight's tier if specified, otherwise use default
                tier = insight.tier if insight.tier else default_tier

                # Skip if not important enough
                if insight.importance < 0.5:
                    continue

                # Scrub PII if saving to shared tier
                text_to_save = insight.text
                if tier == MemoryTier.SHARED:
                    text_to_save = await self._scrub_pii(text_to_save)

                # Create memory fragment
                fragment_id = await self._save_fragment(
                    db=db,
                    org_id=org_id,
                    user_id=user_id,
                    text=text_to_save,
                    tier=tier,
                    provider=provider,
                    model=model,
                    thread_id=thread_id
                )

                if fragment_id:
                    saved_count += 1

            return saved_count

        except Exception as e:
            print(f"Error saving memory from turn: {e}")
            return 0

    async def _extract_insights(
        self,
        user_message: str,
        assistant_message: str,
        provider: ProviderType,
        model: str
    ) -> List[ExtractedInsight]:
        """
        Extract key insights from a conversation turn.

        This uses heuristics to identify important information worth saving.
        Could be enhanced with an LLM-based extraction in the future.
        """
        insights = []

        # Simple heuristic extraction
        # In a production system, you'd use an LLM to extract structured insights

        # If assistant message contains factual information (e.g., definitions, facts)
        if len(assistant_message) > 100:
            # Check for factual patterns
            factual_indicators = [
                "is defined as", "refers to", "means", "is a",
                "was founded", "was created", "was born", "in the year",
                "according to", "research shows", "studies indicate"
            ]

            has_factual_content = any(
                indicator in assistant_message.lower()
                for indicator in factual_indicators
            )

            if has_factual_content:
                # Extract key sentences
                sentences = assistant_message.split('. ')
                for sentence in sentences[:3]:  # Take first 3 sentences
                    if len(sentence) > 50:
                        insights.append(ExtractedInsight(
                            text=sentence.strip(),
                            tier=MemoryTier.SHARED,  # Factual info can be shared
                            importance=0.8
                        ))

        # If the query asks for a specific piece of information
        query_indicators = [
            "what is", "who is", "when", "where", "how to", "explain"
        ]

        is_info_seeking = any(
            indicator in user_message.lower()
            for indicator in query_indicators
        )

        if is_info_seeking and len(assistant_message) > 50:
            # Save a summary insight
            # Take first 200 chars as a summary
            summary = assistant_message[:200].strip()
            if not summary.endswith('.'):
                # Find last period
                last_period = summary.rfind('.')
                if last_period > 0:
                    summary = summary[:last_period + 1]

            insights.append(ExtractedInsight(
                text=f"Q: {user_message}\nA: {summary}",
                tier=MemoryTier.PRIVATE,  # Keep Q&A pairs private by default
                importance=0.7
            ))

        return insights

    async def _save_fragment(
        self,
        db: AsyncSession,
        org_id: str,
        user_id: Optional[str],
        text: str,
        tier: MemoryTier,
        provider: ProviderType,
        model: str,
        thread_id: str
    ) -> Optional[str]:
        """Save a single memory fragment to both DB and Qdrant."""
        try:
            # Generate content hash for deduplication
            content_hash = self._hash_content(text)

            # Check if fragment already exists
            existing_stmt = select(MemoryFragment).where(
                MemoryFragment.org_id == org_id,
                MemoryFragment.content_hash == content_hash
            )
            existing_result = await db.execute(existing_stmt)
            existing = existing_result.scalar_one_or_none()

            if existing:
                return None  # Already saved

            # Create provenance
            provenance = {
                "provider": provider.value,
                "model": model,
                "thread_id": thread_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Get embedding
            embedding = await self._get_embedding(text)

            # Generate vector ID
            vector_id = f"mem_{content_hash}"

            # Save to database
            fragment = MemoryFragment(
                org_id=org_id,
                user_id=user_id,
                text=text,
                tier=tier,
                vector_id=vector_id,
                provenance=provenance,
                content_hash=content_hash
            )
            db.add(fragment)
            await db.flush()

            # Save to Qdrant
            client = await self._get_client()
            await client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[
                    PointStruct(
                        id=vector_id,
                        vector=embedding,
                        payload={
                            "text": text,
                            "tier": tier.value,
                            "org_id": org_id,
                            "user_id": user_id or "",
                            "provenance": provenance,
                            "created_at": provenance["timestamp"]
                        }
                    )
                ]
            )

            await db.commit()

            return fragment.id

        except Exception as e:
            print(f"Error saving fragment: {e}")
            await db.rollback()
            return None

    async def _get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for text.

        Uses OpenAI's embedding API. Caches results for efficiency.
        """
        # Check cache
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self._embedding_cache:
            return self._embedding_cache[text_hash]

        try:
            # Import here to avoid circular dependency
            import httpx

            # Get OpenAI API key from settings
            # In production, you'd want a dedicated embedding key
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "text-embedding-3-small",  # Smaller, faster model
                        "input": text[:8000]  # Truncate if too long
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    embedding = data["data"][0]["embedding"]

                    # Cache it
                    self._embedding_cache[text_hash] = embedding

                    return embedding
                else:
                    # Fallback: return zero vector
                    return [0.0] * 1536

        except Exception as e:
            print(f"Error getting embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 1536

    def _hash_content(self, text: str) -> str:
        """Generate hash for content deduplication."""
        return hashlib.sha256(text.encode()).hexdigest()
    
    async def _scrub_pii(self, text: str) -> str:
        """
        Scrub PII (Personally Identifiable Information) from text before saving to shared memory.
        
        This is a basic implementation. In production, use a dedicated PII detection service
        (e.g., Presidio, AWS Comprehend, or an LLM-based detector).
        """
        import re
        
        # Email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', text)
        
        # Phone numbers (US format)
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE_REDACTED]', text)
        
        # Credit card numbers (basic pattern)
        text = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD_REDACTED]', text)
        
        # SSN (US format)
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', text)
        
        # IP addresses
        text = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_REDACTED]', text)
        
        # Common patterns that might indicate names (basic heuristic)
        # This is a simple approach - production should use NER models
        # Look for "My name is X" or "I'm X" patterns and redact
        text = re.sub(r'\b(?:my name is|i\'?m|call me)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b', 
                     r'\1 [NAME_REDACTED]', text, flags=re.IGNORECASE)
        
        return text
    
    async def expire_old_fragments(
        self,
        db: AsyncSession,
        org_id: Optional[str] = None,
        days_old: int = 90
    ) -> int:
        """
        Expire (soft delete) memory fragments older than specified days.
        
        Args:
            db: Database session
            org_id: Optional org ID to limit expiration to specific org
            days_old: Number of days after which fragments expire (default 90)
        
        Returns:
            Number of fragments expired
        """
        try:
            from datetime import timedelta
            from sqlalchemy import and_
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
            
            # Build query
            conditions = [
                MemoryFragment.created_at < cutoff_date
            ]
            if org_id:
                conditions.append(MemoryFragment.org_id == org_id)
            
            stmt = select(MemoryFragment).where(and_(*conditions))
            result = await db.execute(stmt)
            old_fragments = result.scalars().all()
            
            expired_count = 0
            client = await self._get_client()
            
            for fragment in old_fragments:
                # Delete from Qdrant
                try:
                    if fragment.vector_id:
                        await client.delete(
                            collection_name=self.COLLECTION_NAME,
                            points_selector=[fragment.vector_id]
                        )
                except Exception as e:
                    print(f"Error deleting fragment {fragment.id} from Qdrant: {e}")
                
                # Delete from database
                await db.delete(fragment)
                expired_count += 1
            
            await db.commit()
            return expired_count
            
        except Exception as e:
            print(f"Error expiring old fragments: {e}")
            await db.rollback()
            return 0


# Singleton instance
memory_service = MemoryService()
