"""
Collaboration Orchestrator V2: Dynamic Model Selection + LLM Council

This module orchestrates the 6-stage collaboration pipeline:
1. Analyst - break down the problem
2. Researcher - gather information
3. Creator - multiple models generate drafts (multi-model stage!)
4. Critic - critique the drafts
5. Council - judge between drafts, issue verdict
6. Synthesizer - write final unified answer

Key differences from V1:
- Models are chosen dynamically using pick_model_for_stage() from workflow_registry
- Creator stage runs multiple models in parallel
- Council stage actually compares creator drafts and issues a JSON verdict
- Synthesizer uses the council verdict to write a single polished answer
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import logging

from app.config.workflow_registry import (
    pick_model_for_stage,
    get_creator_pool,
    StageId,
)
from app.config.collab_prompts import (
    GLOBAL_COLLAB_PROMPT,
    STAGE_SYSTEM_PROMPTS,
    build_messages_for_stage,
)
from app.models.provider_key import ProviderType

logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class StageContext:
    """Accumulated context flowing through the pipeline"""
    user_question: str
    analyst_output: Optional[str] = None
    researcher_output: Optional[str] = None
    creator_drafts: List[Dict[str, str]] = None  # List of {modelId, content}
    critic_output: Optional[str] = None
    council_verdict: Optional[Dict[str, Any]] = None
    synth_output: Optional[str] = None

    def __post_init__(self):
        if self.creator_drafts is None:
            self.creator_drafts = []


@dataclass
class StageResult:
    """Result from executing a stage"""
    stage_id: StageId
    status: str  # "success" or "error"
    model_id: str
    output: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class CouncilVerdict:
    """Council's judgment on creator drafts"""
    best_draft_index: int
    best_model_id: str
    reasoning: str
    must_keep_points: List[str]
    must_fix_issues: List[str]
    speculative_claims: List[str]
    # Quality metrics
    substance_score: float = 0.0
    completeness_score: float = 0.0
    depth_score: float = 0.0
    accuracy_score: float = 0.0
    overall_quality_score: float = 0.0
    quality_gate_passed: bool = False
    depth_appropriate: bool = True

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "CouncilVerdict":
        """Parse council response JSON into verdict"""
        return cls(
            best_draft_index=data.get("best_draft_index", 0),
            best_model_id=data.get("best_model_id", ""),
            reasoning=data.get("reasoning", ""),
            must_keep_points=data.get("must_keep_points", []),
            must_fix_issues=data.get("must_fix_issues", []),
            speculative_claims=data.get("speculative_claims", []),
            substance_score=data.get("substance_score", 0.0),
            completeness_score=data.get("completeness_score", 0.0),
            depth_score=data.get("depth_score", 0.0),
            accuracy_score=data.get("accuracy_score", 0.0),
            overall_quality_score=data.get("overall_quality_score", 0.0),
            quality_gate_passed=data.get("quality_gate_passed", False),
            depth_appropriate=data.get("depth_appropriate", True),
        )


# ============================================================================
# STAGE IMPLEMENTATIONS
# ============================================================================

async def call_model(
    provider: ProviderType,
    model_name: str,
    system_prompt: str,
    user_message: str,
    api_keys: Dict[str, str],
    max_tokens: int = 2000,
    temperature: float = 0.7,
    json_mode: bool = False,
) -> str:
    """
    Call an LLM model via the appropriate provider.

    This is a placeholder that would call the actual provider APIs.
    You'd use your existing LLM calling infrastructure here.
    """
    # TODO: Implement actual calls to OpenAI, Google, Perplexity, Kimi
    # For now, return a mock response
    logger.info(f"Calling {provider.value} with model {model_name}")
    return f"[Mock response from {model_name}]"


async def run_analyst(ctx: StageContext, api_keys: Dict[str, str]) -> StageResult:
    """Analyst stage: break down the problem"""
    model = pick_model_for_stage("analyst", 0, "auto")
    logger.info(f"🔮 Router selected {model.id} for analyst stage")

    # Build messages using production prompts
    messages = build_messages_for_stage("analyst", ctx.user_question, {})

    # Format messages for call_model (expects system_prompt + user_message)
    system_prompts = [m["content"] for m in messages if m["role"] == "system"]
    user_messages = [m["content"] for m in messages if m["role"] == "user"]

    combined_system = "\n\n".join(system_prompts)
    user_message = user_messages[0] if user_messages else ctx.user_question

    output = await call_model(
        provider=model.provider,
        model_name=model.model_name,
        system_prompt=combined_system,
        user_message=user_message,
        api_keys=api_keys,
        max_tokens=1500,
    )

    return StageResult(
        stage_id="analyst",
        status="success",
        model_id=model.id,
        output=output,
    )


async def run_researcher(ctx: StageContext, api_keys: Dict[str, str]) -> StageResult:
    """Researcher stage: gather information"""
    model = pick_model_for_stage("researcher", 0, "auto")
    logger.info(f"🔮 Router selected {model.id} for researcher stage")

    # Build messages using production prompts
    messages = build_messages_for_stage("researcher", ctx.user_question, {
        "analyst_output": ctx.analyst_output,
    })

    system_prompts = [m["content"] for m in messages if m["role"] == "system"]
    user_messages = [m["content"] for m in messages if m["role"] == "user"]

    combined_system = "\n\n".join(system_prompts)
    user_message = user_messages[0] if user_messages else ctx.user_question

    output = await call_model(
        provider=model.provider,
        model_name=model.model_name,
        system_prompt=combined_system,
        user_message=user_message,
        api_keys=api_keys,
        max_tokens=2000,
    )

    return StageResult(
        stage_id="researcher",
        status="success",
        model_id=model.id,
        output=output,
    )


async def run_creator_multi(ctx: StageContext, api_keys: Dict[str, str]) -> StageResult:
    """
    Creator stage: run multiple models in PARALLEL to generate competing drafts.

    This is the key difference - instead of 1 creator, we get drafts from 3+ models
    so the council can compare and choose the best one.
    """
    creator_models = get_creator_pool()
    logger.info(f"📝 Creator stage: running {len(creator_models)} models in parallel")

    # Build messages using production prompts
    builder_messages = build_messages_for_stage("creator", ctx.user_question, {
        "analyst_output": ctx.analyst_output,
        "researcher_output": ctx.researcher_output,
    })

    system_prompts = [m["content"] for m in builder_messages if m["role"] == "system"]
    user_messages = [m["content"] for m in builder_messages if m["role"] == "user"]

    combined_system = "\n\n".join(system_prompts)
    user_message = user_messages[0] if user_messages else ctx.user_question

    # Run all creator models in parallel
    tasks = [
        call_model(
            provider=model.provider,
            model_name=model.model_name,
            system_prompt=combined_system,
            user_message=user_message,
            api_keys=api_keys,
            max_tokens=2000,
            temperature=0.7,
        )
        for model in creator_models
    ]

    outputs = await asyncio.gather(*tasks, return_exceptions=True)

    # Combine drafts
    drafts = []
    for model, output in zip(creator_models, outputs):
        if isinstance(output, Exception):
            logger.error(f"Creator {model.id} failed: {output}")
            continue
        drafts.append({"model_id": model.id, "content": output})

    # Create combined output for logging/storage
    combined = "\n\n".join(
        [f"Draft from {d['model_id']}:\n{d['content'][:500]}..." for d in drafts]
    )

    # Store in context for council
    ctx.creator_drafts = drafts

    return StageResult(
        stage_id="creator",
        status="success",
        model_id="multi-creator",
        output=combined,
        metadata={"draft_count": len(drafts)},
    )


async def run_critic(ctx: StageContext, api_keys: Dict[str, str]) -> StageResult:
    """Critic stage: critique the drafts"""
    model = pick_model_for_stage("critic", 0, "auto")
    logger.info(f"🔮 Router selected {model.id} for critic stage")

    # Build messages using production prompts
    messages = build_messages_for_stage("critic", ctx.user_question, {
        "analyst_output": ctx.analyst_output,
        "researcher_output": ctx.researcher_output,
        "creator_drafts": ctx.creator_drafts,
    })

    system_prompts = [m["content"] for m in messages if m["role"] == "system"]
    user_messages = [m["content"] for m in messages if m["role"] == "user"]

    combined_system = "\n\n".join(system_prompts)
    user_message = user_messages[0] if user_messages else ctx.user_question

    output = await call_model(
        provider=model.provider,
        model_name=model.model_name,
        system_prompt=combined_system,
        user_message=user_message,
        api_keys=api_keys,
        max_tokens=1500,
    )

    return StageResult(
        stage_id="critic",
        status="success",
        model_id=model.id,
        output=output,
    )


async def run_council(ctx: StageContext, api_keys: Dict[str, str]) -> StageResult:
    """
    Council stage: compare creator drafts and issue a verdict.

    This is the NEW stage that doesn't exist in V1!
    It looks at all creator outputs and decides which is best.
    """
    model = pick_model_for_stage("council", 0, "auto")
    logger.info(f"🔮 Router selected {model.id} for council stage")

    # Build messages using production prompts
    messages = build_messages_for_stage("council", ctx.user_question, {
        "analyst_output": ctx.analyst_output,
        "researcher_output": ctx.researcher_output,
        "creator_drafts": ctx.creator_drafts,
        "critic_output": ctx.critic_output,
    })

    system_prompts = [m["content"] for m in messages if m["role"] == "system"]
    user_messages = [m["content"] for m in messages if m["role"] == "user"]

    combined_system = "\n\n".join(system_prompts)
    user_message = user_messages[0] if user_messages else ctx.user_question

    output = await call_model(
        provider=model.provider,
        model_name=model.model_name,
        system_prompt=combined_system,
        user_message=user_message,
        api_keys=api_keys,
        max_tokens=500,
        json_mode=True,  # Request JSON response
    )

    # Parse council verdict
    try:
        verdict_json = json.loads(output)
        verdict = CouncilVerdict.from_json(verdict_json)
        ctx.council_verdict = asdict(verdict)
        logger.info(f"✅ Council verdict: Draft {verdict.best_draft_index} from {verdict.best_model_id}")
    except json.JSONDecodeError:
        logger.error(f"Failed to parse council verdict: {output}")
        # Fallback: pick first draft
        verdict = CouncilVerdict(
            best_draft_index=0,
            best_model_id=ctx.creator_drafts[0]["model_id"] if ctx.creator_drafts else "unknown",
            reasoning="Could not parse council response",
            must_keep_points=[],
            must_fix_issues=[],
            speculative_claims=[],
        )
        ctx.council_verdict = asdict(verdict)

    return StageResult(
        stage_id="council",
        status="success",
        model_id=model.id,
        output=json.dumps(ctx.council_verdict),
        metadata={"best_draft": verdict.best_draft_index},
    )


async def run_synth(ctx: StageContext, api_keys: Dict[str, str]) -> StageResult:
    """
    Synthesizer stage: write the final unified answer.

    Uses:
    - All creator drafts
    - Critic feedback
    - Council verdict

    The result is ONE polished answer that integrates the best ideas.
    """
    model = pick_model_for_stage("synth", 0, "auto")
    logger.info(f"🔮 Router selected {model.id} for synthesizer stage")

    # Build messages using production prompts
    messages = build_messages_for_stage("synth", ctx.user_question, {
        "analyst_output": ctx.analyst_output,
        "researcher_output": ctx.researcher_output,
        "creator_drafts": ctx.creator_drafts,
        "critic_output": ctx.critic_output,
        "council_verdict": ctx.council_verdict,
    })

    system_prompts = [m["content"] for m in messages if m["role"] == "system"]
    user_messages = [m["content"] for m in messages if m["role"] == "user"]

    combined_system = "\n\n".join(system_prompts)
    user_message = user_messages[0] if user_messages else ctx.user_question

    output = await call_model(
        provider=model.provider,
        model_name=model.model_name,
        system_prompt=combined_system,
        user_message=user_message,
        api_keys=api_keys,
        max_tokens=2500,
        temperature=0.4,  # Lower temp for final answer
    )

    return StageResult(
        stage_id="synth",
        status="success",
        model_id=model.id,
        output=output,
    )


# ============================================================================
# MAIN ORCHESTRATION
# ============================================================================

async def run_collaboration_v2(
    user_question: str,
    api_keys: Dict[str, str],
) -> Dict[str, Any]:
    """
    Run the full 6-stage collaboration pipeline with dynamic model selection.

    Returns a dict with all stage outputs and the final answer.
    """
    ctx = StageContext(user_question=user_question)

    logger.info("🚀 Starting collaboration pipeline (V2)")
    logger.info(f"User question: {user_question[:100]}...")

    results = {}

    # Stage 1: Analyst
    logger.info("📊 Stage 1/6: Analyst")
    result = await run_analyst(ctx, api_keys)
    results["analyst"] = result
    ctx.analyst_output = result.output

    # Stage 2: Researcher
    logger.info("📊 Stage 2/6: Researcher")
    result = await run_researcher(ctx, api_keys)
    results["researcher"] = result
    ctx.researcher_output = result.output

    # Stage 3: Creator (MULTI-MODEL!)
    logger.info("📊 Stage 3/6: Creator (multi-model)")
    result = await run_creator_multi(ctx, api_keys)
    results["creator"] = result

    # Stage 4: Critic
    logger.info("📊 Stage 4/6: Critic")
    result = await run_critic(ctx, api_keys)
    results["critic"] = result
    ctx.critic_output = result.output

    # Stage 5: Council (NEW!)
    logger.info("📊 Stage 5/6: Council (NEW!)")
    result = await run_council(ctx, api_keys)
    results["council"] = result

    # Stage 6: Synthesizer
    logger.info("📊 Stage 6/6: Synthesizer")
    result = await run_synth(ctx, api_keys)
    results["synth"] = result
    ctx.synth_output = result.output

    logger.info("✅ Collaboration pipeline complete!")

    return {
        "final_answer": ctx.synth_output,
        "stages": {
            stage_id: asdict(result) for stage_id, result in results.items()
        },
        "context": asdict(ctx),
    }
