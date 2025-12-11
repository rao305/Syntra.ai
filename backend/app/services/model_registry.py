"""Model registry with valid models per provider and fallback logic."""
from __future__ import annotations

from typing import Dict, List, Optional

from app.models.provider_key import ProviderType


# Valid models per provider based on current API availability (2025)
# These should be updated periodically as APIs change
# Source: Official API documentation for each provider
MODEL_REGISTRY: Dict[ProviderType, List[str]] = {
    ProviderType.PERPLEXITY: [
        # Perplexity Sonar family (2025) - Official model names
        "sonar",                    # Default: Lightweight, fast answers with real-time citations
        "sonar-pro",                # Enhanced: More precise searches and richer context
        "sonar-reasoning",          # Chain-of-Thought for logical reasoning tasks
        "sonar-reasoning-pro",      # Advanced reasoning powered by DeepSeek-R1
    ],
    ProviderType.OPENAI: [
        # OpenAI models (2025) - Official API names
        "gpt-4o-mini",              # Cost-effective, fast (TTFT ~0.4s)
        "gpt-4o",                   # More capable (per DAC paper)
        "gpt-4-turbo",              # Alternative with vision
        "gpt-3.5-turbo",            # Fallback for simple queries
    ],
    ProviderType.GEMINI: [
        # Google Gemini models (2025) - Updated to available models
        "gemini-1.5-flash",         # STABLE: Most reliable, widely available
        "gemini-2.0-flash",         # Fast, production-ready alternative
        "gemini-2.5-flash",         # Fastest, newest flash model (may have availability issues)
        "gemini-2.5-pro",           # Most capable, larger context
        "gemini-2.0-flash-exp",     # Experimental, testing only
    ],
    ProviderType.OPENROUTER: [
        # OpenRouter models (2025) - format: provider/model-name
        # Free tier options (verified working)
        "google/gemini-flash-1.5-8b:free",      # Free Gemini Flash 8B
        "meta-llama/llama-3.2-3b-instruct:free",  # Free Llama 3.2 3B
        "microsoft/phi-3-mini-128k-instruct:free",  # Free Phi-3 Mini
        "qwen/qwen-2-7b-instruct:free",         # Free Qwen
        "mistralai/mistral-7b-instruct:free",   # Free Mistral
        # Paid tier for fallback
        "google/gemini-pro-1.5",                # Paid Gemini Pro
        "anthropic/claude-3-haiku",             # Paid Claude Haiku
        "openai/gpt-4o-mini",                   # Paid GPT-4o-mini via OpenRouter
    ],
    ProviderType.KIMI: [
        # Kimi (Moonshot AI) models (2025) - OpenAI-compatible API
        "kimi-k2-turbo-preview",                # Turbo model with long context (128k tokens)
        "moonshot-v1-8k",                       # 8k context window
        "moonshot-v1-32k",                      # 32k context window
        "moonshot-v1-128k",                     # 128k context window
    ],
}


def get_valid_models(provider: ProviderType) -> List[str]:
    """Get list of valid models for a provider."""
    return MODEL_REGISTRY.get(provider, [])


def get_default_model(provider: ProviderType) -> Optional[str]:
    """Get the default (first) model for a provider."""
    models = get_valid_models(provider)
    return models[0] if models else None


def get_fallback_model(provider: ProviderType, current_model: str) -> Optional[str]:
    """
    Get a fallback model if current model fails.
    
    Try the next model in the list, or return the default if current model not found.
    """
    models = get_valid_models(provider)
    if not models:
        return None
    
    try:
        current_index = models.index(current_model)
        # Try next model in list
        if current_index + 1 < len(models):
            return models[current_index + 1]
    except ValueError:
        # Current model not in list, return default
        pass
    
    # Return default if no fallback found
    return models[0] if models else None


def is_valid_model(provider: ProviderType, model: str) -> bool:
    """Check if a model is valid for a provider."""
    return model in get_valid_models(provider)


def validate_and_get_model(provider: ProviderType, requested_model: Optional[str] = None) -> str:
    """
    Validate and return a model for a provider.
    
    If requested_model is provided and valid, returns it.
    Otherwise, returns the default model for the provider.
    """
    if requested_model and is_valid_model(provider, requested_model):
        return requested_model
    
    default = get_default_model(provider)
    if default:
        return default
    
    raise ValueError(f"No valid models configured for provider: {provider.value}")

