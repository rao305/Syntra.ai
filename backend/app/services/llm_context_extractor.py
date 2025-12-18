"""LLM-based context extraction - works for ANY topic, not just hardcoded patterns.

This module provides LLM-powered entity extraction and query rewriting capabilities
that integrate with the coreference resolution service for comprehensive context-awareness.
"""
import json
from typing import List, Dict, Any, Optional, Tuple
from app.services.coreference_service import (

import logging
logger = logging.getLogger(__name__)
    get_conversation_context,
    Entity,
    resolve_vague_reference,
    should_ask_for_clarification,
)


async def extract_context_with_llm(
    conversation_history: List[Dict[str, str]],
    max_entities: int = 10
) -> List[Dict[str, Any]]:
    """
    Use LLM to extract important entities/topics from conversation.

    This works for ANY topic - people, places, products, concepts, etc.
    No hardcoded patterns needed.

    Args:
        conversation_history: Recent conversation turns
        max_entities: Maximum entities to extract

    Returns:
        List of entities: [{"name": "...", "type": "...", "context": "..."}]
    """
    if not conversation_history:
        return []

    # Build conversation context
    context_text = "\n".join([
        f"{turn.get('role', 'user')}: {turn.get('content', '')}"
        for turn in conversation_history[-8:]  # Last 8 turns
    ])

    # LLM prompt for entity extraction
    system_prompt = """You are a context analyzer. Extract important entities from the conversation.

Return a JSON array of entities. Each entity should have:
- "name": The entity name (person, place, product, concept, etc.)
- "type": Type of entity (person, place, product, concept, organization, etc.)
- "context": Brief context about why it's important

Only extract entities that are substantive topics of discussion.
Maximum {max_entities} entities.

Example output:
[
  {"name": "Albert Einstein", "type": "person", "context": "Physicist being discussed"},
  {"name": "Theory of Relativity", "type": "concept", "context": "Scientific theory mentioned"},
  {"name": "1905", "type": "date", "context": "Year Einstein published papers"}
]
"""

    user_prompt = f"""Analyze this conversation and extract important entities:

{context_text}

Return ONLY valid JSON array, no other text."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    try:
        # Use OpenAI GPT-4o-mini - fast and cheap for this task
        from config import get_settings
        from app.adapters.openai_adapter import call_openai
        settings = get_settings()
        api_key = settings.openai_api_key
        if not api_key:
            logger.warning("⚠️  No OpenAI API key, skipping LLM context extraction")
            return []

        response = await call_openai(
            messages=messages,
            model="gpt-4o-mini",  # Fast and cheap model for context extraction
            api_key=api_key,
            max_tokens=500
        )

        # Parse JSON response
        content = response.content.strip()

        # Clean up markdown code blocks if present
        if content.startswith("```"):
            # Remove ```json and ``` markers
            content = content.replace("```json", "").replace("```", "").strip()

        entities = json.loads(content)

        # Validate structure
        if not isinstance(entities, list):
            logger.warning("⚠️  LLM returned non-list: {type(entities)}")
            return []

        # Ensure each entity has required fields
        validated = []
        for entity in entities[:max_entities]:
            if isinstance(entity, dict) and "name" in entity and "type" in entity:
                validated.append({
                    "name": entity["name"],
                    "type": entity.get("type", "unknown"),
                    "context": entity.get("context", "")
                })

        return validated

    except json.JSONDecodeError as e:
        logger.warning("⚠️  Failed to parse LLM response as JSON: {e}")
        return []
    except Exception as e:
        logger.error("⚠️  LLM context extraction error: {e}")
        return []


async def rewrite_query_with_llm(
    user_message: str,
    conversation_history: List[Dict[str, str]],
    entities: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Use LLM to rewrite user query to be self-contained.

    This handles ANY pronoun or reference, not just hardcoded patterns.

    Args:
        user_message: User's latest message
        conversation_history: Recent conversation
        entities: Entities extracted from conversation

    Returns:
        {
            "rewritten": "self-contained query",
            "needs_clarification": true/false,
            "clarification_question": "...",
            "options": [...]
        }
    """
    # Build context
    context_text = "\n".join([
        f"{turn.get('role', 'user')}: {turn.get('content', '')}"
        for turn in conversation_history[-5:]
    ])

    entities_text = "\n".join([
        f"- {e['name']} ({e['type']}): {e.get('context', '')}"
        for e in entities
    ])

    system_prompt = """You are a query rewriter. Your job is to make user queries self-contained by resolving pronouns and references.

Rules:
1. If the user's message has pronouns (it, that, they, he, she, etc.), replace them with specific entities
2. Use the conversation context and entity list to determine what the pronouns refer to
3. If ambiguous, set needs_clarification=true and provide options
4. If clear, just rewrite the query to be self-contained

Return JSON:
{
  "rewritten": "the self-contained query",
  "needs_clarification": false,
  "reasoning": "brief explanation of what you did"
}

OR if ambiguous:
{
  "rewritten": "<original>",
  "needs_clarification": true,
  "clarification_question": "Which one did you mean?",
  "options": ["Option 1", "Option 2"],
  "reasoning": "why it's ambiguous"
}
"""

    user_prompt = f"""Recent conversation:
{context_text}

Entities mentioned:
{entities_text}

User's latest message: "{user_message}"

Rewrite this message to be self-contained. Return ONLY valid JSON."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    try:
        from config import get_settings
        from app.adapters.openai_adapter import call_openai
        settings = get_settings()
        api_key = settings.openai_api_key
        if not api_key:
            return {
                "rewritten": user_message,
                "needs_clarification": False,
                "reasoning": "No OpenAI API key available"
            }

        response = await call_openai(
            messages=messages,
            model="gpt-4o-mini",  # Fast and cheap model for query rewriting
            api_key=api_key,
            max_tokens=500
        )

        # Parse response
        content = response.content.strip()
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()

        result = json.loads(content)

        # Log the rewrite
        if result.get("rewritten") != user_message:
            logger.info("✏️  LLM rewrite: {user_message[:50]}... → {result.get('rewritten', '')[:50]}...")
            if result.get("reasoning"):
                logger.info("   Reasoning: {result['reasoning']}")

        return result

    except Exception as e:
        logger.error("⚠️  LLM query rewrite error: {e}")
        return {
            "rewritten": user_message,
            "needs_clarification": False,
            "reasoning": f"Error: {e}"
        }


async def extract_and_save_entities(
    thread_id: str,
    conversation_history: List[Dict[str, str]],
    max_entities: int = 10
) -> List[Entity]:
    """
    Extract entities from conversation and save them to the coreference service.

    Args:
        thread_id: Thread ID for entity tracking
        conversation_history: Recent conversation turns
        max_entities: Maximum entities to extract

    Returns:
        List of Entity objects saved to the coreference service
    """
    # Get conversation context
    context = get_conversation_context(thread_id)

    # Extract entities using LLM
    entity_dicts = await extract_context_with_llm(conversation_history, max_entities)

    # Convert to Entity objects and save
    entities = []
    for entity_dict in entity_dicts:
        entity = Entity(
            name=entity_dict["name"],
            type=entity_dict.get("type", "unknown"),
            context=entity_dict.get("context", "")
        )
        context.add_entity(entity)
        entities.append(entity)

    return entities


async def resolve_references_in_query(
    thread_id: str,
    user_message: str,
    conversation_history: List[Dict[str, str]]
) -> Tuple[str, bool, Optional[Dict[str, Any]]]:
    """
    Resolve vague references in user query using both rule-based and LLM approaches.

    This combines:
    1. Rule-based coreference resolution (fast, for clear cases)
    2. LLM-based query rewriting (comprehensive, handles complex cases)

    Args:
        thread_id: Thread ID
        user_message: User's query with potential references
        conversation_history: Recent conversation

    Returns:
        (resolved_query, needs_clarification, disambiguation_data)
    """
    # Get conversation context
    context = get_conversation_context(thread_id)

    # Extract and save entities first
    entities = await extract_and_save_entities(thread_id, conversation_history)

    # Convert entities to dict format for LLM
    entity_dicts = [
        {
            "name": e.name,
            "type": e.type,
            "context": e.context
        }
        for e in entities
    ]

    # Use LLM to rewrite query
    rewrite_result = await rewrite_query_with_llm(
        user_message=user_message,
        conversation_history=conversation_history,
        entities=entity_dicts
    )

    # Check if clarification needed
    needs_clarification = rewrite_result.get("needs_clarification", False)
    disambiguation_data = None

    if needs_clarification:
        disambiguation_data = {
            "question": rewrite_result.get("clarification_question", "Which did you mean?"),
            "options": rewrite_result.get("options", []),
            "reasoning": rewrite_result.get("reasoning", "")
        }

    resolved_query = rewrite_result.get("rewritten", user_message)

    return resolved_query, needs_clarification, disambiguation_data
