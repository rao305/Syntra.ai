"""Model configuration with capabilities for dynamic routing."""
from dataclasses import dataclass
from typing import List, Literal, Optional
from app.models.provider_key import ProviderType


# Model capability tags
CapabilityTag = Literal[
    "web_search",
    "coding",
    "math",
    "reasoning",
    "creative_writing",
    "summarization",
    "multi_doc_rag",
    "chat",
]


@dataclass
class ModelConfig:
    """Configuration for a model with capabilities, cost, and latency."""

    id: str  # Model identifier (e.g., "gpt-4o-mini")
    provider: ProviderType
    display_name: str
    provider_model: str  # Actual model name for API calls (e.g., "gpt-4o")
    max_context: int  # Maximum context window in tokens
    avg_latency_ms: int  # Average latency in milliseconds
    cost_per_1k_tokens: float  # Cost per 1k tokens (input/output average)
    strengths: List[CapabilityTag]  # What this model is good at


# Model configurations based on current capabilities and pricing
MODELS: List[ModelConfig] = [
    ModelConfig(
        id="perplexity-sonar",
        provider=ProviderType.PERPLEXITY,
        display_name="Perplexity Sonar",
        provider_model="sonar",
        max_context=200_000,
        avg_latency_ms=3500,
        cost_per_1k_tokens=0.002,
        strengths=["web_search", "summarization", "multi_doc_rag"],
    ),
    ModelConfig(
        id="perplexity-sonar-pro",
        provider=ProviderType.PERPLEXITY,
        display_name="Perplexity Sonar Pro",
        provider_model="sonar-pro",
        max_context=200_000,
        avg_latency_ms=4000,
        cost_per_1k_tokens=0.003,
        strengths=["web_search", "summarization", "multi_doc_rag", "reasoning"],
    ),
    ModelConfig(
        id="gpt-4o-mini",
        provider=ProviderType.OPENAI,
        display_name="GPT-4o Mini",
        provider_model="gpt-4o-mini",
        max_context=128_000,
        avg_latency_ms=2500,
        cost_per_1k_tokens=0.003,
        strengths=["reasoning", "coding", "math", "creative_writing", "chat"],
    ),
    ModelConfig(
        id="gpt-4o",
        provider=ProviderType.OPENAI,
        display_name="GPT-4o",
        provider_model="gpt-4o",
        max_context=128_000,
        avg_latency_ms=3000,
        cost_per_1k_tokens=0.005,
        strengths=["reasoning", "coding", "math", "creative_writing", "chat"],
    ),
    ModelConfig(
        id="gemini-2.5-flash",
        provider=ProviderType.GEMINI,
        display_name="Gemini 2.5 Flash",
        provider_model="gemini-2.5-flash",
        max_context=100_000,
        avg_latency_ms=2200,
        cost_per_1k_tokens=0.0025,
        strengths=["reasoning", "summarization", "coding", "chat"],
    ),
    ModelConfig(
        id="gemini-2.5-pro",
        provider=ProviderType.GEMINI,
        display_name="Gemini 2.5 Pro",
        provider_model="gemini-2.5-pro",
        max_context=1_000_000,
        avg_latency_ms=3500,
        cost_per_1k_tokens=0.0035,
        strengths=["reasoning", "summarization", "multi_doc_rag", "coding"],
    ),
    ModelConfig(
        id="kimi-k2-turbo",
        provider=ProviderType.KIMI,
        display_name="Kimi K2 Turbo",
        provider_model="kimi-k2-turbo-preview",
        max_context=200_000,
        avg_latency_ms=3000,
        cost_per_1k_tokens=0.0015,
        strengths=["web_search", "summarization", "creative_writing"],
    ),
    ModelConfig(
        id="openrouter-default",
        provider=ProviderType.OPENROUTER,
        display_name="OpenRouter Mix",
        provider_model="google/gemini-flash-1.5-8b:free",
        max_context=32_000,
        avg_latency_ms=1800,
        cost_per_1k_tokens=0.001,
        strengths=["creative_writing", "chat"],
    ),
]


def get_model_by_id(model_id: str) -> Optional[ModelConfig]:
    """Get a model config by its ID."""
    for model in MODELS:
        if model.id == model_id:
            return model
    return None


def get_models_by_provider(provider: ProviderType) -> List[ModelConfig]:
    """Get all models for a provider."""
    return [m for m in MODELS if m.provider == provider]





