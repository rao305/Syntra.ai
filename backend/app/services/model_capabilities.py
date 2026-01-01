"""
Model Capabilities Registry

Defines the capabilities and metadata for all available AI models,
enabling dynamic model selection based on task requirements.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from enum import Enum

from app.models.provider_key import ProviderType


class CostTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ModelStrengths:
    """Capability scores for a model (0.0 to 1.0)"""
    reasoning: float  # Logical reasoning, analysis, problem decomposition
    creativity: float  # Creative writing, ideation, novel solutions
    factuality: float  # Factual accuracy, up-to-date information
    code: float  # Code generation, debugging, technical tasks
    long_context: float  # Handling long inputs/outputs effectively
    
    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class ModelCapability:
    """Complete capability profile for a model"""
    id: str  # Format: "provider:model-name"
    display_name: str
    provider: ProviderType
    model_name: str  # Actual model name for API calls
    strengths: ModelStrengths
    cost_tier: CostTier
    has_browse: bool  # Can access real-time web information
    has_vision: bool  # Can process images
    relative_latency: float  # 0.0 (fastest) to 1.0 (slowest)
    max_context_tokens: int  # Maximum context window
    description: str
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "provider": self.provider.value,
            "model_name": self.model_name,
            "strengths": self.strengths.to_dict(),
            "cost_tier": self.cost_tier.value,
            "has_browse": self.has_browse,
            "has_vision": self.has_vision,
            "relative_latency": self.relative_latency,
            "max_context_tokens": self.max_context_tokens,
            "description": self.description
        }


# Complete Model Registry with Capabilities
MODEL_CAPABILITIES: Dict[str, ModelCapability] = {
    # OpenAI Models
    "openai:gpt-4o": ModelCapability(
        id="openai:gpt-4o",
        display_name="GPT-4o",
        provider=ProviderType.OPENAI,
        model_name="gpt-4o",
        strengths=ModelStrengths(
            reasoning=0.95,
            creativity=0.85,
            factuality=0.85,
            code=0.92,
            long_context=0.75
        ),
        cost_tier=CostTier.HIGH,
        has_browse=False,
        has_vision=True,  # GPT-4o supports vision
        relative_latency=0.6,
        max_context_tokens=128000,
        description="OpenAI's most capable model with vision, excellent for complex reasoning and image analysis"
    ),
    "openai:gpt-4o-mini": ModelCapability(
        id="openai:gpt-4o-mini",
        display_name="GPT-4o Mini",
        provider=ProviderType.OPENAI,
        model_name="gpt-4o-mini",
        strengths=ModelStrengths(
            reasoning=0.80,
            creativity=0.75,
            factuality=0.75,
            code=0.80,
            long_context=0.70
        ),
        cost_tier=CostTier.LOW,
        has_browse=False,
        has_vision=True,  # GPT-4o mini supports vision
        relative_latency=0.3,
        max_context_tokens=128000,
        description="Fast, cost-effective OpenAI model for most tasks"
    ),
    "openai:gpt-4-turbo": ModelCapability(
        id="openai:gpt-4-turbo",
        display_name="GPT-4 Turbo",
        provider=ProviderType.OPENAI,
        model_name="gpt-4-turbo",
        strengths=ModelStrengths(
            reasoning=0.92,
            creativity=0.85,
            factuality=0.85,
            code=0.90,
            long_context=0.85
        ),
        cost_tier=CostTier.HIGH,
        has_browse=False,
        has_vision=True,  # GPT-4 Turbo supports vision
        relative_latency=0.5,
        max_context_tokens=128000,
        description="GPT-4 with improved speed and vision capabilities"
    ),
    
    # Gemini Models
    "gemini:gemini-2.5-flash": ModelCapability(
        id="gemini:gemini-2.5-flash",
        display_name="Gemini 2.5 Flash",
        provider=ProviderType.GEMINI,
        model_name="gemini-2.5-flash",
        strengths=ModelStrengths(
            reasoning=0.85,
            creativity=0.80,
            factuality=0.80,
            code=0.82,
            long_context=0.90
        ),
        cost_tier=CostTier.LOW,
        has_browse=False,
        has_vision=True,  # Gemini 2.5 Flash supports vision
        relative_latency=0.25,
        max_context_tokens=1000000,
        description="Google's fastest Gemini model with massive context"
    ),
    "gemini:gemini-2.5-pro": ModelCapability(
        id="gemini:gemini-2.5-pro",
        display_name="Gemini 2.5 Pro",
        provider=ProviderType.GEMINI,
        model_name="gemini-2.5-pro",
        strengths=ModelStrengths(
            reasoning=0.92,
            creativity=0.85,
            factuality=0.85,
            code=0.88,
            long_context=0.95
        ),
        cost_tier=CostTier.HIGH,
        has_browse=False,
        has_vision=True,  # Gemini 2.5 Pro supports vision
        relative_latency=0.6,
        max_context_tokens=2000000,
        description="Google's most capable model with 2M token context"
    ),
    "gemini:gemini-2.0-flash": ModelCapability(
        id="gemini:gemini-2.0-flash",
        display_name="Gemini 2.0 Flash",
        provider=ProviderType.GEMINI,
        model_name="gemini-2.0-flash",
        strengths=ModelStrengths(
            reasoning=0.82,
            creativity=0.78,
            factuality=0.78,
            code=0.80,
            long_context=0.85
        ),
        cost_tier=CostTier.LOW,
        has_browse=False,
        has_vision=True,  # Gemini 2.0 Flash supports vision
        relative_latency=0.3,
        max_context_tokens=1000000,
        description="Fast and reliable Gemini model"
    ),
    
    # Perplexity Models
    "perplexity:sonar-pro": ModelCapability(
        id="perplexity:sonar-pro",
        display_name="Perplexity Sonar Pro",
        provider=ProviderType.PERPLEXITY,
        model_name="sonar-pro",
        strengths=ModelStrengths(
            reasoning=0.78,
            creativity=0.65,
            factuality=0.95,  # Highest factuality due to web search
            code=0.65,
            long_context=0.80
        ),
        cost_tier=CostTier.MEDIUM,
        has_browse=True,  # Real-time web search
        has_vision=False,  # Perplexity Sonar Pro does not support vision
        relative_latency=0.5,
        max_context_tokens=127000,
        description="Best for research with real-time web access and citations"
    ),
    "perplexity:sonar": ModelCapability(
        id="perplexity:sonar",
        display_name="Perplexity Sonar",
        provider=ProviderType.PERPLEXITY,
        model_name="sonar",
        strengths=ModelStrengths(
            reasoning=0.70,
            creativity=0.60,
            factuality=0.90,
            code=0.55,
            long_context=0.75
        ),
        cost_tier=CostTier.LOW,
        has_browse=True,
        has_vision=False,  # Perplexity Sonar does not support vision
        relative_latency=0.4,
        max_context_tokens=127000,
        description="Fast web search with good factuality"
    ),
    "perplexity:sonar-reasoning": ModelCapability(
        id="perplexity:sonar-reasoning",
        display_name="Perplexity Sonar Reasoning",
        provider=ProviderType.PERPLEXITY,
        model_name="sonar-reasoning",
        strengths=ModelStrengths(
            reasoning=0.88,
            creativity=0.65,
            factuality=0.92,
            code=0.70,
            long_context=0.80
        ),
        cost_tier=CostTier.MEDIUM,
        has_browse=True,
        has_vision=False,  # Perplexity Sonar Reasoning does not support vision
        relative_latency=0.6,
        max_context_tokens=127000,
        description="Chain-of-thought reasoning with web access"
    ),
    
    # Kimi (Moonshot) Models
    "kimi:moonshot-v1-32k": ModelCapability(
        id="kimi:moonshot-v1-32k",
        display_name="Kimi Moonshot 32K",
        provider=ProviderType.KIMI,
        model_name="moonshot-v1-32k",
        strengths=ModelStrengths(
            reasoning=0.78,
            creativity=0.80,
            factuality=0.75,
            code=0.75,
            long_context=0.80
        ),
        cost_tier=CostTier.LOW,
        has_browse=False,
        has_vision=False,  # Kimi models do not support vision currently
        relative_latency=0.4,
        max_context_tokens=32000,
        description="Kimi's balanced model with 32K context"
    ),
    "kimi:moonshot-v1-128k": ModelCapability(
        id="kimi:moonshot-v1-128k",
        display_name="Kimi Moonshot 128K",
        provider=ProviderType.KIMI,
        model_name="moonshot-v1-128k",
        strengths=ModelStrengths(
            reasoning=0.80,
            creativity=0.82,
            factuality=0.75,
            code=0.75,
            long_context=0.92
        ),
        cost_tier=CostTier.MEDIUM,
        has_browse=False,
        has_vision=False,  # Kimi models do not support vision currently
        relative_latency=0.5,
        max_context_tokens=128000,
        description="Kimi's long-context model for extensive documents"
    ),
    "kimi:kimi-k2-turbo-preview": ModelCapability(
        id="kimi:kimi-k2-turbo-preview",
        display_name="Kimi K2 Turbo",
        provider=ProviderType.KIMI,
        model_name="kimi-k2-turbo-preview",
        strengths=ModelStrengths(
            reasoning=0.82,
            creativity=0.85,
            factuality=0.78,
            code=0.78,
            long_context=0.90
        ),
        cost_tier=CostTier.MEDIUM,
        has_browse=False,
        has_vision=False,  # Kimi models do not support vision currently
        relative_latency=0.45,
        max_context_tokens=128000,
        description="Kimi's latest turbo model with improved capabilities"
    ),
}


def get_available_models(api_keys: Dict[str, str]) -> List[ModelCapability]:
    """
    Get list of available models based on configured API keys.
    
    Args:
        api_keys: Dict mapping provider name to API key
        
    Returns:
        List of ModelCapability objects for available models
    """
    available = []
    
    for model_id, capability in MODEL_CAPABILITIES.items():
        provider_key = capability.provider.value
        if provider_key in api_keys and api_keys[provider_key]:
            available.append(capability)
    
    return available


def get_model_by_id(model_id: str) -> Optional[ModelCapability]:
    """Get model capability by ID"""
    return MODEL_CAPABILITIES.get(model_id)


def get_models_by_provider(provider: ProviderType) -> List[ModelCapability]:
    """Get all models for a specific provider"""
    return [
        cap for cap in MODEL_CAPABILITIES.values() 
        if cap.provider == provider
    ]


def get_best_model_for_role(
    role: str, 
    available_models: List[ModelCapability],
    priority: str = "balanced"
) -> Optional[ModelCapability]:
    """
    Get the best model for a specific role based on capabilities.
    
    Args:
        role: One of 'analyst', 'researcher', 'creator', 'critic', 'synthesizer'
        available_models: List of available model capabilities
        priority: One of 'quality', 'balanced', 'speed', 'cost'
        
    Returns:
        Best ModelCapability for the role, or None if no models available
    """
    if not available_models:
        return None
    
    # Define role requirements (importance weights for each strength)
    role_requirements = {
        "analyst": {
            "reasoning": 1.0,
            "creativity": 0.3,
            "factuality": 0.6,
            "code": 0.4,
            "long_context": 0.5,
            "needs_browse": False
        },
        "researcher": {
            "reasoning": 0.5,
            "creativity": 0.2,
            "factuality": 1.0,
            "code": 0.2,
            "long_context": 0.6,
            "needs_browse": True
        },
        "creator": {
            "reasoning": 0.6,
            "creativity": 1.0,
            "factuality": 0.5,
            "code": 0.8,
            "long_context": 0.7,
            "needs_browse": False
        },
        "critic": {
            "reasoning": 1.0,
            "creativity": 0.2,
            "factuality": 0.8,
            "code": 0.6,
            "long_context": 0.5,
            "needs_browse": False
        },
        "synthesizer": {
            "reasoning": 0.8,
            "creativity": 0.7,
            "factuality": 0.6,
            "code": 0.4,
            "long_context": 0.8,
            "needs_browse": False
        }
    }
    
    requirements = role_requirements.get(role, role_requirements["creator"])
    
    def score_model(model: ModelCapability) -> float:
        """Calculate a score for how well a model fits the role"""
        strengths = model.strengths
        
        # Base capability score
        capability_score = (
            strengths.reasoning * requirements["reasoning"] +
            strengths.creativity * requirements["creativity"] +
            strengths.factuality * requirements["factuality"] +
            strengths.code * requirements["code"] +
            strengths.long_context * requirements["long_context"]
        ) / sum(requirements[k] for k in ["reasoning", "creativity", "factuality", "code", "long_context"])
        
        # Bonus for browse capability if needed
        if requirements.get("needs_browse") and model.has_browse:
            capability_score += 0.2
        
        # Adjust based on priority
        if priority == "quality":
            # Prioritize capability, ignore cost/speed
            return capability_score
        elif priority == "speed":
            # Prioritize low latency
            return capability_score * 0.6 + (1 - model.relative_latency) * 0.4
        elif priority == "cost":
            # Prioritize low cost
            cost_score = {"low": 1.0, "medium": 0.6, "high": 0.3}[model.cost_tier.value]
            return capability_score * 0.5 + cost_score * 0.5
        else:  # balanced
            cost_score = {"low": 1.0, "medium": 0.7, "high": 0.4}[model.cost_tier.value]
            speed_score = 1 - model.relative_latency
            return capability_score * 0.5 + cost_score * 0.25 + speed_score * 0.25
    
    # Score all available models and return the best
    scored_models = [(model, score_model(model)) for model in available_models]
    scored_models.sort(key=lambda x: x[1], reverse=True)
    
    return scored_models[0][0] if scored_models else None


def format_models_for_orchestrator(available_models: List[ModelCapability]) -> List[Dict]:
    """Format model capabilities for the orchestrator LLM input"""
    return [model.to_dict() for model in available_models]












