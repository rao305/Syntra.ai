"""
Base agent executor with provider abstraction.

Handles LLM calls to any supported provider (OpenAI, Perplexity, Gemini, Kimi).
"""

import asyncio
import logging
from typing import Dict, List, Optional
from app.models.provider_key import ProviderType
from app.services.provider_dispatch import call_provider_adapter
from app.services.council.config import (
    get_model_for_provider,
    TOKEN_LIMITS,
    AGENT_PROVIDER_MAPPING
)

logger = logging.getLogger(__name__)

# Timeout for individual provider calls (in seconds)
# Synthesizer and Judge need more time due to larger inputs
PROVIDER_CALL_TIMEOUT = 30
SYNTHESIZER_PROVIDER_TIMEOUT = 90  # 90 seconds for synthesizer
JUDGE_PROVIDER_TIMEOUT = 120  # 120 seconds for judge


async def run_agent(
    agent_name: str,
    system_prompt: str,
    user_message: str,
    api_keys: Dict[str, str],
    preferred_provider: Optional[ProviderType] = None,
    max_tokens: Optional[int] = None,
) -> tuple[str, ProviderType]:
    """
    Execute a single agent with the given prompt using specified provider.
    Automatically falls back to available providers if preferred provider fails.

    Args:
        agent_name: Name of the agent (architect, data_engineer, etc.)
        system_prompt: The agent's system instructions
        user_message: The user's query or combined input
        api_keys: Dict of API keys by provider ({"openai": "key", "gemini": "key", ...})
        preferred_provider: Preferred provider (defaults from AGENT_PROVIDER_MAPPING)
        max_tokens: Maximum tokens in response (defaults from TOKEN_LIMITS)

    Returns:
        Tuple of (response_text, provider_used)

    Raises:
        ValueError: If no API key available for any provider
        Exception: If all provider attempts fail
    """

    # Get available providers
    available_providers = get_available_providers(api_keys)
    if not available_providers:
        raise ValueError(
            f"No API keys available for any provider. "
            f"Required: at least one of {[p.value for p in ProviderType]}"
        )

    # Determine which provider to use (with fallback)
    if preferred_provider is None:
        preferred_provider = AGENT_PROVIDER_MAPPING.get(
            agent_name, ProviderType.OPENAI
        )

    # Build provider priority list: preferred first, then others
    provider_priority = [preferred_provider]
    for provider in available_providers:
        if provider not in provider_priority:
            provider_priority.append(provider)

    # Try each provider in priority order
    last_error = None
    providers_tried = []
    for provider in provider_priority:
        # Skip if no API key for this provider
        provider_key = provider.value
        api_key = api_keys.get(provider_key)
        if not api_key:
            logger.debug(f"Skipping {provider_key} for {agent_name} - no API key")
            continue
        
        providers_tried.append(provider_key)

        # Get model for this provider
        try:
            model = get_model_for_provider(provider)
        except ValueError:
            logger.warning(f"Unsupported provider {provider_key}, skipping")
            continue

        # Set token limits
        if max_tokens is None:
            max_tokens = TOKEN_LIMITS.get("specialist", 1500)
            if agent_name == "synthesizer":
                max_tokens = TOKEN_LIMITS["synthesizer"]
            elif agent_name == "judge":
                max_tokens = TOKEN_LIMITS["judge"]

        logger.info(
            f"Running {agent_name} agent via {provider_key}",
            extra={
                "agent": agent_name,
                "provider": provider_key,
                "model": model,
                "max_tokens": max_tokens,
                "is_fallback": provider != preferred_provider,
                "system_prompt_length": len(system_prompt),
                "user_message_length": len(user_message)
            }
        )

        try:
            # Call the provider adapter with timeout protection
            # Use longer timeouts for synthesizer and judge due to larger inputs
            timeout = PROVIDER_CALL_TIMEOUT
            if agent_name == "synthesizer":
                timeout = SYNTHESIZER_PROVIDER_TIMEOUT
            elif agent_name == "judge":
                timeout = JUDGE_PROVIDER_TIMEOUT

            logger.debug(f"Calling provider adapter for {agent_name} via {provider_key} (timeout: {timeout}s)...")
            try:
                response = await asyncio.wait_for(
                    call_provider_adapter(
                        provider=provider,
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message}
                        ],
                        api_key=api_key,
                        max_tokens=max_tokens
                    ),
                    timeout=timeout
                )
                logger.debug(f"Provider adapter returned response for {agent_name} via {provider_key}")
            except asyncio.TimeoutError:
                error_msg = f"Provider {provider_key} timed out after {timeout} seconds"
                logger.warning(
                    f"{error_msg} for {agent_name}",
                    extra={
                        "agent": agent_name,
                        "provider": provider_key,
                        "timeout_seconds": timeout
                    }
                )
                raise Exception(error_msg)

            # Extract text from response
            response_text = response.content

            # Log success (mention if fallback was used)
            if provider != preferred_provider:
                logger.info(
                    f"{agent_name} agent completed via fallback provider {provider_key} "
                    f"(preferred was {preferred_provider.value})",
                    extra={
                        "agent": agent_name,
                        "provider": provider_key,
                        "preferred_provider": preferred_provider.value,
                        "response_length": len(response_text)
                    }
                )
            else:
                logger.info(
                    f"{agent_name} agent completed",
                    extra={
                        "agent": agent_name,
                        "provider": provider_key,
                        "response_length": len(response_text)
                    }
                )

            return response_text, provider

        except Exception as e:
            # Log error but continue to next provider
            error_msg = str(e)
            logger.warning(
                f"Error calling {agent_name} agent via {provider_key}: {error_msg}",
                extra={
                    "agent": agent_name,
                    "provider": provider_key,
                    "error": error_msg
                }
            )
            last_error = e
            # Continue to next provider in priority list
            continue

    # If we get here, all providers failed
    raise Exception(
        f"All provider attempts failed for {agent_name}. "
        f"Last error: {str(last_error) if last_error else 'Unknown error'}. "
        f"Tried providers: {providers_tried}"
    )


def get_available_providers(api_keys: Dict[str, str]) -> List[ProviderType]:
    """Get list of available providers based on provided API keys."""
    available = []
    for key, value in api_keys.items():
        if value:  # If API key is provided
            try:
                provider = ProviderType(key.lower())
                available.append(provider)
            except ValueError:
                logger.warning(f"Unknown provider key: {key}")
    return available
