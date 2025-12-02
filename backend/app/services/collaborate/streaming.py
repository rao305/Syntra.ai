"""Streaming wrapper for Collaborate pipeline.

Emits events as the pipeline progresses, allowing frontend to animate in real-time.
Includes both detailed stage events and high-level abstracted phase events for UI.
"""
import json
from typing import AsyncGenerator, Dict, Any
from datetime import datetime

from app.services.collaborate.models import ModelInfo
from app.services.collaborate.pipeline import run_collaborate, run_inner_stage, run_council, run_director, compress_internal_report, load_system_prompt, run_inner_team_pipeline

# Map internal roles to user-facing abstract phases
ROLE_TO_PHASE = {
    "analyst": "understand",
    "creator": "understand",
    "researcher": "research",
    "critic": "reason_refine",
    "internal_synth": "reason_refine",
    "council": "crosscheck",
    "director": "synthesize",
}

# Phase display labels
PHASE_LABELS = {
    "understand": "Understanding your query",
    "research": "Researching recent data and trends",
    "reason_refine": "Refining and organizing the answer",
    "crosscheck": "Cross-checking with other AI models",
    "synthesize": "Synthesizing final report",
}

# Phase indices for UI display (Step X of 5)
PHASE_INDICES = {
    "understand": 0,
    "research": 1,
    "reason_refine": 2,
    "crosscheck": 3,
    "synthesize": 4,
}


def sse_event(event_type: str, data: Dict[str, Any], run_id: str) -> str:
    """Format an event as Server-Sent Event with proper event: prefix."""
    payload = {
        "type": event_type,
        "run_id": run_id,
        "timestamp": datetime.utcnow().isoformat(),
        **data,
    }
    # Proper SSE format: "event: type\ndata: {json}\n\n"
    return f"event: {event_type}\ndata: {json.dumps(payload, default=str)}\n\n"


async def run_collaborate_streaming(
    user_query: str,
    mode: str = "auto",
    inner_models: dict[str, ModelInfo] = None,
    compression_model: ModelInfo = None,
    council_models: dict[str, ModelInfo] = None,
    director_model: ModelInfo = None,
    api_keys: dict[str, str] = None,
    run_id: str = None,
) -> AsyncGenerator[str, None]:
    """
    Run collaborate pipeline with streaming events.

    Yields SSE formatted events as the pipeline progresses:
    - stage_start
    - stage_delta (optional)
    - stage_end
    - council_progress
    - final_answer_delta
    - final_answer_done

    Then yields the complete CollaborateResponse at the end.
    """
    import uuid
    from app.services.collaborate.models import CollabState

    if not run_id:
        run_id = str(uuid.uuid4())

    if not inner_models:
        raise ValueError("inner_models required")

    # Load system prompts
    inner_team_prompt = load_system_prompt("inner_team_system.txt")
    council_prompt = load_system_prompt("council_reviewer_system.txt")
    director_prompt = load_system_prompt("director_system.txt")

    # Track all stages and reviews for final response
    all_stages = []
    all_reviews = []
    compressed_report_obj = None
    final_answer_obj = None

    try:
        # ===== 1. Inner Team Pipeline =====
        state = CollabState(user_query=user_query)
        inner_roles = ["analyst", "researcher", "creator", "critic", "internal_synth"]
        current_phase = None
        phase_start_time = None

        for idx, role in enumerate(inner_roles):
            step_index = idx
            model = inner_models[role]
            api_key = api_keys.get(model.provider, "")

            if not api_key:
                raise ValueError(f"No API key for provider '{model.provider}'")

            phase = ROLE_TO_PHASE[role]

            # Emit phase_start when entering a new phase
            if phase != current_phase:
                if current_phase is not None:
                    # Emit phase_end for previous phase
                    yield sse_event(
                        "phase_end",
                        {
                            "phase": current_phase,
                            "latency_ms": int((datetime.utcnow() - phase_start_time).total_seconds() * 1000) if phase_start_time else None,
                        },
                        run_id,
                    )

                # Start new phase
                current_phase = phase
                phase_start_time = datetime.utcnow()

                # Determine model_display for this phase
                # For "understand" phase, show the model of the first role (analyst)
                if phase == "understand":
                    phase_model_display = inner_models.get("analyst", model).display_name
                else:
                    phase_model_display = model.display_name

                yield sse_event(
                    "phase_start",
                    {
                        "phase": phase,
                        "label": PHASE_LABELS[phase],
                        "model_display": phase_model_display,
                        "step_index": PHASE_INDICES[phase],
                    },
                    run_id,
                )

            # Emit stage_start (detailed events still emitted for internal logging)
            yield sse_event(
                "stage_start",
                {
                    "role": role,
                    "label": role.replace("_", " ").title(),
                    "model_display": model.display_name,
                    "step_index": step_index,
                },
                run_id,
            )

            # Run stage
            try:
                state, stage = await run_inner_stage(
                    role=role,
                    collab_state=state,
                    model=model,
                    system_prompt_template=inner_team_prompt,
                    api_key=api_key,
                )
                all_stages.append(stage)

                # Emit stage_end
                yield sse_event(
                    "stage_end",
                    {
                        "role": role,
                        "latency_ms": stage.latency_ms,
                    },
                    run_id,
                )
            except Exception as e:
                yield sse_event(
                    "error",
                    {
                        "stage": role,
                        "message": f"Stage failed: {str(e)}",
                    },
                    run_id,
                )
                raise

        # Emit phase_end for the last inner phase
        if current_phase is not None:
            yield sse_event(
                "phase_end",
                {
                    "phase": current_phase,
                    "latency_ms": int((datetime.utcnow() - phase_start_time).total_seconds() * 1000) if phase_start_time else None,
                },
                run_id,
            )

        if not state.internal_report:
            raise RuntimeError("Internal report not generated")

        # ===== 2. Compress Report =====
        compress_api_key = api_keys.get(compression_model.provider, "")
        if not compress_api_key:
            raise ValueError(f"No API key for compression model")

        compressed = await compress_internal_report(
            internal_report=state.internal_report.content,
            compression_model=compression_model,
            api_key=compress_api_key,
        )
        compressed_report_obj = compressed

        # ===== 3. LLM Council (crosscheck phase) =====
        council_phase_start_time = datetime.utcnow()

        # Emit phase_start for crosscheck
        yield sse_event(
            "phase_start",
            {
                "phase": "crosscheck",
                "label": PHASE_LABELS["crosscheck"],
                "model_display": ", ".join([m.display_name for m in council_models.values()])[:100],
                "step_index": PHASE_INDICES["crosscheck"],
            },
            run_id,
        )

        # Emit stage_start for detailed tracking
        yield sse_event(
            "stage_start",
            {
                "role": "council",
                "label": "External Reviews",
                "model_display": "Multi-model Council",
                "step_index": 5,
            },
            run_id,
        )

        # Run council and track progress
        council_reviewers = list(council_models.items())
        completed = 0

        for source, model in council_reviewers:
            api_key = api_keys.get(model.provider, "")
            if not api_key:
                continue

            try:
                from app.services.collaborate.pipeline import run_single_council_review

                review = await run_single_council_review(
                    source=source,
                    model=model,
                    reviewer_system_prompt=council_prompt,
                    user_query=user_query,
                    compressed_report=compressed.content,
                    api_key=api_key,
                )
                all_reviews.append(review)
                completed += 1

                # Emit progress
                # Count stances
                stance_counts = {
                    "agree": sum(1 for r in all_reviews if r.stance == "agree"),
                    "mixed": sum(1 for r in all_reviews if r.stance == "mixed"),
                    "disagree": sum(1 for r in all_reviews if r.stance == "disagree"),
                }

                yield sse_event(
                    "council_progress",
                    {
                        "completed": completed,
                        "total": len(council_reviewers),
                        "stance_counts": stance_counts,
                    },
                    run_id,
                )
            except Exception as e:
                print(f"Council review failed for {source}: {e}")
                continue

        # Emit council done (detailed stage event)
        yield sse_event(
            "stage_end",
            {
                "role": "council",
                "latency_ms": None,
            },
            run_id,
        )

        # Emit phase_end for crosscheck
        yield sse_event(
            "phase_end",
            {
                "phase": "crosscheck",
                "latency_ms": int((datetime.utcnow() - council_phase_start_time).total_seconds() * 1000),
            },
            run_id,
        )

        # ===== 4. Director Final Answer (synthesize phase) =====
        director_phase_start_time = datetime.utcnow()

        # Emit phase_start for synthesize
        yield sse_event(
            "phase_start",
            {
                "phase": "synthesize",
                "label": PHASE_LABELS["synthesize"],
                "model_display": director_model.display_name,
                "step_index": PHASE_INDICES["synthesize"],
            },
            run_id,
        )

        # Emit stage_start for detailed tracking
        yield sse_event(
            "stage_start",
            {
                "role": "director",
                "label": "Director",
                "model_display": director_model.display_name,
                "step_index": 6,
            },
            run_id,
        )

        director_api_key = api_keys.get(director_model.provider, "")
        if not director_api_key:
            raise ValueError("No API key for director model")

        final_answer = await run_director(
            user_query=user_query,
            internal_report=state.internal_report.content,
            external_reviews=all_reviews,
            director_system_prompt=director_prompt,
            director_model=director_model,
            api_key=director_api_key,
        )
        final_answer_obj = final_answer

        # Emit phase_delta with preview of final answer
        preview_text = (final_answer.content[:80] + "...") if len(final_answer.content) > 80 else final_answer.content
        yield sse_event(
            "phase_delta",
            {
                "phase": "synthesize",
                "delta": preview_text,
            },
            run_id,
        )

        # Emit final_answer_start to signal start of answer streaming
        yield sse_event(
            "final_answer_start",
            {},
            run_id,
        )

        # Stream final answer content (simulate token-by-token)
        # In a real streaming director call, you'd get chunks
        for char in final_answer.content:
            yield sse_event(
                "final_answer_delta",
                {
                    "delta": char,
                },
                run_id,
            )

        # Emit phase_end for synthesize
        yield sse_event(
            "phase_end",
            {
                "phase": "synthesize",
                "latency_ms": int((datetime.utcnow() - director_phase_start_time).total_seconds() * 1000),
            },
            run_id,
        )

        # ===== 5. Visualization & Image Generation =====
        visuals_obj = None

        if state.visualizations or state.images:
            viz_phase_start_time = datetime.utcnow()

            # Emit phase_start for visualization
            yield sse_event(
                "phase_start",
                {
                    "phase": "visualize",
                    "label": "Generating visualizations and images...",
                    "model_display": "Charts & Images",
                    "step_index": 5,  # New phase after synthesize
                },
                run_id,
            )

            try:
                from app.services.collaborate.visualization_service import render_visualizations
                from app.services.collaborate.image_generation_service import generate_images, select_image_provider
                from app.services.collaborate.models import Visuals

                charts = []
                images = []

                # Render charts
                if state.visualizations:
                    try:
                        charts = await render_visualizations(state.visualizations, run_id)
                        yield sse_event(
                            "visualization_progress",
                            {
                                "type": "charts",
                                "count": len(charts),
                                "total": len(state.visualizations),
                            },
                            run_id,
                        )
                    except Exception as e:
                        print(f"Visualization rendering failed: {e}")

                # Generate images
                if state.images:
                    try:
                        image_provider, image_api_key = select_image_provider(api_keys)
                        if image_provider and image_api_key:
                            images = await generate_images(
                                state.images,
                                provider=image_provider,
                                api_key=image_api_key,
                            )
                            yield sse_event(
                                "visualization_progress",
                                {
                                    "type": "images",
                                    "count": len(images),
                                    "total": len(state.images),
                                },
                                run_id,
                            )
                    except Exception as e:
                        print(f"Image generation failed: {e}")

                if charts or images:
                    visuals_obj = Visuals(
                        charts=charts,
                        images=images,
                        generated_at=datetime.utcnow(),
                    )

            except Exception as e:
                print(f"Visualization generation failed: {e}")

            # Emit phase_end for visualization
            yield sse_event(
                "phase_end",
                {
                    "phase": "visualize",
                    "latency_ms": int((datetime.utcnow() - viz_phase_start_time).total_seconds() * 1000),
                },
                run_id,
            )

        # ===== 6. Complete Response =====
        from app.services.collaborate.models import (
            CollaborateRunMeta,
            CollaborateResponse,
            InternalPipeline,
        )

        meta = CollaborateRunMeta(
            run_id=run_id,
            mode=mode,  # type: ignore
            started_at=all_stages[0].created_at if all_stages else datetime.utcnow(),
            finished_at=datetime.utcnow(),
            models_involved=list({(m.provider, m.model_slug): m for m in [
                *inner_models.values(),
                compression_model,
                *council_models.values(),
                director_model,
            ]}.values()),
        )

        response = CollaborateResponse(
            final_answer=final_answer_obj,
            internal_pipeline=InternalPipeline(
                stages=all_stages,
                compressed_report=compressed_report_obj,
            ),
            external_reviews=all_reviews,
            visuals=visuals_obj,
            meta=meta,
        )

        # Emit final_answer_end with confidence and full response
        yield sse_event(
            "final_answer_end",
            {
                "confidence": "high",  # Could be determined by quality metrics
                "full_response": json.loads(response.model_dump_json(default=str)),
            },
            run_id,
        )

    except Exception as e:
        yield sse_event(
            "error",
            {
                "message": f"Pipeline failed: {str(e)}",
                "error_code": "PIPELINE_ERROR",
            },
            run_id,
        )
        raise
