"""Monitoring and logging for Collaborate pipeline.

Integrates with:
- OpenTelemetry (spans and traces)
- Structured logging (JSON)
- Metrics collection
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.services.collaborate.models import (
    CollaborateResponse,
    InternalStage,
    ExternalReview,
)

# Setup structured logger
logger = logging.getLogger(__name__)


class CollaborateObserver:
    """Track metrics and emit logs for collaborate runs."""

    def __init__(self, run_id: str, org_id: str, thread_id: str):
        self.run_id = run_id
        self.org_id = org_id
        self.thread_id = thread_id
        self.start_time = datetime.utcnow()
        self.events: List[Dict[str, Any]] = []

    def log_stage_start(self, role: str, model: str) -> None:
        """Log when a stage starts."""
        self.events.append({
            "event": "stage_start",
            "role": role,
            "model": model,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def log_stage_end(self, role: str, latency_ms: int, tokens_in: int = 0, tokens_out: int = 0) -> None:
        """Log when a stage completes."""
        self.events.append({
            "event": "stage_end",
            "role": role,
            "latency_ms": latency_ms,
            "tokens_input": tokens_in,
            "tokens_output": tokens_out,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def log_council_start(self) -> None:
        """Log council review start."""
        self.events.append({
            "event": "council_start",
            "timestamp": datetime.utcnow().isoformat(),
        })

    def log_council_review(self, source: str, stance: str, latency_ms: int = 0) -> None:
        """Log individual council review."""
        self.events.append({
            "event": "council_review",
            "source": source,
            "stance": stance,
            "latency_ms": latency_ms,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def log_completion(self, response: CollaborateResponse) -> None:
        """Log successful completion with full response metrics."""
        total_input_tokens = 0
        total_output_tokens = 0

        # Count tokens from stages
        for stage in response.internal_pipeline.stages:
            if stage.token_usage:
                total_input_tokens += stage.token_usage.input_tokens
                total_output_tokens += stage.token_usage.output_tokens

        # Count tokens from reviews
        for review in response.external_reviews:
            if review.token_usage:
                total_input_tokens += review.token_usage.input_tokens
                total_output_tokens += review.token_usage.output_tokens

        # Calculate stance distribution
        stance_counts = {
            "agree": sum(1 for r in response.external_reviews if r.stance == "agree"),
            "mixed": sum(1 for r in response.external_reviews if r.stance == "mixed"),
            "disagree": sum(1 for r in response.external_reviews if r.stance == "disagree"),
        }

        total_latency = response.meta.total_latency_ms or 0

        completion_log = {
            "event": "collaborate_run_complete",
            "run_id": self.run_id,
            "thread_id": self.thread_id,
            "org_id": self.org_id,
            "mode": response.meta.mode,
            "status": "success",
            "total_latency_ms": total_latency,
            "stages": [
                {
                    "role": stage.role,
                    "model": stage.model.display_name,
                    "latency_ms": stage.latency_ms,
                }
                for stage in response.internal_pipeline.stages
            ],
            "council": {
                "reviewed_by": [r.source for r in response.external_reviews],
                "stance_distribution": stance_counts,
            },
            "final_answer": {
                "confidence": response.final_answer.explanation.confidence_level
                if response.final_answer.explanation
                else "unknown",
                "model": response.final_answer.model.display_name,
            },
            "tokens": {
                "input": total_input_tokens,
                "output": total_output_tokens,
                "total": total_input_tokens + total_output_tokens,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Log as JSON
        logger.info(json.dumps(completion_log))

        # Also emit OpenTelemetry span if available
        try:
            from opentelemetry import trace

            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span("collaborate.run.complete") as span:
                span.set_attribute("collaborate.run_id", self.run_id)
                span.set_attribute("collaborate.thread_id", self.thread_id)
                span.set_attribute("collaborate.mode", response.meta.mode)
                span.set_attribute("collaborate.latency_ms", total_latency)
                span.set_attribute("collaborate.token_count", total_input_tokens + total_output_tokens)
                span.set_attribute("collaborate.confidence",
                                 response.final_answer.explanation.confidence_level
                                 if response.final_answer.explanation else "unknown")
        except ImportError:
            pass

    def log_error(self, error: str, stage: Optional[str] = None) -> None:
        """Log a failure."""
        error_log = {
            "event": "collaborate_run_error",
            "run_id": self.run_id,
            "thread_id": self.thread_id,
            "org_id": self.org_id,
            "status": "error",
            "stage": stage,
            "error_message": error,
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.error(json.dumps(error_log))

        try:
            from opentelemetry import trace

            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span("collaborate.run.error") as span:
                span.set_attribute("collaborate.run_id", self.run_id)
                span.set_attribute("collaborate.stage", stage or "unknown")
                span.set_attribute("error", error)
        except ImportError:
            pass


def emit_performance_metrics(response: CollaborateResponse) -> Dict[str, Any]:
    """Extract performance metrics from a collaborate response."""
    metrics = {
        "total_latency_ms": response.meta.total_latency_ms or 0,
        "stages": {},
        "council_count": len(response.external_reviews),
    }

    for stage in response.internal_pipeline.stages:
        metrics["stages"][stage.role] = {
            "latency_ms": stage.latency_ms or 0,
            "model": stage.model.model_slug,
        }

    return metrics


def format_collaborate_summary(response: CollaborateResponse) -> str:
    """Generate a human-readable summary of a collaborate run."""
    lines = [
        "📊 Collaborate Run Summary",
        "=" * 50,
        f"Run ID: {response.meta.run_id}",
        f"Mode: {response.meta.mode}",
        f"Total latency: {(response.meta.total_latency_ms or 0) / 1000:.2f}s",
        "",
        "Inner Pipeline:",
    ]

    for stage in response.internal_pipeline.stages:
        lines.append(
            f"  • {stage.role.ljust(15)} ({stage.model.display_name}) – {stage.latency_ms}ms"
        )

    lines.extend([
        "",
        "Council Reviews:",
        f"  • Total reviewers: {len(response.external_reviews)}",
    ])

    stance_counts = {
        "agree": sum(1 for r in response.external_reviews if r.stance == "agree"),
        "mixed": sum(1 for r in response.external_reviews if r.stance == "mixed"),
        "disagree": sum(1 for r in response.external_reviews if r.stance == "disagree"),
    }

    for stance, count in stance_counts.items():
        if count > 0:
            lines.append(f"  • {stance.capitalize()}: {count}")

    lines.extend([
        "",
        "Final Answer:",
        f"  • Model: {response.final_answer.model.display_name}",
        f"  • Confidence: {response.final_answer.explanation.confidence_level if response.final_answer.explanation else 'unknown'}",
    ])

    return "\n".join(lines)
