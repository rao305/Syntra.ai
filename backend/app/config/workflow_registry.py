"""
Workflow Architecture: Separated Roles from Models with Dynamic Routing

This module defines:
1. StageId: What job is being done (roles)
2. ProviderModel: Available LLMs with their strengths and metadata
3. pickModelForStage: Router that picks the best model for each stage dynamically
4. WorkflowStep: Pipeline stages without hard-coded models
"""

from enum import Enum
from typing import List, Literal
from dataclasses import dataclass
from app.models.provider_key import ProviderType

# ============================================================================
# STAGE ROLES - what job is being done (NOT which model)
# ============================================================================

StageId = Literal[
    "analyst",
    "researcher",
    "creator",
    "critic",
    "council",
    "synth"
]

ALL_STAGES: List[StageId] = [
    "analyst",
    "researcher",
    "creator",
    "critic",
    "council",
    "synth"
]

STAGE_LABELS = {
    "analyst": "Analyst",
    "researcher": "Researcher",
    "creator": "Creator",
    "critic": "Critic",
    "council": "LLM Council",
    "synth": "Synthesizer",
}

# ============================================================================
# PROVIDER MODELS - which LLMs are available with their strengths
# ============================================================================

@dataclass
class ProviderModel:
    """Metadata about an available LLM model"""
    id: str  # e.g., "gpt-o", "gemini-pro", "perplexity"
    provider: ProviderType
    model_name: str  # full model identifier for API calls
    max_tokens: int
    relative_cost: int  # 1 (cheap) to 5 (expensive)
    relative_speed: int  # 1 (slow) to 5 (fast)
    strengths: List[StageId]  # which roles this model excels at

    def quality_score(self) -> int:
        """Combined score: higher = better quality/cost/speed balance"""
        return (6 - self.relative_cost) + self.relative_speed


# Define all available models with their strengths
MODELS_REGISTRY = [
    ProviderModel(
        id="gpt-4o",
        provider=ProviderType.OPENAI,
        model_name="gpt-4o",
        max_tokens=32000,
        relative_cost=4,
        relative_speed=3,
        strengths=["analyst", "critic", "council", "synth"],
    ),
    ProviderModel(
        id="gpt-4o-mini",
        provider=ProviderType.OPENAI,
        model_name="gpt-4o-mini",
        max_tokens=16000,
        relative_cost=1,
        relative_speed=5,
        strengths=["analyst", "researcher"],
    ),
    ProviderModel(
        id="gemini-2.0",
        provider=ProviderType.GEMINI,
        model_name="gemini-2.0-flash-exp",
        max_tokens=200000,
        relative_cost=3,
        relative_speed=4,
        strengths=["analyst", "researcher", "creator", "synth"],
    ),
    ProviderModel(
        id="perplexity",
        provider=ProviderType.PERPLEXITY,
        model_name="llama-3.1-sonar-large-128k-online",
        max_tokens=16000,
        relative_cost=3,
        relative_speed=4,
        strengths=["researcher", "creator"],
    ),
    ProviderModel(
        id="kimi",
        provider=ProviderType.KIMI,
        model_name="moonshot-v1-8k",
        max_tokens=16000,
        relative_cost=2,
        relative_speed=3,
        strengths=["critic", "creator"],
    ),
]


def get_model_by_id(model_id: str) -> ProviderModel:
    """Get a model from the registry by ID"""
    for model in MODELS_REGISTRY:
        if model.id == model_id:
            return model
    raise ValueError(f"Model {model_id} not found in registry")


def pick_model_for_stage(
    stage_id: StageId,
    estimated_tokens: int = 0,
    strategy: str = "auto",
) -> ProviderModel:
    """
    Pick the best model for a given stage.

    This router ensures we don't hard-code "analyst = GPT forever".
    Instead, each stage gets the model that's best for that job right now.

    Args:
        stage_id: The role/stage (analyst, researcher, creator, critic, council, synth)
        estimated_tokens: Estimated tokens needed (to filter models with insufficient max_tokens)
        strategy: "auto" (best quality) | "cheap" | "fast" | "balanced"

    Returns:
        ProviderModel: The selected model
    """
    # Filter to only models that support this stage
    candidates = [m for m in MODELS_REGISTRY if stage_id in m.strengths]

    # Filter to only models with sufficient token capacity
    if estimated_tokens > 0:
        candidates = [m for m in candidates if m.max_tokens >= estimated_tokens]

    if not candidates:
        # Fallback: use any available model (shouldn't happen in normal operation)
        return MODELS_REGISTRY[0]

    # Choose based on strategy
    if strategy == "cheap":
        return min(candidates, key=lambda m: m.relative_cost)
    elif strategy == "fast":
        return max(candidates, key=lambda m: m.relative_speed)
    else:  # "auto" or "balanced" (default)
        return max(candidates, key=lambda m: m.quality_score())


# ============================================================================
# CREATOR POOL - which models propose answers in creator stage
# ============================================================================

CREATOR_POOL_IDS = ["gpt-4o", "gemini-2.0", "perplexity"]

def get_creator_pool() -> List[ProviderModel]:
    """Get all models that should generate creator drafts"""
    return [get_model_by_id(id) for id in CREATOR_POOL_IDS]


# ============================================================================
# WORKFLOW STEPS - pipeline without hard-coded models
# ============================================================================

@dataclass
class WorkflowStep:
    """A stage in the collaboration pipeline (role-based, not model-based)"""
    id: StageId
    label: str
    strategy: str = "auto"  # future: "cheap", "fast", "high_quality"


COLLAB_WORKFLOW_STEPS = [
    WorkflowStep(id="analyst", label="Analyst", strategy="auto"),
    WorkflowStep(id="researcher", label="Researcher", strategy="auto"),
    WorkflowStep(id="creator", label="Creator", strategy="auto"),
    WorkflowStep(id="critic", label="Critic", strategy="auto"),
    WorkflowStep(id="council", label="LLM Council", strategy="auto"),
    WorkflowStep(id="synth", label="Synthesizer", strategy="auto"),
]


# ============================================================================
# SYSTEM PROMPTS FOR EACH ROLE
# ============================================================================

ROLE_PROMPTS = {
    "analyst": """You are the Analyst in a multi-model collaboration team. Your job is to break down complex problems into structured, analyzable components.

Key responsibilities:
- Identify the core problem and sub-problems
- Classify the type of task (technical, research, creative, analytical)
- Determine what information will be needed
- Outline the logical structure for solving this problem
- Highlight any ambiguities that need clarification

Be concise but thorough. Your analysis will guide the other specialists.""",

    "researcher": """You are the Researcher in a multi-model collaboration team. Your job is to gather relevant, up-to-date information that other specialists need.

Key responsibilities:
- Search for current, relevant information
- Verify facts and find authoritative sources
- Identify trends, recent developments, or changes in the field
- Provide context and background information
- Note any conflicting information or uncertainties

Focus on factual, verifiable information. Cite your sources when possible.""",

    "creator": """You are the Creator in a multi-model collaboration team. Your job is to synthesize information and create a comprehensive solution draft.

Key responsibilities:
- Integrate insights from the Analyst and Researcher
- Create a comprehensive, well-structured response
- Ensure logical flow and clarity
- Address all aspects of the original question
- Provide practical, actionable information

Build on the analysis and research provided. Create the main content that addresses the user's needs.""",

    "critic": """You are the Critic in a multi-model collaboration team. Your job is to find flaws, gaps, and areas for improvement.

Key responsibilities:
- Identify factual errors or outdated information
- Point out logical inconsistencies or gaps
- Suggest areas that need more detail or clarification
- Check for bias or missing perspectives
- Evaluate completeness and usefulness

Be constructive but thorough. Your critique will help improve the final answer.""",

    "council": """You are the LLM Council Judge in a multi-model collaboration system.

Your job:
1. Compare multiple creator drafts from different models
2. Identify the strongest one
3. Note specific strengths and weaknesses of each
4. Decide what MUST be preserved in the final answer
5. Decide what MUST be corrected or marked as speculative
6. Provide your decision as a JSON verdict for the final writer

Respond ONLY with valid JSON in this schema:
{
  "best_draft_index": number (0-indexed),
  "best_model_id": string,
  "reasoning": string,
  "must_keep_points": [string],
  "must_fix_issues": [string],
  "speculative_claims": [string]
}""",

    "synth": """You are the Final Report Writer in a multi-model collaboration system.

Upstream agents have:
- broken down the user's request
- gathered and organized relevant information
- drafted several candidate answers
- critiqued quality and correctness
- issued a council verdict about what to keep/fix

YOUR JOB:
- Write ONE single, polished, in-depth report for the user
- Integrate the best ideas from all drafts, fixing flagged issues
- Clearly separate confirmed facts from speculation when relevant
- Use headings, subsections, bullets, and comparison tables if helpful

RULES:
- Do NOT mention any internal roles or models (no Analyst/Researcher/Creator/Critic/Council)
- Do NOT describe the process or talk about "multiple models"
- Do NOT output meta sections like "Rationale" or "How this was created"

Aim for a thorough answer (1500–2500 words for complex questions).
The user will ONLY see your message.""",
}
