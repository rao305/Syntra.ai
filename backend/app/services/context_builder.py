"""
Centralized Context Builder for LLM Provider Calls.

This module provides a single source of truth for building the messages array
that is sent to all LLM providers (Perplexity, OpenRouter, etc.).

Key principles:
1. All models receive the same rich context (history + memory + rewritten query)
2. Query rewriter sees full context to resolve pronouns correctly
3. Supermemory is consistently retrieved and injected
4. Short-term history and long-term memory are clearly separated
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import os
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message, MessageRole
from app.services.memory_service import memory_service, MemoryContext
from app.services.memory_guard import memory_guard
from app.services.query_rewriter import QueryRewriter
from app.services.topic_extractor import extract_topics_from_thread
from app.services.llm_context_extractor import resolve_references_in_query
from config import get_settings

import logging
logger = logging.getLogger(__name__)

settings = get_settings()

# Maximum number of conversation history messages to include
MAX_CONTEXT_MESSAGES = 20


@dataclass
class ContextualMessagesResult:
    """Result of building contextual messages."""
    messages: List[Dict[str, str]]
    rewritten_query: Optional[str] = None
    memory_snippet: Optional[str] = None
    short_term_history: List[Dict[str, str]] = None
    entities: List[Dict[str, Any]] = None
    is_ambiguous: bool = False
    disambiguation_data: Optional[Dict[str, Any]] = None


class ContextBuilder:
    """Centralized context builder for all LLM provider calls."""
    
    def __init__(self):
        self.query_rewriter = QueryRewriter()
    
    async def build_contextual_messages(
        self,
        db: AsyncSession,
        thread_id: str,
        user_id: Optional[str],
        org_id: str,
        latest_user_message: str,
        provider: Optional[Any] = None,
        use_memory: bool = True,
        use_query_rewriter: bool = True,
        base_system_prompt: Optional[str] = None,
        attachments: Optional[List[Dict[str, str]]] = None,
    ) -> ContextualMessagesResult:
        """
        Build contextual messages array for LLM provider calls.
        
        This is the SINGLE SOURCE OF TRUTH for building messages.
        All models (Perplexity, OpenRouter, etc.) should use this function.
        
        Steps:
        1. Load short-term history from database
        2. Retrieve long-term memory via supermemory (if enabled)
        3. Run query rewriter WITH full context
        4. Build final messages array with:
           - Base system prompt
           - Memory snippet (if available)
           - Short-term history
           - Original + rewritten user message
        
        Args:
            db: Database session
            thread_id: Thread ID
            user_id: User ID (for memory scoping)
            org_id: Organization ID
            latest_user_message: The latest user message
            provider: Provider type (for memory access graph)
            use_memory: Whether to retrieve memory context
            use_query_rewriter: Whether to rewrite the query
            base_system_prompt: Base system prompt (Syntra persona, etc.)
        
        Returns:
            ContextualMessagesResult with messages array and metadata
        """
        # STEP 1: Load short-term history with robust fallback
        # CRITICAL: This MUST succeed or we lose conversation context
        # CRITICAL: Normalize thread_id to string to ensure consistent key matching
        thread_id = str(thread_id)
        logger.info("[CTX] build_contextual_messages called with thread_id={thread_id!r}, type={type(thread_id).__name__}")
        
        try:
            short_term_history = await self._load_short_term_history(db, thread_id)
            if not isinstance(short_term_history, list):
                logger.warning("⚠️  History is not a list: {type(short_term_history)}, converting...")
                short_term_history = []
        except Exception as e:
            logger.error("❌ CRITICAL: Failed to load history: {e}")
            import traceback
            print(traceback.format_exc())
            short_term_history = []  # Graceful degradation
        
        # Validate history format
        validated_history = []
        for msg in short_term_history:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                validated_history.append(msg)
            else:
                logger.warning("⚠️  Invalid message format: {msg}, skipping...")
        short_term_history = validated_history
        
        logger.info("📚 Loaded {len(short_term_history)} validated history messages")
        logger.info("[CTX] Conversation history turns: {len(short_term_history)} (before adding current user message)")
        
        # STEP 2: Retrieve long-term memory via supermemory (if enabled)
        memory_snippet = None
        memory_context = None
        memory_enabled = bool(int(os.getenv("MEMORY_ENABLED", "0")))
        
        if use_memory and memory_enabled and not memory_guard.disabled:
            try:
                memory_context = await self._retrieve_memory_context(
                    db=db,
                    org_id=org_id,
                    user_id=user_id,
                    query=latest_user_message,
                    thread_id=thread_id,
                    provider=provider
                )
                
                if memory_context and memory_context.total_fragments > 0:
                    memory_snippet = self._format_memory_snippet(memory_context)
            except Exception as e:
                logger.error("⚠️  Memory retrieval error: {e}, continuing without memory")
        else:
            logger.info("[CTX] Memory retrieval disabled (memory_enabled={memory_enabled})")
        
        # STEP 3: Run query rewriter WITH full context (history + memory)
        # TEMPORARILY DISABLED FOR DEBUGGING - Focus on short-term history first
        # CRITICAL: The rewriter must see both short-term history AND memory snippet
        # This ensures pronouns like "his" resolve correctly to entities from previous turns
        rewritten_query = None
        is_ambiguous = False
        disambiguation_data = None
        entities = []
        
        # Enable query rewriter for better context resolution
        if use_query_rewriter:
            pass  # Commented out for now
        #     try:
        #         # Extract topics/entities from conversation history
        #         topics = extract_topics_from_thread(thread_id, short_term_history)
        #         entities = topics
        #         
        #         # Use LLM-based context extractor for comprehensive resolution
        #         # This works for ANY topic, not just hardcoded patterns
        #         # CRITICAL: Pass memory snippet to the rewriter so it has full context
        #         from app.services.llm_context_extractor import resolve_references_in_query
        #         
        #         # Build enhanced context that includes memory snippet
        #         enhanced_history = short_term_history.copy()
        #         if memory_snippet:
        #             # Prepend memory as a system message in the history context
        #             enhanced_history.insert(0, {
        #                 "role": "system",
        #                 "content": f"Long-term memory context:\n{memory_snippet}"
        #             })
        #         
        #         # CRITICAL: resolve_references_in_query returns (str, bool, Optional[Dict])
        #         # Handle the tuple return correctly
        #         try:
        #             rewritten_result, is_ambiguous, disambiguation_data = await resolve_references_in_query(
        #                 thread_id=thread_id,
        #                 user_message=latest_user_message,
        #                 conversation_history=enhanced_history  # Includes memory snippet
        #             )
        #             
        #             # rewritten_result is a string (the rewritten query)
        #             if rewritten_result and isinstance(rewritten_result, str) and not is_ambiguous:
        #                 rewritten_query = rewritten_result
        #             elif not rewritten_result or is_ambiguous:
        #                 # Fallback to rule-based rewriter if LLM rewriter didn't work
        #                 rewrite_result = self.query_rewriter.rewrite(
        #                     user_message=latest_user_message,
        #                     recent_turns=enhanced_history,  # Includes memory snippet
        #                     topics=topics
        #                 )
        #                 # rewrite_result is a dict
        #                 if isinstance(rewrite_result, dict):
        #                     rewritten_query = rewrite_result.get("rewritten", latest_user_message)
        #                     is_ambiguous = rewrite_result.get("AMBIGUOUS", False)
        #                     if is_ambiguous:
        #                         disambiguation_data = rewrite_result.get("disambiguation")
        #                 else:
        #                     # If rewrite_result is not a dict, use original message
        #                     rewritten_query = latest_user_message
        #         except ValueError as e:
        #             # Handle case where resolve_references_in_query returns wrong format
        #             logger.error("⚠️  Query rewriter return type error: {e}, using rule-based fallback")
        #             rewrite_result = self.query_rewriter.rewrite(
        #                 user_message=latest_user_message,
        #                 recent_turns=enhanced_history,
        #                 topics=topics
        #             )
        #             if isinstance(rewrite_result, dict):
        #                 rewritten_query = rewrite_result.get("rewritten", latest_user_message)
        #             else:
        #                 rewritten_query = latest_user_message
        #     except Exception as e:
        #         logger.error("⚠️  Query rewriter error: {e}, using original message")
        #         import traceback
        #         print(traceback.format_exc())
        #         rewritten_query = None
        
        # STEP 4: Build final messages array with validation
        try:
            messages = self._build_messages_array(
                base_system_prompt=base_system_prompt,
                memory_snippet=memory_snippet,
                short_term_history=short_term_history,
                original_user_message=latest_user_message,
                rewritten_query=rewritten_query,
                attachments=attachments
            )
            
            # CRITICAL VALIDATION: Ensure messages array is valid
            if not isinstance(messages, list):
                raise ValueError(f"Messages must be a list, got {type(messages)}")
            
            if len(messages) == 0:
                raise ValueError("Messages array cannot be empty")
            
            # Validate each message has required fields
            for i, msg in enumerate(messages):
                if not isinstance(msg, dict):
                    raise ValueError(f"Message {i} must be a dict, got {type(msg)}")
                if "role" not in msg:
                    raise ValueError(f"Message {i} missing 'role' field")
                if "content" not in msg:
                    raise ValueError(f"Message {i} missing 'content' field")
            
            # CRITICAL: Ensure history is included (not just system + current message)
            history_count = len([m for m in messages if m.get("role") in ["user", "assistant"]])
            if history_count < len(short_term_history):
                logger.warning("⚠️  WARNING: Only {history_count} history messages in array, expected {len(short_term_history)}")
                logger.info("   This may indicate a bug in _build_messages_array")
            
            # Ensure latest user message is present
            last_message = messages[-1] if messages else None
            if not last_message or last_message.get("role") != "user":
                logger.warning("⚠️  WARNING: Last message is not a user message, adding it...")
                messages.append({
                    "role": "user",
                    "content": latest_user_message
                })
            
        except Exception as e:
            logger.error("❌ CRITICAL: Failed to build messages array: {e}")
            import traceback
            print(traceback.format_exc())
            # FALLBACK: Build minimal valid messages array
            messages = [
                {"role": "system", "content": base_system_prompt or "You are a helpful assistant."},
                {"role": "user", "content": latest_user_message}
            ]
            # Try to include history if available
            for msg in short_term_history[-10:]:  # Last 10 messages
                messages.insert(-1, msg)  # Insert before last user message
        
        # CRITICAL LOGGING: Log what we're building
        self._log_context_build(
            thread_id=thread_id,
            messages=messages,
            rewritten_query=rewritten_query,
            memory_snippet=memory_snippet,
            short_term_history=short_term_history,
            is_ambiguous=is_ambiguous
        )
        
        return ContextualMessagesResult(
            messages=messages,
            rewritten_query=rewritten_query,
            memory_snippet=memory_snippet,
            short_term_history=short_term_history,
            entities=entities,
            is_ambiguous=is_ambiguous,
            disambiguation_data=disambiguation_data
        )
    
    def _log_context_build(
        self,
        thread_id: str,
        messages: List[Dict[str, str]],
        rewritten_query: Optional[str],
        memory_snippet: Optional[str],
        short_term_history: List[Dict[str, str]],
        is_ambiguous: bool
    ) -> None:
        """
        Log the context build for debugging and verification.
        
        This is CRITICAL for debugging the "his children" bug - it shows exactly
        what context is being sent to providers.
        """
        logger.info("\n{'='*80}")
        logger.info("🔧 CONTEXT BUILDER: thread_id={thread_id}")
        logger.info("{'='*80}")
        logger.info("Short-term history turns: {len(short_term_history)}")
        logger.info("Memory snippet present: {memory_snippet is not None}")
        if memory_snippet:
            logger.info("Memory snippet length: {len(memory_snippet)} chars")
        logger.info("Query rewritten: {rewritten_query is not None and rewritten_query != messages[-1].get('content', '')}")
        logger.info("Is ambiguous: {is_ambiguous}")
        logger.info("Total messages: {len(messages)}")
        logger.info("System messages: {len([m for m in messages if m.get('role') == 'system'])}")
        logger.info("Conversation history turns: {len([m for m in messages if m.get('role') in ['user', 'assistant']])}")
        
        # Detailed messages preview (matches TypeScript blueprint format)
        logger.info("\nMessages array preview:")
        for i, msg in enumerate(messages):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            if isinstance(content, str):
                preview = content[:120]
                logger.info("  [{i}] {role}: {preview}{'...' if len(content) > 120 else ''}")
            else:
                logger.info("  [{i}] {role}: [non-string content]")
        
        if rewritten_query:
            logger.info("\nRewritten query (first 120 chars): {rewritten_query[:120]}{'...' if len(rewritten_query) > 120 else ''}")
        
        # Show conversation history summary for verification
        logger.info("\nConversation history summary:")
        for i, turn in enumerate(short_term_history[-5:]):  # Last 5 turns
            role = turn.get('role', 'unknown')
            content = turn.get('content', '')
            preview = content[:80] if isinstance(content, str) else str(content)[:80]
            logger.info("  [{i}] {role}: {preview}{'...' if len(content) > 80 else ''}")
        
        logger.info("{'='*80}\n")
    
    async def _load_short_term_history(
        self,
        db: AsyncSession,
        thread_id: str,
        max_retries: int = 3,
        retry_delay: float = 0.1
    ) -> List[Dict[str, str]]:
        """
        Load short-term conversation history with robust fallback strategy.
        
        PRIORITY ORDER (most reliable first):
        1. In-memory thread storage (fastest, always up-to-date for current session)
        2. Database query (persistent, works across sessions)
        3. Empty list (graceful degradation)
        
        This ensures we ALWAYS have conversation history, even if DB is slow or unavailable.
        
        Args:
            db: Database session
            thread_id: Thread ID
            max_retries: Maximum retries for DB operations
            retry_delay: Initial delay between retries (exponential backoff)
        
        Returns:
            List of message dicts with role and content
        """
        import asyncio
        from app.services.threads_store import get_history, Turn
        
        # CRITICAL: Normalize thread_id to string to ensure consistent key matching
        thread_id = str(thread_id)
        
        logger.info("[CTX] _load_short_term_history called with thread_id={thread_id!r}, type={type(thread_id).__name__}")
        
        history = []
        
        # STRATEGY 1: Try in-memory thread storage first (FASTEST, most up-to-date)
        # CRITICAL: This is the primary source for conversation continuity
        # CRITICAL: Use get_history (read-only) - NEVER creates or overwrites threads
        try:
            logger.info("[CTX] Attempting to load from in-memory thread storage...")
            history_turns = get_history(thread_id, max_turns=MAX_CONTEXT_MESSAGES)
            logger.info("[CTX] get_history returned {len(history_turns)} turns for thread_id={thread_id!r}")
            
            if history_turns:
                # Convert in-memory turns to message format
                history = [
                    {
                        "role": turn.role,
                        "content": turn.content
                    }
                    for turn in history_turns
                ]
                logger.info("[CTX] short_term_history_len={len(history)}")
                logger.info("✅ Loaded {len(history)} messages from in-memory thread storage (thread_id: {thread_id})")
                if history:
                    # Validate we have both user and assistant messages
                    user_count = len([m for m in history if m.get("role") == "user"])
                    assistant_count = len([m for m in history if m.get("role") == "assistant"])
                    logger.info("   History breakdown: {user_count} user, {assistant_count} assistant messages")
                    return history
                else:
                    logger.warning("⚠️  In-memory thread storage exists but has no turns")
            else:
                logger.info("[CTX] No history found for thread_id={thread_id!r} (thread may not exist or has no turns)")
        except Exception as e:
            logger.error("⚠️  In-memory thread storage error: {e}, falling back to DB")
            import traceback
            print(traceback.format_exc())
        
        # STRATEGY 2: Fall back to database (with retry logic)
        for attempt in range(max_retries):
            try:
                from app.api.threads import _get_recent_messages
                
                prior_messages = await _get_recent_messages(db, thread_id)
                history = [
                    {"role": msg.role.value, "content": msg.content}
                    for msg in prior_messages
                ]
                
                if history:
                    logger.info("✅ Loaded {len(history)} messages from database (attempt {attempt + 1})")
                    # Also populate in-memory store for next time (only if empty)
                    try:
                        from app.services.threads_store import get_thread, add_turn, Turn
                        thread_mem = get_thread(thread_id)
                        # Only sync if thread doesn't exist or has no turns (don't overwrite existing turns)
                        if thread_mem is None or not thread_mem.turns:
                            for msg in history:
                                add_turn(thread_id, Turn(role=msg.get("role", "user"), content=msg.get("content", "")))
                    except Exception as e:
                        logger.warning("⚠️  Failed to populate in-memory store: {e}")
                    return history
                else:
                    logger.warning("⚠️  No messages found in DB for thread {thread_id}")
                    break  # No point retrying if DB returns empty
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning("⚠️  DB query failed (attempt {attempt + 1}/{max_retries}): {e}, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error("❌ DB query failed after {max_retries} attempts: {e}")
        
        # STRATEGY 3: Graceful degradation - return empty list
        logger.warning("⚠️  No conversation history available for thread {thread_id}, starting fresh")
        return []
    
    async def _retrieve_memory_context(
        self,
        db: AsyncSession,
        org_id: str,
        user_id: Optional[str],
        query: str,
        thread_id: str,
        provider: Optional[Any] = None
    ) -> Optional[MemoryContext]:
        """Retrieve long-term memory context from collaborative memory service."""
        import asyncio
        
        try:
            return await asyncio.wait_for(
                memory_service.retrieve_memory_context(
                    db=db,
                    org_id=org_id,
                    user_id=user_id,
                    query=query,
                    thread_id=thread_id,
                    top_k=3,
                    current_provider=provider
                ),
                timeout=2.0
            )
        except asyncio.TimeoutError:
            logger.warning("⚠️  Memory retrieval timeout, continuing without memory")
            return None
        except Exception as e:
            logger.error("⚠️  Memory retrieval error: {e}")
            return None
    
    def _format_memory_snippet(self, memory_context: MemoryContext, max_chars: int = 2000) -> str:
        """
        Format memory context into a concise system-level snippet.

        This shows both:
        - Episodic memories (from SuperMemory): User preferences, decisions, history
        - Knowledge base (from Qdrant): Domain knowledge, best practices

        This should be concise and placed before conversation history.
        """
        memory_content = "Long-term memory for this user and thread (summarized):\n\n"

        # EPISODIC MEMORIES (from SuperMemory)
        if memory_context.episodic_fragments:
            memory_content += "## Your Previous Interactions & Preferences:\n"
            for frag in memory_context.episodic_fragments:
                text = frag.get('text', '')
                # Truncate long text
                if len(text) > 150:
                    text = text[:147] + "..."
                memory_content += f"- {text}\n"
            memory_content += "\n"

        # KNOWLEDGE BASE (from Qdrant - private + shared)
        if memory_context.knowledge_fragments:
            memory_content += "## Relevant Knowledge Base:\n"
            for frag in memory_context.knowledge_fragments:
                text = frag.get('text', '')
                # Truncate long text
                if len(text) > 150:
                    text = text[:147] + "..."
                source_info = frag.get('source', 'knowledge')
                memory_content += f"- {text}\n"
            memory_content += "\n"

        # Legacy format support (if only private/shared are populated)
        if not memory_context.episodic_fragments and memory_context.private_fragments:
            memory_content += "## Your Previous Interactions:\n"
            for frag in memory_context.private_fragments:
                memory_content += f"- {frag['text']}\n"
            memory_content += "\n"

        if not memory_context.knowledge_fragments and memory_context.shared_fragments:
            memory_content += "## Shared Knowledge:\n"
            for frag in memory_context.shared_fragments:
                provider_info = frag.get('provenance', {}).get('provider', 'unknown')
                memory_content += f"- {frag['text']} (from {provider_info})\n"

        # Truncate if too long
        if len(memory_content) > max_chars:
            memory_content = memory_content[:max_chars] + "\n\n[truncated]"

        return memory_content
    
    def _build_messages_array(
        self,
        base_system_prompt: Optional[str],
        memory_snippet: Optional[str],
        short_term_history: List[Dict[str, str]],
        original_user_message: str,
        rewritten_query: Optional[str],
        attachments: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """
        Build the final messages array in the correct order.

        Structure:
        1. Base system prompt (Syntra persona, etc.)
        2. Memory snippet (long-term memory)
        3. Short-term history (recent conversation turns)
        4. Current user message (original + rewritten if available, with optional attachments)
        """
        messages: List[Dict[str, str]] = []

        # 1. Base system prompt (if provided)
        if base_system_prompt:
            messages.append({
                "role": "system",
                "content": base_system_prompt
            })

        # 2. Memory snippet (long-term memory)
        if memory_snippet:
            messages.append({
                "role": "system",
                "content": memory_snippet
            })

        # 3. Short-term history (recent conversation turns)
        # Limit to MAX_CONTEXT_MESSAGES to avoid token overflow
        limited_history = short_term_history[-MAX_CONTEXT_MESSAGES:]
        messages.extend(limited_history)

        # 4. Current user message with optional attachments
        # Handle multimodal content (text + images)
        has_images = attachments and any(a.get("type") == "image" for a in attachments)

        if has_images:
            # Build multimodal content array (OpenAI Vision API format)
            content_parts = []

            # Add text content if present
            if original_user_message.strip():
                # Format matches TypeScript blueprint: original + rewritten with separator
                user_message_parts = [f"Original user message:\n{original_user_message}"]

                if rewritten_query and rewritten_query != original_user_message:
                    user_message_parts.append(
                        f"Contextualized / rewritten query (use this as the primary query while still respecting the original intent):\n{rewritten_query}"
                    )

                content_parts.append({
                    "type": "text",
                    "text": "\n\n".join(user_message_parts)
                })
            else:
                # Image-only message: Add default prompt
                content_parts.append({
                    "type": "text",
                    "text": "Please analyze this image. Provide a brief (1-2 sentence) description of what you see, then ask the user: 'What would you like me to do with this image?' and suggest 2-3 common tasks (e.g., describe in detail, extract text, identify issues, etc.)."
                })

            # Add images
            for attachment in attachments:
                if attachment.get("type") == "image":
                    # Handle both URL and base64 data
                    if attachment.get("data"):
                        # Base64 data - convert to data URL
                        mime_type = attachment.get("mimeType", "image/png")
                        data_url = f"data:{mime_type};base64,{attachment.get('data')}"
                        content_parts.append({
                            "type": "image_url",
                            "image_url": {
                                "url": data_url
                            }
                        })
                    elif attachment.get("url"):
                        # Regular URL
                        content_parts.append({
                            "type": "image_url",
                            "image_url": {
                                "url": attachment.get("url", "")
                            }
                        })


            messages.append({
                "role": "user",
                "content": content_parts  # Multimodal content
            })
        else:
            # Text-only message (original behavior)
            user_message_parts = [f"Original user message:\n{original_user_message}"]

            if rewritten_query and rewritten_query != original_user_message:
                user_message_parts.append(
                    f"Contextualized / rewritten query (use this as the primary query while still respecting the original intent):\n{rewritten_query}"
                )

            messages.append({
                "role": "user",
                "content": "\n\n---\n\n".join(user_message_parts)
            })

        return messages


# Global instance
context_builder = ContextBuilder()

