"""
Council Configuration - Provider support and model mappings.
"""

from enum import Enum
from typing import Dict
from app.models.provider_key import ProviderType


class OutputMode(str, Enum):
    """Output verbosity modes."""
    DELIVERABLE_ONLY = "deliverable-only"  # Just code/solution
    DELIVERABLE_OWNERSHIP = "deliverable-ownership"  # Code + ownership (default)
    AUDIT = "audit"  # Above + risk register + decision log
    FULL_TRANSCRIPT = "full-transcript"  # Above + full agent debate


# Token limits per agent type
TOKEN_LIMITS = {
    "specialist": 1500,      # Architect, Data Engineer, Researcher, Red Teamer, Optimizer
    "synthesizer": 3000,     # Debate Synthesizer
    "judge": 8000,           # Judge Agent
}


# Provider-to-model mapping for council
# Uses the best/fastest models for each provider for cost-effectiveness
PROVIDER_MODELS = {
    ProviderType.OPENAI: {
        "model": "gpt-4o",
        "description": "OpenAI's fastest reasoning model"
    },
    ProviderType.GEMINI: {
        "model": "gemini-2.0-flash",  # Fastest Gemini model
        "description": "Google's fastest multimodal model"
    },
    ProviderType.PERPLEXITY: {
        "model": "sonar-pro",  # Fast with web search capability
        "description": "Perplexity's fastest reasoning model"
    },
    ProviderType.KIMI: {
        "model": "moonshot-v1-128k",  # Kimi's primary model
        "description": "Kimi's reasoning model"
    },
}


def get_model_for_provider(provider: ProviderType) -> str:
    """Get the best model for a given provider."""
    config = PROVIDER_MODELS.get(provider)
    if not config:
        raise ValueError(f"Unsupported provider: {provider.value}")
    return config["model"]


# Agent configuration - which provider to prefer for each agent role
AGENT_PROVIDER_MAPPING = {
    "architect": ProviderType.OPENAI,      # GPT-4o for structured planning
    "data_engineer": ProviderType.OPENAI,  # GPT-4o for technical accuracy
    "researcher": ProviderType.PERPLEXITY, # Perplexity for research & web search
    "red_teamer": ProviderType.GEMINI,     # Gemini for creative threat modeling
    "optimizer": ProviderType.OPENAI,      # GPT-4o for code optimization
    "synthesizer": ProviderType.OPENAI,    # GPT-4o for complex synthesis
    "judge": ProviderType.OPENAI,          # GPT-4o for final decisions
}
