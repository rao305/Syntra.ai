"""
Extensible Model Registry and Router Configuration.
Add new models by simply adding entries to MODEL_REGISTRY.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from enum import Enum
import os


# =============================================================================
# ENUMS
# =============================================================================

class TaskType(Enum):
    """Types of tasks the router can classify."""
    SIMPLE_QA = "simple_qa"           # Basic questions
    CONVERSATION = "conversation"      # Casual chat
    CODING = "coding"                  # Code generation/debugging
    REASONING = "reasoning"            # Logic, analysis
    MATH = "math"                      # Mathematical problems
    CREATIVE = "creative"              # Writing, brainstorming
    RESEARCH = "research"              # Web search needed
    LONG_CONTEXT = "long_context"      # Large documents
    TRANSLATION = "translation"        # Language translation
    SUMMARIZATION = "summarization"    # Content condensation
    MULTIMODAL = "multimodal"          # Images/files involved


class CostTier(Enum):
    """Cost classification for models."""
    FREE = "free"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PREMIUM = "premium"


class LatencyTier(Enum):
    """Latency classification for models."""
    ULTRA_FAST = "ultra_fast"    # < 300ms
    FAST = "fast"                # 300-800ms
    NORMAL = "normal"            # 800-2000ms
    SLOW = "slow"                # > 2000ms


class UserPriority(Enum):
    """User preference for routing decisions."""
    SPEED = "speed"              # Fastest response
    COST = "cost"                # Cheapest option
    QUALITY = "quality"          # Best quality
    BALANCED = "balanced"        # Balance all factors


# =============================================================================
# MODEL CAPABILITIES DATACLASS
# =============================================================================

@dataclass
class ModelCapabilities:
    """
    Defines a model's capabilities, costs, and characteristics.
    Add new models by creating new instances of this class.
    """
    # Identification
    model_id: str                          # Internal ID (e.g., "gpt-4o")
    provider: str                          # Provider name (e.g., "openai")
    display_name: str                      # UI display name
    description: str                       # Brief description

    # Costs (per 1K tokens)
    cost_per_1k_input: float
    cost_per_1k_output:  float
    cost_tier: CostTier

    # Performance
    avg_latency_ms: int                    # Average response time
    latency_tier: LatencyTier
    max_context:  int                       # Max context window
    max_output:  int                        # Max output tokens

    # Capabilities
    strengths: List[str]                   # What it's good at
    weaknesses: List[str]                  # What it's not good at
    best_for: List[TaskType]               # Optimal task types

    # Features
    supports_streaming: bool = True
    supports_vision: bool = False
    supports_web_search: bool = False
    supports_file_upload: bool = False
    supports_function_calling: bool = False

    # Availability
    is_available: bool = True
    requires_api_key:  str = ""             # Env var name for API key

    # Metadata
    version: str = "latest"
    release_date: Optional[str] = None

    # Custom routing logic (optional)
    custom_router: Optional[Callable] = None

    def get_cost_score(self) -> float:
        """Returns normalized cost score (0-1, lower is cheaper)."""
        tier_scores = {
            CostTier.FREE: 0.0,
            CostTier.LOW: 0.25,
            CostTier.MEDIUM: 0.5,
            CostTier.HIGH:  0.75,
            CostTier.PREMIUM:  1.0
        }
        return tier_scores.get(self.cost_tier, 0.5)

    def get_latency_score(self) -> float:
        """Returns normalized latency score (0-1, lower is faster)."""
        tier_scores = {
            LatencyTier.ULTRA_FAST:  0.0,
            LatencyTier.FAST: 0.33,
            LatencyTier.NORMAL: 0.66,
            LatencyTier.SLOW: 1.0
        }
        return tier_scores.get(self.latency_tier, 0.5)

    def is_suitable_for(self, task_type: TaskType) -> bool:
        """Check if model is suitable for a task type."""
        return task_type in self.best_for

    def has_api_key(self) -> bool:
        """Check if required API key is configured."""
        if not self.requires_api_key:
            return True
        return bool(os.getenv(self.requires_api_key))


# =============================================================================
# MODEL REGISTRY — ADD NEW MODELS HERE
# =============================================================================

MODEL_REGISTRY:  Dict[str, ModelCapabilities] = {

    # =========================================================================
    # OPENAI MODELS
    # =========================================================================

    "gpt-4o-mini": ModelCapabilities(
        model_id="gpt-4o-mini",
        provider="openai",
        display_name="GPT-4o Mini",
        description="Fast, affordable model for simple tasks",
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.0006,
        cost_tier=CostTier.LOW,
        avg_latency_ms=400,
        latency_tier=LatencyTier.FAST,
        max_context=128000,
        max_output=16384,
        strengths=[
            "fast_response",
            "cost_effective",
            "good_general_knowledge",
            "simple_coding",
            "conversation"
        ],
        weaknesses=[
            "complex_reasoning",
            "advanced_math",
            "nuanced_analysis",
            "long_form_content"
        ],
        best_for=[
            TaskType.SIMPLE_QA,
            TaskType.CONVERSATION,
            TaskType.TRANSLATION,
        ],
        supports_vision=True,
        supports_function_calling=True,
        requires_api_key="OPENAI_API_KEY",
    ),

    "gpt-4o": ModelCapabilities(
        model_id="gpt-4o",
        provider="openai",
        display_name="GPT-4o",
        description="Most capable OpenAI model for complex tasks",
        cost_per_1k_input=0.005,
        cost_per_1k_output=0.015,
        cost_tier=CostTier.HIGH,
        avg_latency_ms=1200,
        latency_tier=LatencyTier.NORMAL,
        max_context=128000,
        max_output=16384,
        strengths=[
            "complex_reasoning",
            "advanced_coding",
            "math_proofs",
            "system_design",
            "analysis",
            "instruction_following"
        ],
        weaknesses=[
            "cost",
            "latency",
            "web_search"
        ],
        best_for=[
            TaskType.CODING,
            TaskType.REASONING,
            TaskType.MATH,
        ],
        supports_vision=True,
        supports_function_calling=True,
        requires_api_key="OPENAI_API_KEY",
    ),

    # =========================================================================
    # GOOGLE MODELS
    # =========================================================================

    "gemini-2.5-flash":  ModelCapabilities(
        model_id="gemini-2.5-flash",
        provider="google",
        display_name="Gemini 2.5 Flash",
        description="Ultra-fast with massive context window",
        cost_per_1k_input=0.0001,
        cost_per_1k_output=0.0004,
        cost_tier=CostTier.LOW,
        avg_latency_ms=350,
        latency_tier=LatencyTier.ULTRA_FAST,
        max_context=1000000,  # 1M tokens!
        max_output=8192,
        strengths=[
            "ultra_fast",
            "massive_context",
            "cost_effective",
            "document_analysis",
            "summarization",
            "bulk_processing"
        ],
        weaknesses=[
            "complex_reasoning",
            "creative_writing",
            "nuanced_responses"
        ],
        best_for=[
            TaskType.LONG_CONTEXT,
            TaskType.SUMMARIZATION,
            TaskType.SIMPLE_QA,
        ],
        supports_vision=True,
        supports_file_upload=True,
        requires_api_key="GEMINI_API_KEY",
    ),

    # =========================================================================
    # PERPLEXITY MODELS
    # =========================================================================

    "perplexity-sonar-pro": ModelCapabilities(
        model_id="sonar-pro",
        provider="perplexity",
        display_name="Perplexity Sonar Pro",
        description="Web-connected AI for research and current events",
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        cost_tier=CostTier.MEDIUM,
        avg_latency_ms=2000,
        latency_tier=LatencyTier.SLOW,
        max_context=127000,
        max_output=4096,
        strengths=[
            "web_search",
            "citations",
            "current_events",
            "fact_checking",
            "research",
            "real_time_info"
        ],
        weaknesses=[
            "creative_writing",
            "coding",
            "latency",
            "offline_tasks"
        ],
        best_for=[
            TaskType.RESEARCH,
        ],
        supports_web_search=True,
        requires_api_key="PERPLEXITY_API_KEY",
    ),

    # =========================================================================
    # KIMI/MOONSHOT MODELS
    # =========================================================================

    "kimi-k2": ModelCapabilities(
        model_id="kimi-k2",
        provider="moonshot",
        display_name="Kimi K2",
        description="Powerful model with strong reasoning and long context",
        cost_per_1k_input=0.002,
        cost_per_1k_output=0.008,
        cost_tier=CostTier.MEDIUM,
        avg_latency_ms=1000,
        latency_tier=LatencyTier.NORMAL,
        max_context=128000,
        max_output=8192,
        strengths=[
            "reasoning",
            "coding",
            "long_context",
            "chinese_language",
            "analysis",
            "math"
        ],
        weaknesses=[
            "web_search",
            "real_time_info"
        ],
        best_for=[
            TaskType.CODING,
            TaskType.REASONING,
            TaskType.LONG_CONTEXT,
            TaskType.MATH,
        ],
        supports_vision=False,
        supports_file_upload=True,
        requires_api_key="KIMI_API_KEY",
    ),

    # =========================================================================
    # TEMPLATE FOR ADDING NEW MODELS
    # =========================================================================

    # "new-model-id": ModelCapabilities(
    #     model_id="new-model-id",
    #     provider="provider_name",
    #     display_name="Display Name",
    #     description="Brief description",
    #     cost_per_1k_input=0.001,
    #     cost_per_1k_output=0.002,
    #     cost_tier=CostTier.MEDIUM,
    #     avg_latency_ms=1000,
    #     latency_tier=LatencyTier.NORMAL,
    #     max_context=100000,
    #     max_output=4096,
    #     strengths=["strength1", "strength2"],
    #     weaknesses=["weakness1", "weakness2"],
    #     best_for=[TaskType.CODING, TaskType.REASONING],
    #     requires_api_key="NEW_MODEL_API_KEY",
    # ),
}


# =============================================================================
# ROUTER CONFIGURATION
# =============================================================================

@dataclass
class RouterConfig:
    """Configuration for the intelligent router."""

    # Fine-tuned model settings
    router_model: str = "gpt-4o-mini"  # Base model for routing
    fine_tuned_model_id: Optional[str] = None  # Set after fine-tuning
    use_fine_tuned: bool = True

    # Fallback behavior
    fallback_model: str = "gpt-4o-mini"  # Default if routing fails
    confidence_threshold: float = 0.7   # Min confidence to trust routing

    # Cost/latency optimization
    max_routing_latency_ms: int = 500   # Max time for routing decision
    enable_cost_optimization:  bool = True
    enable_latency_optimization: bool = True

    # Caching
    enable_routing_cache: bool = True
    cache_ttl_seconds: int = 3600

    # Metrics
    enable_metrics: bool = True
    log_routing_decisions: bool = True


# Global config instance
ROUTER_CONFIG = RouterConfig()


# =============================================================================
# ROUTER SYSTEM PROMPT
# =============================================================================

def generate_router_system_prompt() -> str:
    """
    Dynamically generates the router system prompt based on registered models.
    This ensures the prompt stays in sync with MODEL_REGISTRY.
    """

    # Build model descriptions
    model_descriptions = []
    for model_id, caps in MODEL_REGISTRY.items():
        if caps.is_available and caps.has_api_key():
            desc = f"""
{len(model_descriptions) + 1}. {model_id} ({caps.display_name})
   - Provider: {caps. provider}
   - Cost:  {caps.cost_tier.value} (${caps.cost_per_1k_input:.4f}/1K input)
   - Speed: {caps.latency_tier.value} (~{caps.avg_latency_ms}ms)
   - Best for: {', '. join(t.value for t in caps.best_for)}
   - Strengths: {', '.join(caps.strengths[: 4])}
   - Web search:  {'Yes' if caps.supports_web_search else 'No'}
   - Vision: {'Yes' if caps.supports_vision else 'No'}"""
            model_descriptions.append(desc)

    models_section = "\n".join(model_descriptions)

    return f"""You are Syntra's intelligent query router.  Analyze user queries and decide which AI model should handle them for optimal results.

=== AVAILABLE MODELS ===
{models_section}

=== ROUTING PRINCIPLES ===
1. COST EFFICIENCY: Use the cheapest model that can handle the task well
2. TASK MATCHING: Route to models based on their strengths
3. WEB SEARCH: Only use Perplexity when current/real-time information is needed
4. COMPLEXITY:  Use more powerful models for complex reasoning/coding
5. SPEED: Consider latency requirements for time-sensitive queries

=== TASK CLASSIFICATION ===
- simple_qa: Basic factual questions, definitions
- conversation: Casual chat, greetings, small talk
- coding: Code generation, debugging, review
- reasoning: Logic problems, analysis, planning
- math: Mathematical computations, proofs
- creative: Writing, brainstorming, content creation
- research:  Requires web search, citations, current events
- long_context: Processing large documents (>50K tokens)
- summarization:  Condensing content
- translation: Language translation

=== OUTPUT FORMAT ===
Respond with ONLY valid JSON (no markdown, no explanation):
{{
  "model":  "model-id",
  "task_type": "task_type",
  "complexity": 1-5,
  "confidence": 0.0-1.0,
  "reasoning":  "one sentence explanation",
  "needs_web":  true/false,
  "estimated_tokens": number
}}

=== ROUTING RULES ===
1. Simple greetings/chat → gpt-4o-mini (cheapest, fastest)
2. Basic questions → gpt-4o-mini or gemini-2.5-flash
3. Complex coding/debugging → gpt-4o or kimi-k2
4. Math proofs/logic → gpt-4o or kimi-k2
5. Creative writing → gpt-4o (or claude when available)
6. Current events/research → perplexity-sonar-pro (ONLY model with web)
7. Long documents (>50K tokens) → gemini-2.5-flash (1M context)
8. Uncertain/vague queries → gpt-4o-mini (clarify with cheap model)

IMPORTANT:
- perplexity-sonar-pro is the ONLY model with web search
- gemini-2.5-flash is the ONLY model with 1M token context
- When in doubt, prefer cheaper/faster models"""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_available_models() -> List[str]:
    """Get list of available model IDs."""
    return [
        model_id for model_id, caps in MODEL_REGISTRY.items()
        if caps.is_available and caps.has_api_key()
    ]


def get_model(model_id: str) -> Optional[ModelCapabilities]:
    """Get model capabilities by ID."""
    return MODEL_REGISTRY.get(model_id)


def get_models_by_task(task_type: TaskType) -> List[str]:
    """Get models suitable for a specific task type."""
    return [
        model_id for model_id, caps in MODEL_REGISTRY.items()
        if caps.is_suitable_for(task_type) and caps.is_available
    ]


def get_cheapest_model() -> str:
    """Get the cheapest available model."""
    available = [
        (model_id, caps) for model_id, caps in MODEL_REGISTRY.items()
        if caps.is_available and caps.has_api_key()
    ]
    if not available:
        return "gpt-4o-mini"
    return min(available, key=lambda x: x[1].cost_per_1k_input)[0]


def get_fastest_model() -> str:
    """Get the fastest available model."""
    available = [
        (model_id, caps) for model_id, caps in MODEL_REGISTRY.items()
        if caps. is_available and caps.has_api_key()
    ]
    if not available:
        return "gemini-2.5-flash"
    return min(available, key=lambda x:  x[1].avg_latency_ms)[0]


def add_model(model_id: str, capabilities: ModelCapabilities) -> None:
    """Add a new model to the registry at runtime."""
    MODEL_REGISTRY[model_id] = capabilities


def remove_model(model_id: str) -> bool:
    """Remove a model from the registry."""
    if model_id in MODEL_REGISTRY:
        del MODEL_REGISTRY[model_id]
        return True
    return False
