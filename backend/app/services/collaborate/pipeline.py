"""Collaborate pipeline orchestrator (LLM council architecture)."""
import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path

from app.services.collaborate.models import (
    CollabState,
    InternalStage,
    InternalPipeline,
    CompressedReport,
    ExternalReview,
    FinalAnswer,
    FinalAnswerExplanation,
    CollaborateResponse,
    CollaborateRunMeta,
    ModelInfo,
)
from app.models.provider_key import ProviderType
from app.services.provider_dispatch import call_provider_adapter

logger = logging.getLogger(__name__)


# ---------- Helpers ----------

def now() -> datetime:
    """Return current datetime in UTC."""
    return datetime.utcnow()


def stage_id(role: str) -> str:
    """Generate a unique stage ID."""
    return f"stage_{role}_{uuid.uuid4().hex[:6]}"


def review_id(source: str) -> str:
    """Generate a unique review ID."""
    return f"rev_{source}_{uuid.uuid4().hex[:4]}"


def load_system_prompt(filename: str) -> str:
    """Load system prompt from file."""
    prompt_dir = Path(__file__).parent / "prompts"
    filepath = prompt_dir / filename
    with open(filepath, "r") as f:
        return f.read()


def map_provider_string_to_type(provider_str: str) -> ProviderType:
    """Map provider string to ProviderType enum."""
    provider_map = {
        "openai": ProviderType.OPENAI,
        "google": ProviderType.GEMINI,
        "perplexity": ProviderType.PERPLEXITY,
        "kimi": ProviderType.KIMI,
        "openrouter": ProviderType.OPENROUTER,
    }
    return provider_map.get(provider_str, ProviderType.OPENAI)


# ---------- LLM calls ----------

async def call_llm_json(
    *,
    provider: str,
    model: str,
    system_prompt: str,
    user_payload: dict,
    response_key: str = None,
    api_key: str,
) -> tuple[dict, object]:
    """
    Call an LLM and expect JSON response.

    If response_key is provided, extracts that key from the response.
    If response_key is None, returns the full parsed JSON.
    Returns (extracted_content, provider_response).
    """
    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": json.dumps(user_payload),
        },
    ]

    provider_type = map_provider_string_to_type(provider)
    response = await call_provider_adapter(
        provider=provider_type,
        model=model,
        messages=messages,
        api_key=api_key,
    )

    # Parse JSON from response
    try:
        parsed = json.loads(response.content)
    except json.JSONDecodeError:
        raise ValueError(f"LLM did not return valid JSON: {response.content}")

    # Extract the specific key if provided
    if response_key:
        if response_key not in parsed:
            raise ValueError(f"Response missing key '{response_key}': {parsed.keys()}")
        return parsed[response_key], response
    else:
        # Return full parsed JSON
        return parsed, response


# ---------- Inner team stages ----------

async def run_inner_stage(
    role: str,
    collab_state: CollabState,
    model: ModelInfo,
    system_prompt_template: str,
    api_key: str,
) -> tuple[CollabState, InternalStage]:
    """
    Run a single inner-team stage (analyst/researcher/creator/critic/internal_synth).

    Returns updated collab_state and the stage record.
    """
    # Substitute {{STAGE_ROLE}} in system prompt
    system_prompt = system_prompt_template.replace("{{STAGE_ROLE}}", role)

    # Prepare user payload
    user_payload = {
        "user_query": collab_state.user_query,
        "collab_state": json.loads(collab_state.model_dump_json()),
    }

    start = time.time()
    try:
        # Call LLM (expect JSON with stage_role, summary, collab_state_delta)
        full_response, provider_response = await call_llm_json(
            provider=model.provider,
            model=model.model_slug,
            system_prompt=system_prompt,
            user_payload=user_payload,
            response_key=None,  # Get full response
            api_key=api_key,
        )
    except Exception as e:
        raise RuntimeError(f"Stage '{role}' failed: {str(e)}")

    latency_ms = int((time.time() - start) * 1000)

    # Extract collab_state_delta from the response
    partial_state_dict = full_response.get("collab_state_delta", {})
    stage_summary = full_response.get("summary", "")

    # Merge partial state into current state
    merged_dict = {**collab_state.model_dump(), **partial_state_dict}
    updated_state = CollabState(**merged_dict)

    # Create stage record
    stage = InternalStage(
        id=stage_id(role),
        role=role,  # type: ignore
        title=role.replace("_", " ").title(),
        model=model,
        content=json.dumps(partial_state_dict, indent=2),
        created_at=now(),
        latency_ms=latency_ms,
        token_usage=(
            {
                "input_tokens": provider_response.prompt_tokens or 0,
                "output_tokens": provider_response.completion_tokens or 0,
            }
            if provider_response.prompt_tokens and provider_response.completion_tokens
            else None
        ),
    )

    return updated_state, stage


async def run_inner_team_pipeline(
    user_query: str,
    inner_team_prompt: str,
    models: dict[str, ModelInfo],
    api_keys: dict[str, str],
) -> tuple[CollabState, InternalPipeline]:
    """
    Orchestrate Analyst → Researcher → Creator → Critic → Internal Synth.

    `models`: {
        "analyst": ModelInfo,
        "researcher": ModelInfo,
        "creator": ModelInfo,
        "critic": ModelInfo,
        "internal_synth": ModelInfo,
    }
    `api_keys`: { "openai": "sk-...", "gemini": "...", ...}
    """
    state = CollabState(user_query=user_query)
    stages: list[InternalStage] = []

    for role in ["analyst", "researcher", "creator", "critic", "internal_synth"]:
        model = models[role]
        api_key = api_keys.get(model.provider, "")

        if not api_key:
            raise ValueError(f"No API key for provider '{model.provider}'")

        state, stage = await run_inner_stage(
            role=role,
            collab_state=state,
            model=model,
            system_prompt_template=inner_team_prompt,
            api_key=api_key,
        )
        stages.append(stage)

    pipeline = InternalPipeline(stages=stages)
    return state, pipeline


# ---------- Compression ----------

async def compress_internal_report(
    internal_report: str,
    compression_model: ModelInfo,
    api_key: str,
) -> CompressedReport:
    """Compress internal report to ~300 tokens for council review."""
    system_prompt = (
        "You are a compressor. Given a long internal report, "
        "produce a concise 250–400 token summary that preserves all key facts, "
        "tradeoffs, and uncertainties. Output JSON {\"summary\": \"...\"}"
    )
    user_payload = {"internal_report": internal_report}

    start = time.time()
    result, provider_response = await call_llm_json(
        provider=compression_model.provider,
        model=compression_model.model_slug,
        system_prompt=system_prompt,
        user_payload=user_payload,
        response_key="summary",
        api_key=api_key,
    )
    latency_ms = int((time.time() - start) * 1000)

    return CompressedReport(
        model=compression_model,
        content=result,
    )


# ---------- LLM Council reviews ----------

async def run_single_council_review(
    *,
    source: str,
    model: ModelInfo,
    reviewer_system_prompt: str,
    user_query: str,
    compressed_report: str,
    api_key: str,
) -> ExternalReview:
    """Run a single external reviewer."""
    payload = {
        "user_query": user_query,
        "compressed_report": compressed_report,
    }

    start = time.time()
    # Get full response (with stage_role, summary, collab_state_delta)
    full_response, provider_response = await call_llm_json(
        provider=model.provider,
        model=model.model_slug,
        system_prompt=reviewer_system_prompt,
        user_payload=payload,
        response_key=None,  # Get full response
        api_key=api_key,
    )
    latency_ms = int((time.time() - start) * 1000)

    # Extract external_review from collab_state_delta
    review_obj = full_response.get("collab_state_delta", {}).get("external_review", {})

    # Reconstruct content from review object
    content = "\n".join(
        [
            "Issues:",
            *[f"- {i}" for i in review_obj.get("issues", [])],
            "",
            "Missing points:",
            *[f"- {m}" for m in review_obj.get("missing_points", [])],
            "",
            "Suggestions:",
            *[f"- {s}" for s in review_obj.get("improvement_suggestions", [])],
            "",
            "Overall:",
            review_obj.get("overall_comment", ""),
        ]
    )

    stance = review_obj.get("stance", "unknown")

    return ExternalReview(
        id=review_id(source),
        source=source,  # type: ignore
        model=model,
        stance=stance,  # type: ignore
        content=content,
        created_at=now(),
        token_usage=(
            {
                "input_tokens": provider_response.prompt_tokens or 0,
                "output_tokens": provider_response.completion_tokens or 0,
            }
            if provider_response.prompt_tokens and provider_response.completion_tokens
            else None
        ),
        latency_ms=latency_ms,
    )


async def run_council(
    *,
    user_query: str,
    compressed_report: str,
    reviewer_system_prompt: str,
    reviewers: dict[str, ModelInfo],
    api_keys: dict[str, str],
) -> list[ExternalReview]:
    """
    Run LLM council in parallel.

    reviewers: {
        "perplexity": ModelInfo,
        "gemini": ModelInfo,
        ...
    }
    """
    tasks = []
    for source, model in reviewers.items():
        api_key = api_keys.get(model.provider, "")
        if not api_key:
            continue  # Skip if no API key

        tasks.append(
            run_single_council_review(
                source=source,
                model=model,
                reviewer_system_prompt=reviewer_system_prompt,
                user_query=user_query,
                compressed_report=compressed_report,
                api_key=api_key,
            )
        )

    if not tasks:
        return []

    return await asyncio.gather(*tasks)


# ---------- Director (final answer) ----------

async def run_director(
    *,
    user_query: str,
    internal_report: str,
    external_reviews: list[ExternalReview],
    director_system_prompt: str,
    director_model: ModelInfo,
    api_key: str,
) -> FinalAnswer:
    """Director synthesizes internal report + council reviews into final answer."""
    payload = {
        "user_query": user_query,
        "internal_report": internal_report,
        "external_reviews": [
            {
                "source": r.source,
                "stance": r.stance,
                "content": r.content,
            }
            for r in external_reviews
        ],
    }

    start = time.time()
    # Get full response (with stage_role, summary, final_answer)
    full_response, provider_response = await call_llm_json(
        provider=director_model.provider,
        model=director_model.model_slug,
        system_prompt=director_system_prompt,
        user_payload=payload,
        response_key=None,  # Get full response
        api_key=api_key,
    )
    latency_ms = int((time.time() - start) * 1000)

    # Extract final_answer from the response
    result = full_response.get("final_answer", {})

    content = result.get("content", "")
    confidence = result.get("confidence", "medium")
    notes = result.get("notes", [])

    explanation = FinalAnswerExplanation(
        used_internal_report=True,
        external_reviews_considered=len(external_reviews),
        confidence_level=confidence,  # type: ignore
    )

    return FinalAnswer(
        content=content,
        model=director_model,
        created_at=now(),
        explanation=explanation,
    )


# ---------- Top-level orchestrator ----------

async def run_collaborate(
    *,
    user_query: str,
    mode: str = "auto",
    inner_models: dict[str, ModelInfo],
    compression_model: ModelInfo,
    council_models: dict[str, ModelInfo],
    director_model: ModelInfo,
    api_keys: dict[str, str],
) -> CollaborateResponse:
    """
    Main orchestrator: inner team → compress → council → director.

    Args:
        user_query: User's question
        mode: "auto" or "manual"
        inner_models: Dict of { "analyst", "researcher", "creator", "critic", "internal_synth" } -> ModelInfo
        compression_model: ModelInfo for compressing internal report
        council_models: Dict of { "perplexity", "gemini", "gpt", "kimi", "openrouter" } -> ModelInfo
        director_model: ModelInfo for final answer
        api_keys: Dict of { provider_name -> api_key }

    Returns:
        CollaborateResponse with all stages
    """
    start_ts = now()
    start_ms = time.time()

    # Load system prompts
    inner_team_prompt = load_system_prompt("inner_team_system.txt")
    council_prompt = load_system_prompt("council_reviewer_system.txt")
    director_prompt = load_system_prompt("director_system.txt")

    # 1) Inner team pipeline
    collab_state, internal_pipeline = await run_inner_team_pipeline(
        user_query=user_query,
        inner_team_prompt=inner_team_prompt,
        models=inner_models,
        api_keys=api_keys,
    )

    if not collab_state.internal_report:
        raise RuntimeError("Internal report not generated by inner pipeline")

    # 2) Compress report
    compress_api_key = api_keys.get(compression_model.provider, "")
    if not compress_api_key:
        raise ValueError(f"No API key for compression model provider '{compression_model.provider}'")

    compressed = await compress_internal_report(
        internal_report=collab_state.internal_report.content,
        compression_model=compression_model,
        api_key=compress_api_key,
    )
    internal_pipeline.compressed_report = compressed

    # 3) LLM council reviews (parallel)
    external_reviews = await run_council(
        user_query=user_query,
        compressed_report=compressed.content,
        reviewer_system_prompt=council_prompt,
        reviewers=council_models,
        api_keys=api_keys,
    )

    # 4) Director final answer
    director_api_key = api_keys.get(director_model.provider, "")
    if not director_api_key:
        raise ValueError(f"No API key for director model provider '{director_model.provider}'")

    final_answer = await run_director(
        user_query=user_query,
        internal_report=collab_state.internal_report.content,
        external_reviews=external_reviews,
        director_system_prompt=director_prompt,
        director_model=director_model,
        api_key=director_api_key,
    )

    # 5) Render visualizations and generate images
    run_id = str(uuid.uuid4())
    visuals = None

    if collab_state.visualizations or collab_state.images:
        from app.services.collaborate.visualization_service import render_visualizations
        from app.services.collaborate.image_generation_service import generate_images, select_image_provider
        from app.services.collaborate.models import Visuals

        charts = []
        images = []

        # Render charts/visualizations
        if collab_state.visualizations:
            try:
                charts = await render_visualizations(collab_state.visualizations, run_id)
            except Exception as e:
                logger.error(f"Visualization rendering failed: {str(e)}")

        # Generate images
        if collab_state.images:
            try:
                image_provider, image_api_key = select_image_provider(api_keys)
                if image_provider and image_api_key:
                    images = await generate_images(
                        collab_state.images,
                        provider=image_provider,
                        api_key=image_api_key,
                    )
            except Exception as e:
                logger.error(f"Image generation failed: {str(e)}")

        if charts or images:
            visuals = Visuals(
                charts=charts,
                images=images,
                generated_at=now(),
            )

    # 6) Build response metadata
    finish_ts = now()
    total_latency_ms = int((time.time() - start_ms) * 1000)

    # Collect unique models used
    all_models = list(inner_models.values()) + [compression_model] + list(council_models.values()) + [director_model]
    unique_models = {(m.provider, m.model_slug): m for m in all_models}
    models_involved = list(unique_models.values())

    meta = CollaborateRunMeta(
        run_id=run_id,
        mode=mode,  # type: ignore
        started_at=start_ts,
        finished_at=finish_ts,
        total_latency_ms=total_latency_ms,
        models_involved=models_involved,
    )

    return CollaborateResponse(
        final_answer=final_answer,
        internal_pipeline=internal_pipeline,
        external_reviews=external_reviews,
        visuals=visuals,
        meta=meta,
    )
