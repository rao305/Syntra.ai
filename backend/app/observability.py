"""Observability and metrics tracking."""
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class ErrorClass(str, Enum):
    """Error classification for observability."""
    PROVIDER_ERROR = "provider_error"  # External provider failures
    AUTH_ERROR = "auth_error"  # Authentication/authorization failures
    VALIDATION_ERROR = "validation_error"  # Input validation errors
    DB_ERROR = "db_error"  # Database errors
    RATE_LIMIT_ERROR = "rate_limit_error"  # Rate limiting
    TIMEOUT_ERROR = "timeout_error"  # Request timeouts
    UNKNOWN_ERROR = "unknown_error"  # Unknown errors


@dataclass
class RequestMetrics:
    """Metrics for a single request."""
    path: str
    method: str
    status_code: int
    duration_ms: float
    org_id: str | None = None
    provider: str | None = None
    error_class: ErrorClass | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class MetricsCollector:
    """
    In-memory metrics collector for Phase 1.5.

    In production, this would be replaced with Prometheus, DataDog, or similar.
    For now, we keep last N requests in memory for debugging.
    """

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.requests: list[RequestMetrics] = []

        # Aggregated metrics
        self.request_count_by_path: Dict[str, int] = defaultdict(int)
        self.request_count_by_org: Dict[str, int] = defaultdict(int)
        self.request_count_by_provider: Dict[str, int] = defaultdict(int)
        self.error_count_by_class: Dict[str, int] = defaultdict(int)
        self.latency_by_path: Dict[str, list[float]] = defaultdict(list)

    def record_request(self, metrics: RequestMetrics):
        """Record request metrics."""
        # Store in history (FIFO)
        self.requests.append(metrics)
        if len(self.requests) > self.max_history:
            self.requests.pop(0)

        # Update aggregations
        self.request_count_by_path[metrics.path] += 1

        if metrics.org_id:
            self.request_count_by_org[metrics.org_id] += 1

        if metrics.provider:
            self.request_count_by_provider[metrics.provider] += 1

        if metrics.error_class:
            self.error_count_by_class[metrics.error_class.value] += 1

        # Track latency (keep last 100 per path for percentile calculations)
        self.latency_by_path[metrics.path].append(metrics.duration_ms)
        if len(self.latency_by_path[metrics.path]) > 100:
            self.latency_by_path[metrics.path].pop(0)

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return {
            "total_requests": len(self.requests),
            "requests_by_path": dict(self.request_count_by_path),
            "requests_by_org": dict(self.request_count_by_org),
            "requests_by_provider": dict(self.request_count_by_provider),
            "errors_by_class": dict(self.error_count_by_class),
            "latency_stats": self._get_latency_stats(),
        }

    def get_org_metrics(self, org_id: str) -> Dict[str, Any]:
        """Get metrics for a specific organization."""
        org_requests = [r for r in self.requests if r.org_id == org_id]

        provider_requests = defaultdict(int)
        provider_errors = defaultdict(int)

        for req in org_requests:
            if req.provider:
                provider_requests[req.provider] += 1
                if req.error_class:
                    provider_errors[req.provider] += 1

        return {
            "org_id": org_id,
            "total_requests": len(org_requests),
            "requests_by_provider": dict(provider_requests),
            "errors_by_provider": dict(provider_errors),
        }

    def _get_latency_stats(self) -> Dict[str, Any]:
        """Calculate latency statistics."""
        stats = {}

        for path, latencies in self.latency_by_path.items():
            if not latencies:
                continue

            sorted_latencies = sorted(latencies)
            n = len(sorted_latencies)

            stats[path] = {
                "count": n,
                "min_ms": round(sorted_latencies[0], 2),
                "max_ms": round(sorted_latencies[-1], 2),
                "avg_ms": round(sum(sorted_latencies) / n, 2),
                "p50_ms": round(sorted_latencies[n // 2], 2),
                "p95_ms": round(sorted_latencies[int(n * 0.95)], 2) if n > 1 else round(sorted_latencies[0], 2),
                "p99_ms": round(sorted_latencies[int(n * 0.99)], 2) if n > 1 else round(sorted_latencies[0], 2),
            }

        return stats


# Global metrics collector instance
metrics_collector = MetricsCollector()


def classify_error(exception: Exception) -> ErrorClass:
    """
    Classify an exception into an error class.

    This helps with debugging and alerting.
    """
    error_str = str(exception).lower()
    exception_name = type(exception).__name__.lower()

    # Provider errors
    if any(keyword in error_str for keyword in ["openai", "perplexity", "gemini", "openrouter"]):
        return ErrorClass.PROVIDER_ERROR

    # HTTP-specific errors
    if "401" in error_str or "403" in error_str or "unauthorized" in error_str:
        return ErrorClass.AUTH_ERROR

    if "429" in error_str or "rate limit" in error_str:
        return ErrorClass.RATE_LIMIT_ERROR

    if "timeout" in error_str or "timeout" in exception_name:
        return ErrorClass.TIMEOUT_ERROR

    # Validation errors
    if "validation" in exception_name or "422" in error_str:
        return ErrorClass.VALIDATION_ERROR

    # Database errors
    if any(keyword in exception_name for keyword in ["sql", "database", "postgres"]):
        return ErrorClass.DB_ERROR

    return ErrorClass.UNKNOWN_ERROR
