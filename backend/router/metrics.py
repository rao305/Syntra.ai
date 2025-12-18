"""
Performance tracking and analytics for the intelligent router.
Provides comprehensive metrics, monitoring, and reporting capabilities.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import statistics

logger = logging.getLogger(__name__)

# Import cost optimizer for cost tracking integration
try:
    from .cost_optimizer import cost_optimizer
    COST_TRACKING_AVAILABLE = True
except ImportError:
    cost_optimizer = None
    COST_TRACKING_AVAILABLE = False


@dataclass
class RouterMetrics:
    """Comprehensive router performance metrics."""

    # Basic counters
    total_requests: int = 0
    total_routing_time_ms: float = 0
    cache_hits: int = 0
    cache_misses: int = 0

    # Accuracy metrics
    correct_predictions: int = 0
    total_predictions: int = 0

    # Model usage statistics
    model_usage: Dict[str, int] = field(default_factory=dict)
    model_performance: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Task type statistics
    task_usage: Dict[str, int] = field(default_factory=dict)

    # User priority statistics
    priority_usage: Dict[str, int] = field(default_factory=dict)

    # Error tracking
    errors: List[Dict[str, Any]] = field(default_factory=list)

    # Performance windows (rolling statistics)
    recent_latencies: deque = field(default_factory=lambda: deque(maxlen=1000))
    recent_accuracies: deque = field(default_factory=lambda: deque(maxlen=1000))

    # Time-based metrics
    hourly_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    daily_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def record_request(
        self,
        routing_time_ms: float,
        model: str,
        task_type: str,
        user_priority: str,
        confidence: float,
        is_correct: Optional[bool] = None,
        cache_hit: bool = False
    ):
        """Record a routing request."""

        self.total_requests += 1
        self.total_routing_time_ms += routing_time_ms

        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

        # Model usage
        self.model_usage[model] = self.model_usage.get(model, 0) + 1

        # Task usage
        self.task_usage[task_type] = self.task_usage.get(task_type, 0) + 1

        # Priority usage
        self.priority_usage[user_priority] = self.priority_usage.get(user_priority, 0) + 1

        # Performance tracking
        self.recent_latencies.append(routing_time_ms)

        if is_correct is not None:
            self.total_predictions += 1
            if is_correct:
                self.correct_predictions += 1
            self.recent_accuracies.append(1.0 if is_correct else 0.0)

        # Update time-based stats
        self._update_time_based_stats(routing_time_ms, model, confidence)

    def record_error(self, error_type: str, error_message: str, query: Optional[str] = None):
        """Record an error."""

        error_record = {
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "message": error_message,
            "query": query[:100] + "..." if query and len(query) > 100 else query
        }

        self.errors.append(error_record)

        # Keep only recent errors
        if len(self.errors) > 100:
            self.errors = self.errors[-50:]

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""

        avg_routing_time = self.total_routing_time_ms / self.total_requests if self.total_requests > 0 else 0
        cache_hit_rate = self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
        accuracy = self.correct_predictions / self.total_predictions if self.total_predictions > 0 else 0

        summary = {
            "total_requests": self.total_requests,
            "avg_routing_time_ms": round(avg_routing_time, 2),
            "cache_hit_rate": round(cache_hit_rate, 4),
            "accuracy": round(accuracy, 4),
            "model_usage": dict(self.model_usage),
            "task_distribution": dict(self.task_usage),
            "priority_distribution": dict(self.priority_usage),
            "performance_stats": self._calculate_performance_stats(),
            "error_count": len(self.errors),
            "recent_errors": self.errors[-5:] if self.errors else []
        }

        # Add cost efficiency data if available
        if COST_TRACKING_AVAILABLE and cost_optimizer:
            try:
                cost_summary = cost_optimizer.get_summary(hours=24)
                summary.update({
                    "cost_efficiency": {
                        "total_cost_usd": round(cost_summary.total_cost_usd, 4),
                        "avg_cost_per_request": round(cost_summary.avg_cost_per_request, 6),
                        "estimated_savings_usd": round(cost_summary.estimated_savings_usd, 4),
                        "cost_savings_percentage": round(
                            (cost_summary.estimated_savings_usd / cost_summary.total_cost_usd * 100)
                            if cost_summary.total_cost_usd > 0 else 0, 2
                        ),
                        "budget_status": cost_optimizer.get_budget_status()
                    }
                })
            except Exception as e:
                logger.warning(f"Failed to get cost metrics: {e}")

        return summary

    def get_detailed_report(self) -> Dict[str, Any]:
        """Get detailed performance report."""

        summary = self.get_summary()

        # Add more detailed breakdowns
        summary.update({
            "model_performance_details": self._get_model_performance_details(),
            "task_performance_details": self._get_task_performance_details(),
            "time_based_metrics": {
                "hourly": dict(self.hourly_stats),
                "daily": dict(self.daily_stats)
            },
            "error_analysis": self._analyze_errors(),
            "trends": self._calculate_trends()
        })

        return summary

    def _calculate_performance_stats(self) -> Dict[str, Any]:
        """Calculate detailed performance statistics."""

        if not self.recent_latencies:
            return {"error": "No recent data"}

        latencies = list(self.recent_latencies)
        accuracies = list(self.recent_accuracies) if self.recent_accuracies else []

        return {
            "latency_stats": {
                "min_ms": round(min(latencies), 2),
                "max_ms": round(max(latencies), 2),
                "avg_ms": round(statistics.mean(latencies), 2),
                "median_ms": round(statistics.median(latencies), 2),
                "p95_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 2),
                "p99_ms": round(sorted(latencies)[int(len(latencies) * 0.99)], 2)
            },
            "accuracy_stats": {
                "recent_accuracy": round(sum(accuracies) / len(accuracies), 4) if accuracies else 0,
                "total_accuracy": round(self.correct_predictions / self.total_predictions, 4) if self.total_predictions > 0 else 0
            },
            "throughput": {
                "requests_per_second": round(len(latencies) / (sum(latencies) / 1000), 2) if latencies else 0
            }
        }

    def _get_model_performance_details(self) -> Dict[str, Any]:
        """Get detailed per-model performance."""

        details = {}

        for model in self.model_usage.keys():
            # Get recent performance for this model
            model_latencies = []
            model_accuracies = []

            # Note: In a real implementation, we'd need to track per-model latency/accuracy
            # For now, return usage stats
            details[model] = {
                "usage_count": self.model_usage[model],
                "usage_percentage": round(self.model_usage[model] / self.total_requests * 100, 2) if self.total_requests > 0 else 0,
                "estimated_cost_impact": self._estimate_model_cost_impact(model)
            }

        return details

    def _get_task_performance_details(self) -> Dict[str, Any]:
        """Get detailed per-task performance."""

        details = {}

        for task in self.task_usage.keys():
            details[task] = {
                "usage_count": self.task_usage[task],
                "usage_percentage": round(self.task_usage[task] / self.total_requests * 100, 2) if self.total_requests > 0 else 0
            }

        return details

    def _estimate_model_cost_impact(self, model: str) -> Dict[str, Any]:
        """Estimate cost impact of using a specific model."""

        # This would need integration with the model registry
        # For now, return placeholder
        return {
            "relative_cost_score": 0.5,  # Placeholder
            "estimated_tokens_per_request": 500  # Placeholder
        }

    def _update_time_based_stats(
        self,
        routing_time_ms: float,
        model: str,
        confidence: float
    ):
        """Update time-based rolling statistics."""

        now = datetime.now()
        hour_key = now.strftime("%Y-%m-%d %H")
        day_key = now.strftime("%Y-%m-%d")

        # Hourly stats
        if hour_key not in self.hourly_stats:
            self.hourly_stats[hour_key] = {
                "requests": 0,
                "total_latency": 0,
                "models": defaultdict(int),
                "start_time": now.isoformat()
            }

        hour_stats = self.hourly_stats[hour_key]
        hour_stats["requests"] += 1
        hour_stats["total_latency"] += routing_time_ms
        hour_stats["models"][model] += 1

        # Daily stats
        if day_key not in self.daily_stats:
            self.daily_stats[day_key] = {
                "requests": 0,
                "total_latency": 0,
                "models": defaultdict(int),
                "start_time": now.isoformat()
            }

        day_stats = self.daily_stats[day_key]
        day_stats["requests"] += 1
        day_stats["total_latency"] += routing_time_ms
        day_stats["models"][model] += 1

        # Clean old stats (keep last 24 hours for hourly, 30 days for daily)
        self._clean_old_stats()

    def _clean_old_stats(self):
        """Clean old time-based statistics."""

        now = datetime.now()

        # Clean hourly stats older than 24 hours
        cutoff_hour = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H")
        self.hourly_stats = {
            k: v for k, v in self.hourly_stats.items()
            if k >= cutoff_hour
        }

        # Clean daily stats older than 30 days
        cutoff_day = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        self.daily_stats = {
            k: v for k, v in self.daily_stats.items()
            if k >= cutoff_day
        }

    def _analyze_errors(self) -> Dict[str, Any]:
        """Analyze error patterns."""

        if not self.errors:
            return {"total_errors": 0}

        error_types = defaultdict(int)
        recent_errors = [e for e in self.errors if self._is_recent_error(e)]

        for error in self.errors:
            error_types[error["type"]] += 1

        return {
            "total_errors": len(self.errors),
            "recent_errors": len(recent_errors),
            "error_types": dict(error_types),
            "most_common_error": max(error_types.items(), key=lambda x: x[1])[0] if error_types else None
        }

    def _is_recent_error(self, error: Dict[str, Any], hours: int = 24) -> bool:
        """Check if error is within recent time window."""

        try:
            error_time = datetime.fromisoformat(error["timestamp"])
            return (datetime.now() - error_time).total_seconds() < (hours * 3600)
        except (ValueError, KeyError) as e:
            logger.warning(f"Failed to parse error timestamp: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error checking error time: {e}")
            return False

    def _calculate_trends(self) -> Dict[str, Any]:
        """Calculate performance trends."""

        if len(self.recent_latencies) < 10:
            return {"error": "Insufficient data for trend analysis"}

        # Split data into halves for trend calculation
        half = len(self.recent_latencies) // 2
        first_half = list(self.recent_latencies)[:half]
        second_half = list(self.recent_latencies)[half:]

        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)

        latency_trend = "improving" if second_avg < first_avg else "degrading"

        return {
            "latency_trend": latency_trend,
            "latency_change_percent": round((second_avg - first_avg) / first_avg * 100, 2) if first_avg > 0 else 0,
            "first_half_avg": round(first_avg, 2),
            "second_half_avg": round(second_avg, 2)
        }

    def export_metrics(self, filepath: str):
        """Export metrics to JSON file."""

        data = {
            "export_timestamp": datetime.now().isoformat(),
            "metrics": self.get_detailed_report()
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Metrics exported to {filepath}")

    def reset(self):
        """Reset all metrics."""

        self.total_requests = 0
        self.total_routing_time_ms = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.correct_predictions = 0
        self.total_predictions = 0

        self.model_usage.clear()
        self.model_performance.clear()
        self.task_usage.clear()
        self.priority_usage.clear()
        self.errors.clear()

        self.recent_latencies.clear()
        self.recent_accuracies.clear()
        self.hourly_stats.clear()
        self.daily_stats.clear()

        logger.info("Metrics reset")


# =============================================================================
# MONITORING AND ALERTS
# =============================================================================

@dataclass
class MetricAlert:
    """Alert configuration for metrics."""

    name: str
    condition: str  # e.g., "accuracy < 0.8"
    threshold: float
    enabled: bool = True
    cooldown_minutes: int = 60  # Don't alert more often than this
    last_triggered: Optional[datetime] = None

    def should_trigger(self, metrics: RouterMetrics) -> Tuple[bool, str]:
        """
        Check if alert should trigger.

        Returns:
            (should_trigger, reason)
        """
        if not self.enabled:
            return False, "Alert disabled"

        # Check cooldown
        if self.last_triggered:
            since_last = (datetime.now() - self.last_triggered).total_seconds() / 60
            if since_last < self.cooldown_minutes:
                return False, f"Cooldown active ({self.cooldown_minutes - since_last:.1f} min remaining)"

        # Evaluate condition
        summary = metrics.get_summary()

        try:
            # Simple condition evaluation
            if "accuracy" in self.condition and summary["accuracy"] < self.threshold:
                return True, f"Accuracy {summary['accuracy']:.2%} below threshold {self.threshold:.2%}"
            elif "routing_time" in self.condition and summary["avg_routing_time_ms"] > self.threshold:
                return True, f"Avg routing time {summary['avg_routing_time_ms']:.2f}ms above threshold {self.threshold:.2f}ms"
            elif "cache_hit_rate" in self.condition and summary["cache_hit_rate"] < self.threshold:
                return True, f"Cache hit rate {summary['cache_hit_rate']:.2%} below threshold {self.threshold:.2%}"

        except KeyError:
            return False, "Invalid metric in condition"

        return False, "Condition not met"


class MetricsMonitor:
    """Monitor router metrics and trigger alerts."""

    def __init__(self, metrics: RouterMetrics):
        self.metrics = metrics
        self.alerts: List[MetricAlert] = []
        self.alert_history: List[Dict[str, Any]] = []

    def add_alert(self, alert: MetricAlert):
        """Add an alert configuration."""
        self.alerts.append(alert)

    def check_alerts(self) -> List[Dict[str, Any]]:
        """
        Check all alerts and return triggered ones.

        Returns:
            List of triggered alert information
        """
        triggered = []

        for alert in self.alerts:
            should_trigger, reason = alert.should_trigger(self.metrics)

            if should_trigger:
                alert_info = {
                    "timestamp": datetime.now().isoformat(),
                    "alert_name": alert.name,
                    "reason": reason,
                    "threshold": alert.threshold,
                    "current_metrics": self.metrics.get_summary()
                }

                triggered.append(alert_info)
                self.alert_history.append(alert_info)
                alert.last_triggered = datetime.now()

                logger.warning(f"Alert triggered: {alert.name} - {reason}")

        # Keep alert history manageable
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-50:]

        return triggered

    def get_alert_history(self) -> List[Dict[str, Any]]:
        """Get recent alert history."""
        return self.alert_history[-20:]  # Last 20 alerts

    def get_alert_status(self) -> Dict[str, Any]:
        """Get status of all alerts."""

        status = {}
        for alert in self.alerts:
            status[alert.name] = {
                "enabled": alert.enabled,
                "condition": alert.condition,
                "threshold": alert.threshold,
                "last_triggered": alert.last_triggered.isoformat() if alert.last_triggered else None,
                "cooldown_minutes": alert.cooldown_minutes
            }

        return status


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_default_alerts() -> List[MetricAlert]:
    """Create a set of default metric alerts."""

    return [
        MetricAlert(
            name="Low Accuracy Alert",
            condition="accuracy < 0.8",
            threshold=0.8
        ),
        MetricAlert(
            name="High Latency Alert",
            condition="routing_time > 1000",
            threshold=1000.0
        ),
        MetricAlert(
            name="Low Cache Hit Rate",
            condition="cache_hit_rate < 0.3",
            threshold=0.3
        )
    ]


def save_metrics_to_file(metrics: RouterMetrics, filepath: str):
    """Save metrics to a timestamped file."""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filepath}_{timestamp}.json"

    metrics.export_metrics(filename)
    return filename


# =============================================================================
# GLOBAL INSTANCES
# =============================================================================

# Global metrics instance
router_metrics = RouterMetrics()

# Global monitor instance
metrics_monitor = MetricsMonitor(router_metrics)
