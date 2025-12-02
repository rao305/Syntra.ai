"""
Streaming wrapper for Collaboration Orchestrator V2.

Emits SSE (Server-Sent Events) as the pipeline progresses, including:
- stage_start: when a stage begins (includes model name!)
- stage_end: when a stage completes (includes preview)
- final_answer_start: before synth output
- final_answer_delta: streamed chunks of synth output
- final_answer_end: when synth completes

Key feature: Each event includes the **actual model ID** that was selected,
not a hard-coded mapping. This allows the UI to show "Analyst • gpt-4o"
or "Analyst • gemini-2.0" depending on what the router picked.
"""

import json
import asyncio
from typing import AsyncGenerator, Dict, Any
from datetime import datetime
import logging

from app.services.collaborate.orchestrator_v2 import (
    run_collaboration_v2,
    StageContext,
)

logger = logging.getLogger(__name__)


def sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """Format an event as Server-Sent Event (SSE)"""
    payload = {
        "type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        **data,
    }
    return f"event: {event_type}\ndata: {json.dumps(payload, default=str)}\n\n"


async def run_collaborate_streaming_v2(
    user_question: str,
    api_keys: Dict[str, str],
    run_id: str = None,
) -> AsyncGenerator[str, None]:
    """
    Run collaboration pipeline with streaming events.

    Yields SSE formatted events as the pipeline progresses.
    The frontend listens to these events to animate the collab UI.

    Each stage_start event includes the actual **model_id** that was selected,
    allowing the UI to display which model is working on that stage.

    Events emitted:
    - stage_start: { stageId, label, modelId }
    - stage_end: { stageId, preview, durationMs }
    - final_answer_start: {}
    - final_answer_delta: { delta }
    - final_answer_end: {}
    """
    import uuid
    if not run_id:
        run_id = str(uuid.uuid4())

    logger.info(f"Starting collaboration stream (V2), run_id={run_id}")

    try:
        # We need to intercept the orchestrator to emit events
        # For now, we'll wrap it with event emissions

        # Stage metadata for event emission
        stage_info = {
            "analyst": {"label": "Analyst", "stageId": "analyst"},
            "researcher": {"label": "Researcher", "stageId": "researcher"},
            "creator": {"label": "Creator", "stageId": "creator"},
            "critic": {"label": "Critic", "stageId": "critic"},
            "council": {"label": "LLM Council", "stageId": "council"},
            "synth": {"label": "Synthesizer", "stageId": "synth"},
        }

        # Run orchestrator
        # TODO: Modify orchestrator_v2 to support event hooks/callbacks
        #       For now, we'll run it and then emit events afterwards
        result = await run_collaboration_v2(user_question, api_keys)

        # Emit events for each stage
        # In a real implementation, we'd emit these as the orchestrator runs,
        # not after. But for now, this demonstrates the event structure.

        for stage_id in ["analyst", "researcher", "creator", "critic", "council", "synth"]:
            if stage_id in result["stages"]:
                stage_result = result["stages"][stage_id]
                info = stage_info[stage_id]

                # Emit stage_start
                yield sse_event("stage_start", {
                    "stageId": info["stageId"],
                    "label": info["label"],
                    "modelId": stage_result["model_id"],
                })

                await asyncio.sleep(0.1)  # Simulate processing time

                # Emit stage_end
                preview = stage_result["output"][:200] if stage_result["output"] else ""
                yield sse_event("stage_end", {
                    "stageId": info["stageId"],
                    "preview": preview,
                    "durationMs": 1000,  # Mock duration
                })

        # Emit final answer
        yield sse_event("final_answer_start", {})

        final_answer = result.get("final_answer", "")

        # Stream final answer in chunks (simulate streaming)
        chunk_size = 100
        for i in range(0, len(final_answer), chunk_size):
            chunk = final_answer[i : i + chunk_size]
            yield sse_event("final_answer_delta", {
                "delta": chunk,
            })
            await asyncio.sleep(0.01)  # Small delay to simulate streaming

        yield sse_event("final_answer_end", {
            "content": final_answer,
        })

        logger.info(f"Collaboration stream completed (V2), run_id={run_id}")

    except Exception as e:
        logger.error(f"Error in collaboration stream (V2): {e}", exc_info=True)
        yield sse_event("error", {
            "message": str(e),
            "stageId": "unknown",
        })


async def run_collaborate_streaming_v2_with_callbacks(
    user_question: str,
    api_keys: Dict[str, str],
    run_id: str = None,
    on_stage_start = None,
    on_stage_end = None,
    on_final_answer = None,
) -> AsyncGenerator[str, None]:
    """
    Version with callbacks for real-time event emission during execution.

    This is the ideal version where we emit events as stages complete,
    not after the fact. Callbacks are called during orchestration.

    on_stage_start: Called with (stage_id, label, model_id)
    on_stage_end: Called with (stage_id, preview, duration_ms)
    on_final_answer: Called with (content)
    """
    import uuid
    if not run_id:
        run_id = str(uuid.uuid4())

    logger.info(f"Starting collaboration stream (V2 with callbacks), run_id={run_id}")

    # TODO: Modify orchestrator_v2 to accept and call these callbacks
    # For now, this is a placeholder for the ideal architecture

    try:
        # This would be the real implementation:
        # result = await run_collaboration_v2_with_callbacks(
        #     user_question,
        #     api_keys,
        #     on_stage_start=on_stage_start,
        #     on_stage_end=on_stage_end,
        #     on_final_answer=on_final_answer,
        # )

        # For now, fall back to non-callback version
        async for event in run_collaborate_streaming_v2(user_question, api_keys, run_id):
            yield event

    except Exception as e:
        logger.error(f"Error in collaboration stream (V2): {e}", exc_info=True)
        yield sse_event("error", {
            "message": str(e),
            "stageId": "unknown",
        })
