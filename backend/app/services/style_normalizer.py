"""Style Normalizer: Ensures DAC voice consistency.

Post-processes responses to maintain DAC persona, especially for social_chat
intents where providers might return dictionary-style definitions.
"""
from typing import Callable, Awaitable
from app.services.provider_dispatch import call_provider_adapter_streaming
from app.models.provider_key import ProviderType

import logging
logger = logging.getLogger(__name__)


async def normalize_to_dac_voice(
    raw_text: str,
    llm_call: Callable[[str, int], Awaitable[str]],
    max_tokens: int = 120
) -> str:
    """
    Rewrite response to sound like DAC: warm, conversational, concise.
    
    Args:
        raw_text: Raw response from provider
        llm_call: Async function that takes (prompt, max_tokens) and returns text
        max_tokens: Max tokens for normalization
    
    Returns:
        Normalized text in DAC voice
    """
    prompt = (
        "Rewrite the assistant reply to sound like DAC: warm, conversational, concise; "
        "no citations like [2][4][8]; no dictionary definitions unless asked. "
        "Keep it natural and friendly.\n\n"
        f"Reply:\n{raw_text}"
    )
    
    try:
        normalized = await llm_call(prompt, max_tokens)
        return normalized.strip()
    except Exception as e:
        # If normalization fails, return original
        logger.info("Style normalization failed: {e}")
        return raw_text


def looks_like_dictionary_definition(text: str) -> bool:
    """
    Heuristic to detect dictionary-style definitions.
    
    Checks if text starts with quoted phrase followed by "is".
    """
    text_lstrip = text.lstrip()
    if len(text_lstrip) < 10:
        return False
    
    # Check for quoted phrase at start
    starts_with_quote = text_lstrip.startswith(('"', "'"))
    
    # Check for " is " pattern in first 60 chars
    has_is_pattern = " is " in text_lstrip[:60].lower()
    
    return starts_with_quote and has_is_pattern


async def normalize_if_needed(
    raw_text: str,
    intent: str,
    llm_call: Callable[[str, int], Awaitable[str]]
) -> str:
    """
    Normalize text if it looks like a dictionary definition (especially for social_chat).
    
    Args:
        raw_text: Raw response text
        intent: Detected intent
        llm_call: Async function for LLM call
    
    Returns:
        Normalized text if needed, otherwise original
    """
    # Always normalize social_chat responses
    if intent == "social_chat":
        return await normalize_to_dac_voice(raw_text, llm_call)
    
    # Normalize other intents if they look like definitions
    if looks_like_dictionary_definition(raw_text):
        return await normalize_to_dac_voice(raw_text, llm_call)
    
    return raw_text

