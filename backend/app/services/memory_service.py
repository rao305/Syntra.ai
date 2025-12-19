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

import logging
logger = logging.getLogger(__name__)

settings = get_settings()


@dataclass
class MemoryContext:
    """Context retrieved from memory for a query."""

    # Hybrid memory sources
    episodic_fragments: List[Dict[str, Any]]  # From SuperMemory (user-centric)
    knowledge_fragments: List[Dict[str, Any]]  # From Qdrant (domain knowledge)

    # Legacy fields (kept for backward compatibility)
    private_fragments: List[Dict[str, Any]]  # Qdrant private tier
    shared_fragments: List[Dict[str, Any]]  # Qdrant shared tier

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
            logger.error("Error ensuring collection: {e}")
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
        Retrieve relevant memory fragments for a query from BOTH SuperMemory and Qdrant.

        This is the READ operation for the HYBRID memory system:
        - SuperMemory: Episodic (user-centric) memories
        - Qdrant: Knowledge base (domain-specific) memories

        Args:
            db: Database session
            org_id: Organization ID
            user_id: User ID
            query: Current user query
            thread_id: Thread ID
            top_k: Number of fragments to retrieve per source
            current_provider: Current provider/agent making the request

        Returns:
            MemoryContext with episodic and knowledge fragments
        """
        start_time = time.perf_counter()
        import asyncio

        try:
            # Query both sources in parallel for performance
            supermemory_task = self._query_supermemory(user_id, query, top_k)
            qdrant_tasks = [
                self._retrieve_from_tier(
                    db, org_id, user_id, None, MemoryTier.PRIVATE, top_k, current_provider, query
                ),
                self._retrieve_from_tier(
                    db, org_id, user_id, None, MemoryTier.SHARED, top_k, current_provider, query
                )
            ]

            # Execute all queries in parallel
            results = await asyncio.gather(
                supermemory_task,
                *qdrant_tasks,
                return_exceptions=True
            )

            episodic_fragments = results[0] if not isinstance(results[0], Exception) else []
            private_fragments = results[1] if not isinstance(results[1], Exception) else []
            shared_fragments = results[2] if not isinstance(results[2], Exception) else []

            # Log any errors
            if isinstance(results[0], Exception):
                logger.error("[Memory] SuperMemory error: {results[0]}")
            if isinstance(results[1], Exception):
                logger.error("[Memory] Qdrant private tier error: {results[1]}")
            if isinstance(results[2], Exception):
                logger.error("[Memory] Qdrant shared tier error: {results[2]}")

            retrieval_time_ms = (time.perf_counter() - start_time) * 1000

            return MemoryContext(
                episodic_fragments=episodic_fragments,
                knowledge_fragments=private_fragments + shared_fragments,
                private_fragments=private_fragments,  # Legacy field
                shared_fragments=shared_fragments,    # Legacy field
                total_fragments=len(episodic_fragments) + len(private_fragments) + len(shared_fragments),
                retrieval_time_ms=retrieval_time_ms
            )

        except Exception as e:
            logger.error("Error retrieving memory context: {e}")
            # Return empty context on error
            return MemoryContext(
                episodic_fragments=[],
                knowledge_fragments=[],
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
        query_vector: Optional[List[float]],
        tier: MemoryTier,
        top_k: int,
        current_provider: Optional[ProviderType] = None,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve fragments from a specific pgvector tier with access graph permission checks.

        Uses PostgreSQL pgvector for similarity search with HNSW indexing.
        """
        try:
            from sqlalchemy import and_, text as sql_text
            import json

            # Get embedding if not provided
            if query_vector is None and query:
                query_vector = await self._get_embedding(query)
            elif query_vector is None:
                return []

            # Convert query vector to pgvector format
            query_vector_str = json.dumps(query_vector)

            # Build SQL query with pgvector cosine distance
            # Using raw SQL because SQLAlchemy may not have native pgvector support
            sql = f"""
                SELECT id, org_id, user_id, text, tier, embedding, provenance, created_at,
                       (embedding <-> '{query_vector_str}'::vector) AS distance
                FROM memory_fragments
                WHERE org_id = :org_id
                  AND tier = :tier
                  AND embedding IS NOT NULL
            """

            # Add user filter for private tier
            if tier == MemoryTier.PRIVATE and user_id:
                sql += " AND user_id = :user_id"

            # Order by distance and limit
            sql += f"""
                ORDER BY distance ASC
                LIMIT {top_k * 2}
            """

            # Build parameters
            params = {
                "org_id": org_id,
                "tier": tier.value,
            }
            if tier == MemoryTier.PRIVATE and user_id:
                params["user_id"] = user_id

            # Execute raw SQL query
            result = await db.execute(sql_text(sql), params)
            rows = result.all()

            # Convert to dict format and apply access graph permissions
            fragments = []
            for row in rows:
                row_dict = row._mapping
                fragment_id = row_dict["id"]
                distance = row_dict["distance"]

                # Check access graph permissions if provider is specified
                if current_provider:
                    has_access = await self._check_fragment_access(
                        db, org_id, current_provider.value, fragment_id
                    )
                    if not has_access:
                        continue  # Skip fragments this agent cannot access

                # Convert distance to similarity score (1 - distance)
                # Cosine distance ranges from 0 to 2, where 0 = identical, 2 = opposite
                similarity_score = max(0, 1 - distance)

                fragment_dict = {
                    "id": fragment_id,
                    "text": row_dict["text"],
                    "tier": row_dict["tier"],
                    "score": float(similarity_score),
                    "provenance": row_dict["provenance"],
                    "created_at": row_dict["created_at"].isoformat() if row_dict["created_at"] else "",
                    "source": "pgvector"
                }
                fragments.append(fragment_dict)

                # Stop when we have enough fragments
                if len(fragments) >= top_k:
                    break

            return fragments

        except Exception as e:
            logger.error(f"Error retrieving from tier {tier}: {e}")
            import traceback
            traceback.print_exc()
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
            logger.error("Error checking fragment access: {e}")
            # Default to allow on error (fail open for availability)
            return True

    async def _query_supermemory(
        self,
        user_id: Optional[str],
        query: str,
        top_k: int = 8
    ) -> List[Dict[str, Any]]:
        """
        Query SuperMemory for episodic (user-centric) memories.

        Args:
            user_id: User identifier for SuperMemory scoping
            query: Search query
            top_k: Number of memories to retrieve

        Returns:
            List of episodic memory fragments with source marker
        """
        if not user_id:
            return []

        try:
            from app.integrations.supermemory_client import supermemory_client

            # Check if SuperMemory is configured
            if not settings.supermemory_api_key:
                logger.info("[Memory] SuperMemory not configured, skipping episodic memory retrieval")
                return []

            # Query SuperMemory
            memories = await supermemory_client.search_memories(
                user_id=user_id,
                query=query,
                limit=top_k
            )

            # Format as memory fragments
            formatted = [
                {
                    "id": m.get("id", ""),
                    "text": m.get("text", ""),
                    "score": m.get("relevance_score", 0.5),
                    "tags": m.get("tags", []),
                    "created_at": m.get("created_at", ""),
                    "source": "supermemory"
                }
                for m in memories
            ]

            logger.info("[Memory] Retrieved {len(formatted)} episodic memories from SuperMemory")
            return formatted

        except Exception as e:
            logger.error("[Memory] SuperMemory query error: {e}")
            return []

    def classify_memory_tier(
        self,
        user_message: str,
        assistant_message: str,
        insight_text: str
    ) -> MemoryTier:
        """
        Classify an insight into episodic vs. knowledge base tier.

        Episodic indicators:
        - Personal preferences ("I prefer...", "I like...", "I use...")
        - User decisions and actions
        - File/project references
        - User-specific context

        Knowledge indicators:
        - Factual information ("is defined as", "means")
        - Patterns discovered
        - API behavior, best practices
        - Generalizable findings

        Args:
            user_message: The original user message
            assistant_message: The assistant's response
            insight_text: The extracted insight to classify

        Returns:
            MemoryTier.PRIVATE for episodic, MemoryTier.SHARED for knowledge
        """
        episodic_indicators = [
            "i prefer", "i like", "i use", "i work with", "i remember",
            "my project", "my file", "my code", "my preference", "my workflow",
            "decided to", "going to", "will use", "started using",
            "found helpful", "my setup", "my environment"
        ]

        knowledge_indicators = [
            "is defined as", "means", "refers to", "is a", "pattern",
            "best practice", "approach", "method", "technique", "implementation",
            "algorithm", "structure", "design", "architecture", "optimization",
            "performance", "efficiency", "trade-off", "research shows"
        ]

        user_lower = user_message.lower()
        insight_lower = insight_text.lower()

        # Check episodic indicators
        is_episodic = any(ind in insight_lower for ind in episodic_indicators)

        # Check knowledge indicators
        is_knowledge = any(ind in insight_lower for ind in knowledge_indicators)

        # Decision logic
        if is_episodic and not is_knowledge:
            return MemoryTier.PRIVATE
        elif is_knowledge:
            return MemoryTier.SHARED
        elif "what is" in user_lower or "explain" in user_lower:
            # Info-seeking questions tend to produce knowledge
            return MemoryTier.SHARED
        else:
            # Default to episodic for personal context
            return MemoryTier.PRIVATE

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
            logger.error("Error saving memory from turn: {e}")
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
        """Save a single memory fragment to PostgreSQL with pgvector embedding."""
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

            # Save directly to PostgreSQL with pgvector embedding
            fragment = MemoryFragment(
                org_id=org_id,
                user_id=user_id,
                text=text,
                tier=tier,
                embedding=embedding,  # Store embedding directly in pgvector column
                vector_id=None,  # No longer using Qdrant
                provenance=provenance,
                content_hash=content_hash
            )
            db.add(fragment)
            await db.commit()
            await db.refresh(fragment)

            logger.info(f"Saved memory fragment to pgvector: {fragment.id}")
            return fragment.id

        except Exception as e:
            logger.error(f"Error saving fragment: {e}")
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
            logger.error("Error getting embedding: {e}")
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
                    logger.error("Error deleting fragment {fragment.id} from Qdrant: {e}")
                
                # Delete from database
                await db.delete(fragment)
                expired_count += 1
            
            await db.commit()
            return expired_count
            
        except Exception as e:
            logger.error("Error expiring old fragments: {e}")
            await db.rollback()
            return 0


# Singleton instance
memory_service = MemoryService()
