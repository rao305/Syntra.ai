"""Routes provider calls to the right adapter."""
from __future__ import annotations

import os
from typing import List, Dict, AsyncIterator

from app.adapters.base import ProviderResponse
from app.adapters.perplexity import call_perplexity, call_perplexity_streaming
from app.adapters.openai_adapter import call_openai, call_openai_streaming
from app.adapters.gemini import call_gemini, call_gemini_streaming
from app.adapters.openrouter import call_openrouter, call_openrouter_streaming
from app.adapters.kimi import call_kimi, call_kimi_streaming
from app.models.provider_key import ProviderType

# Default completion budgets per provider (tokens)
# Based on model capabilities and API limits
DEFAULT_COMPLETION_TOKENS = {
    ProviderType.PERPLEXITY: 8192,   # Increased from 4096 to allow longer responses
    ProviderType.OPENAI: 8192,       # Increased from 4096 to allow longer responses
    ProviderType.GEMINI: 16384,      # Increased from 8192 for better coverage
    ProviderType.OPENROUTER: 8192,   # Increased from 4096 to allow longer responses
    ProviderType.KIMI: 8192,         # Increased from 4096 to allow longer responses
}


def _completion_budget(provider: ProviderType) -> int:
    """
    Determine the completion token budget for a provider.

    Allows overriding via environment variable, e.g. OPENAI_MAX_OUTPUT_TOKENS=6000.
    """
    env_key = f"{provider.value.upper()}_MAX_OUTPUT_TOKENS"
    override = os.getenv(env_key)
    if override:
        try:
            value = int(override)
            if value > 0:
                return value
        except ValueError:
            pass
    return DEFAULT_COMPLETION_TOKENS.get(provider, 2048)


async def call_provider_adapter(
    provider: ProviderType,
    model: str,
    messages: List[Dict[str, str]],
    api_key: str,
    max_tokens: int = None,
    **kwargs
) -> ProviderResponse:
    """Call the appropriate adapter."""
    if max_tokens is None:
        max_tokens = _completion_budget(provider)

    if provider == ProviderType.PERPLEXITY:
        return await call_perplexity(messages, model, api_key, max_tokens=max_tokens)

    if provider == ProviderType.OPENAI:
        return await call_openai(messages, model, api_key, max_tokens=max_tokens)

    if provider == ProviderType.GEMINI:
        return await call_gemini(messages, model, api_key, max_output_tokens=max_tokens)

    if provider == ProviderType.OPENROUTER:
        return await call_openrouter(messages, model, api_key, max_tokens=max_tokens)

    if provider == ProviderType.KIMI:
        return await call_kimi(messages, model, api_key, max_tokens=max_tokens)

    raise ValueError(f"Unsupported provider: {provider.value}")


async def call_provider_adapter_streaming(
    provider: ProviderType,
    model: str,
    messages: List[Dict[str, str]],
    api_key: str,
    max_tokens: int = None,
    **kwargs
) -> AsyncIterator[Dict]:
    """Call the appropriate adapter with streaming."""
    if max_tokens is None:
        max_tokens = _completion_budget(provider)

    if provider == ProviderType.PERPLEXITY:
        async for chunk in call_perplexity_streaming(messages, model, api_key, max_tokens=max_tokens):
            yield chunk

    elif provider == ProviderType.OPENAI:
        async for chunk in call_openai_streaming(messages, model, api_key, max_tokens=max_tokens):
            yield chunk

    elif provider == ProviderType.GEMINI:
        async for chunk in call_gemini_streaming(messages, model, api_key, max_output_tokens=max_tokens):
            yield chunk

    elif provider == ProviderType.OPENROUTER:
        async for chunk in call_openrouter_streaming(messages, model, api_key, max_tokens=max_tokens):
            yield chunk

    elif provider == ProviderType.KIMI:
        async for chunk in call_kimi_streaming(messages, model, api_key, max_tokens=max_tokens):
            yield chunk

    else:
        raise ValueError(f"Unsupported provider: {provider.value}")
