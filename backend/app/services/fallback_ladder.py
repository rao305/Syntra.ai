"""Fallback Ladder for Production Reliability.

Implements cascading fallback strategy: primary → failover → final
with retries and graceful error handling.
"""
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum
import asyncio
import random
import time

from app.models.provider_key import ProviderType
from app.services.model_registry import validate_and_get_model


class IntentType(str, Enum):
    """Intent types for routing."""
    CODING_HELP = "coding_help"
    QA_RETRIEVAL = "qa_retrieval"
    REASONING_MATH = "reasoning/math"
    SOCIAL_CHAT = "social_chat"
    EDITING_WRITING = "editing/writing"
    AMBIGUOUS = "ambiguous_or_other"


# Fallback ladder configuration
# NOTE: Ordered by speed + quality for fast fallback switching
# If primary is slow, system automatically tries next provider within 6 seconds
FALLBACK_LADDERS: Dict[IntentType, List[Tuple[ProviderType, str, str]]] = {
    IntentType.CODING_HELP: [
        (ProviderType.GEMINI, "gemini-2.5-flash", "Primary: Fast code generation (Fastest)"),
        (ProviderType.OPENAI, "gpt-4o-mini", "Fallback: Reliable reasoning (Fast)"),
        (ProviderType.KIMI, "moonshot-v1-32k", "Backup: Cost-effective alternative"),
        (ProviderType.PERPLEXITY, "sonar", "Final: General fallback"),
    ],
    IntentType.QA_RETRIEVAL: [
        (ProviderType.GEMINI, "gemini-2.5-flash", "Primary: Fast reasoning (fastest, if Perplexity slow)"),
        (ProviderType.PERPLEXITY, "sonar", "Fallback: Search-augmented"),
        (ProviderType.OPENAI, "gpt-4o-mini", "Final: General fallback"),
    ],
    IntentType.REASONING_MATH: [
        (ProviderType.GEMINI, "gemini-2.5-flash", "Primary: Fast (switch from slow OpenAI)"),
        (ProviderType.OPENAI, "gpt-4o-mini", "Fallback: Superior reasoning (but slower)"),
        (ProviderType.PERPLEXITY, "sonar", "Final: General fallback"),
    ],
    IntentType.SOCIAL_CHAT: [
        (ProviderType.GEMINI, "gemini-2.5-flash", "Primary: Fast chat (Fastest)"),
        (ProviderType.OPENAI, "gpt-4o-mini", "Fallback: Conversational chat (slower)"),
        (ProviderType.PERPLEXITY, "sonar", "Final: General fallback"),
    ],
    IntentType.EDITING_WRITING: [
        (ProviderType.GEMINI, "gemini-2.5-flash", "Primary: Fast editing (switch from slow Perplexity)"),
        (ProviderType.PERPLEXITY, "sonar", "Fallback: Web-grounded editing"),
        (ProviderType.OPENAI, "gpt-4o-mini", "Final: General fallback"),
    ],
    IntentType.AMBIGUOUS: [
        (ProviderType.GEMINI, "gemini-2.5-flash", "Primary: Fast (handles vague requests, Fastest)"),
        (ProviderType.OPENAI, "gpt-4o-mini", "Fallback: Good reasoning"),
        (ProviderType.PERPLEXITY, "sonar", "Final: Web-grounded"),
    ],
}


async def get_fallback_chain(intent: str) -> List[Tuple[ProviderType, str, str]]:
    """
    Get fallback chain for an intent.
    
    Returns list of (provider, model, reason) tuples in order of preference.
    """
    try:
        intent_enum = IntentType(intent)
        return FALLBACK_LADDERS.get(intent_enum, FALLBACK_LADDERS[IntentType.AMBIGUOUS])
    except ValueError:
        # Unknown intent, use ambiguous fallback
        return FALLBACK_LADDERS[IntentType.AMBIGUOUS]


def jittered_backoff(attempt: int, base_delay: float = 0.5) -> float:
    """Calculate jittered backoff delay."""
    delay = base_delay * (2 ** attempt)
    jitter = random.uniform(0, delay * 0.3)
    return delay + jitter


async def call_with_fallback(
    call_fn,
    fallback_chain: List[Tuple[ProviderType, str, str]],
    timeout_seconds: float = 6.0,
    max_retries: int = 0
) -> Dict[str, Any]:
    """
    Call a function with fallback ladder and retries.

    Intelligently switches to faster providers if current one is slow.

    Args:
        call_fn: Async function that takes (provider, model, ...) and returns result
        fallback_chain: List of (provider, model, reason) tuples
        timeout_seconds: Timeout per attempt (reduced from 12s to 6s for faster fallback)
        max_retries: Maximum retries per provider (reduced from 1 to 0 for faster switching)

    Returns:
        Dict with: {text, provider, model, usage, latency_ms, error, fallback_used}
    """
    last_error = None
    fallback_used = False
    start_time = time.perf_counter()
    
    for provider, model, reason in fallback_chain:
        # Validate model
        try:
            validated_model = validate_and_get_model(provider, model)
        except ValueError:
            last_error = f"Invalid model {model} for provider {provider.value}"
            continue
        
        # Try with retries
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    # Jittered backoff before retry
                    delay = jittered_backoff(attempt - 1)
                    await asyncio.sleep(delay)
                
                # Call with timeout
                result = await asyncio.wait_for(
                    call_fn(provider, validated_model),
                    timeout=timeout_seconds
                )
                
                # Success - return result dict
                latency_ms = (time.perf_counter() - start_time) * 1000

                # Extract TTFS from result if available
                ttfs_ms = None
                if isinstance(result, dict):
                    ttfs_ms = result.get("ttfs_ms", None)

                # Result is a dict with stream iterator and usage
                if isinstance(result, dict) and "stream" in result:
                    # Streaming result
                    return {
                        "provider": provider.value,
                        "model": validated_model,
                        "stream": result["stream"],  # Async iterator
                        "usage": result.get("usage", {}),
                        "raw": result.get("raw", result.get("usage", {})),
                        "latency_ms": latency_ms,
                        "ttfs_ms": ttfs_ms,  # Time to first token
                        "error": None,
                        "fallback_used": fallback_used
                    }
                else:
                    # Non-streaming result (fallback)
                    text = result.get("content", "") if isinstance(result, dict) else str(result)
                    usage = result.get("raw", {}) if isinstance(result, dict) else {}

                    # Wrap text as single-chunk async iterator
                    async def single_chunk():
                        yield text

                    return {
                        "provider": provider.value,
                        "model": validated_model,
                        "stream": single_chunk(),
                        "usage": usage,
                        "raw": usage,
                        "latency_ms": latency_ms,
                        "ttfs_ms": ttfs_ms,  # Time to first token
                        "error": None,
                        "fallback_used": fallback_used
                    }
                
            except asyncio.TimeoutError:
                last_error = f"Timeout after {timeout_seconds}s"
                if attempt < max_retries:
                    continue  # Retry
                break  # Move to next provider
                
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    continue  # Retry
                break  # Move to next provider
        
        # Mark that we're using fallback
        if not fallback_used and provider != fallback_chain[0][0]:
            fallback_used = True
    
    # All providers failed - return graceful error
    latency_ms = (time.perf_counter() - start_time) * 1000
    return {
        "text": None,
        "provider": None,
        "model": None,
        "usage": {},
        "latency_ms": latency_ms,
        "error": last_error or "All providers failed",
        "fallback_used": fallback_used
    }

