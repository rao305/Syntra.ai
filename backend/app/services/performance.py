"""Performance monitoring service for Phase 1 requirements."""
from __future__ import annotations

import time
from typing import Dict, Optional, Any
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

import logging
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for a single request."""

    # Timestamps
    request_start: float
    ttft: Optional[float] = None  # Time to first token
    request_end: Optional[float] = None

    # Token counts
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

    # Metadata
    provider: Optional[str] = None
    model: Optional[str] = None
    thread_id: Optional[str] = None
    user_id: Optional[str] = None

    # Performance
    latency_ms: Optional[float] = None
    streaming_enabled: bool = False
    cancelled: bool = False
    queue_wait_ms: Optional[int] = None  # Time spent waiting in rate-limit queue

    # Error info
    error: Optional[str] = None
    retry_count: int = 0
    
    def mark_ttft(self) -> float:
        """Mark time to first token and return it."""
        self.ttft = (time.perf_counter() - self.request_start) * 1000
        return self.ttft
    
    def mark_end(self) -> float:
        """Mark end time and calculate total latency."""
        self.request_end = time.perf_counter()
        self.latency_ms = (self.request_end - self.request_start) * 1000
        return self.latency_ms
    
    @property
    def ttft_seconds(self) -> Optional[float]:
        """TTFT in seconds."""
        return self.ttft / 1000 if self.ttft else None
    
    @property
    def latency_seconds(self) -> Optional[float]:
        """Total latency in seconds."""
        return self.latency_ms / 1000 if self.latency_ms else None
    
    @property
    def meets_ttft_target(self) -> bool:
        """Check if TTFT meets Phase 1 target (≤1.5s P95)."""
        return self.ttft_seconds is not None and self.ttft_seconds <= 1.5
    
    @property
    def meets_latency_target_p95(self) -> bool:
        """Check if latency meets Phase 1 P95 target (≤6s)."""
        return self.latency_seconds is not None and self.latency_seconds <= 6.0
    
    @property
    def meets_latency_target_p50(self) -> bool:
        """Check if latency meets Phase 1 P50 target (≤3.5s)."""
        return self.latency_seconds is not None and self.latency_seconds <= 3.5
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "ttft_ms": self.ttft,
            "latency_ms": self.latency_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "provider": self.provider,
            "model": self.model,
            "thread_id": self.thread_id,
            "streaming": self.streaming_enabled,
            "cancelled": self.cancelled,
            "queue_wait_ms": self.queue_wait_ms,
            "error": self.error,
            "retry_count": self.retry_count,
            "meets_ttft_target": self.meets_ttft_target,
            "meets_p95_target": self.meets_latency_target_p95,
            "meets_p50_target": self.meets_latency_target_p50,
        }


class PerformanceMonitor:
    """
    Performance monitoring for Phase 1 requirements.
    
    Tracks:
    - TTFT (Time to First Token): ≤ 1.5s P95
    - End-to-end latency: ≤ 6s P95, ≤ 3.5s P50
    - Token usage for cost monitoring
    - Error rates
    """
    
    def __init__(self):
        self.metrics: list[PerformanceMetrics] = []
        self._lock = asyncio.Lock()
        self._events: Dict[str, int] = defaultdict(int)  # Event name -> count
    
    def start_request(
        self,
        provider: str,
        model: str,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
        streaming: bool = False,
    ) -> PerformanceMetrics:
        """Start tracking a new request."""
        return PerformanceMetrics(
            request_start=time.perf_counter(),
            provider=provider,
            model=model,
            thread_id=thread_id,
            user_id=user_id,
            streaming_enabled=streaming,
        )
    
    def log_event(self, name: str):
        """Log an event (e.g., coalesce_leader, coalesce_follower)."""
        self._events[name] += 1
    
    async def record_metrics(self, metrics: PerformanceMetrics):
        """Record completed metrics."""
        async with self._lock:
            self.metrics.append(metrics)
            
            # Log warning if targets not met
            if not metrics.meets_ttft_target and metrics.ttft is not None:
                logger.warning("⚠️  TTFT target missed: {metrics.ttft_seconds:.2f}s (target: ≤1.5s)")
            
            if not metrics.meets_latency_target_p95 and metrics.latency_ms is not None:
                logger.warning("⚠️  Latency P95 target missed: {metrics.latency_seconds:.2f}s (target: ≤6s)")
    
    async def get_stats(self, last_n: Optional[int] = 100) -> Dict[str, Any]:
        """Get performance statistics."""
        async with self._lock:
            recent_metrics = self.metrics[-last_n:] if last_n else self.metrics

            if not recent_metrics:
                return {"total_requests": 0}

            # Calculate percentiles
            ttfts = [m.ttft_seconds for m in recent_metrics if m.ttft_seconds is not None]
            latencies = [m.latency_seconds for m in recent_metrics if m.latency_seconds is not None]
            queue_waits = [m.queue_wait_ms for m in recent_metrics if m.queue_wait_ms is not None]

            def percentile(data: list[float], p: float) -> float:
                if not data:
                    return 0.0
                sorted_data = sorted(data)
                index = int(len(sorted_data) * p)
                return sorted_data[min(index, len(sorted_data) - 1)]

            # Token stats
            total_tokens = sum(m.total_tokens or 0 for m in recent_metrics)
            prompt_tokens = sum(m.prompt_tokens or 0 for m in recent_metrics)
            completion_tokens = sum(m.completion_tokens or 0 for m in recent_metrics)

            # Error rate
            total_requests = len(recent_metrics)
            errors = sum(1 for m in recent_metrics if m.error is not None)
            error_rate = errors / total_requests if total_requests > 0 else 0

            return {
                "total_requests": total_requests,
                "ttft": {
                    "p50": percentile(ttfts, 0.5) if ttfts else None,
                    "p95": percentile(ttfts, 0.95) if ttfts else None,
                    "p99": percentile(ttfts, 0.99) if ttfts else None,
                    "target_p95": 1.5,
                    "meets_target": percentile(ttfts, 0.95) <= 1.5 if ttfts else False,
                },
                "latency": {
                    "p50": percentile(latencies, 0.5) if latencies else None,
                    "p95": percentile(latencies, 0.95) if latencies else None,
                    "p99": percentile(latencies, 0.99) if latencies else None,
                    "target_p50": 3.5,
                    "target_p95": 6.0,
                    "meets_p50_target": percentile(latencies, 0.5) <= 3.5 if latencies else False,
                    "meets_p95_target": percentile(latencies, 0.95) <= 6.0 if latencies else False,
                },
                "queue_wait_ms": {
                    "p50": percentile(queue_waits, 0.5) if queue_waits else None,
                    "p95": percentile(queue_waits, 0.95) if queue_waits else None,
                    "p99": percentile(queue_waits, 0.99) if queue_waits else None,
                    "target_p95": 1000,  # <1s P95
                    "meets_target": percentile(queue_waits, 0.95) <= 1000 if queue_waits else True,
                },
                "tokens": {
                    "total": total_tokens,
                    "prompt": prompt_tokens,
                    "completion": completion_tokens,
                    "avg_per_request": total_tokens / total_requests if total_requests > 0 else 0,
                },
                "errors": {
                    "total": errors,
                    "rate": error_rate,
                    "target": 0.01,  # <1% error rate
                    "meets_target": error_rate < 0.01,
                },
                "streaming": {
                    "enabled_requests": sum(1 for m in recent_metrics if m.streaming_enabled),
                    "percentage": sum(1 for m in recent_metrics if m.streaming_enabled) / total_requests * 100 if total_requests > 0 else 0,
                },
                "coalesce": {
                    "leaders": self._events.get("coalesce_leader", 0),
                    "followers": self._events.get("coalesce_follower", 0),
                },
            }


# Global performance monitor instance
performance_monitor = PerformanceMonitor()

