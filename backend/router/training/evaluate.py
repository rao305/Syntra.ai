"""
Router evaluation and benchmarking.
Evaluates routing accuracy, performance, and provides detailed metrics.
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import asyncio
import statistics

from .dataset import TRAINING_EXAMPLES, RoutingExample
from ..intelligent_router import IntelligentRouter, RoutingDecision
from ..config import UserPriority, MODEL_REGISTRY, get_available_models

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Result of evaluating a single routing decision."""
    query: str
    expected_model: str
    predicted_model: str
    expected_task_type: str
    predicted_task_type: str
    confidence: float
    is_correct: bool
    routing_time_ms: float
    user_priority: str
    context_length: int

    @property
    def accuracy_score(self) -> float:
        """Return 1.0 for correct, 0.0 for incorrect."""
        return 1.0 if self.is_correct else 0.0


@dataclass
class EvaluationMetrics:
    """Comprehensive evaluation metrics."""
    total_evaluations: int
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    avg_confidence: float
    avg_routing_time_ms: float

    # Per-model metrics
    model_accuracy: Dict[str, float]
    model_precision: Dict[str, float]
    model_recall: Dict[str, float]

    # Per-task metrics
    task_accuracy: Dict[str, float]

    # Performance metrics
    routing_times: List[float]
    confidence_distribution: Dict[str, int]

    # Cost analysis
    estimated_cost_savings: float
    cost_efficiency_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_evaluations": self.total_evaluations,
            "accuracy": round(self.accuracy, 4),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
            "avg_confidence": round(self.avg_confidence, 4),
            "avg_routing_time_ms": round(self.avg_routing_time_ms, 2),
            "model_accuracy": {k: round(v, 4) for k, v in self.model_accuracy.items()},
            "model_precision": {k: round(v, 4) for k, v in self.model_precision.items()},
            "model_recall": {k: round(v, 4) for k, v in self.model_recall.items()},
            "task_accuracy": {k: round(v, 4) for k, v in self.task_accuracy.items()},
            "routing_time_stats": {
                "min": round(min(self.routing_times), 2),
                "max": round(max(self.routing_times), 2),
                "median": round(statistics.median(self.routing_times), 2),
                "p95": round(sorted(self.routing_times)[int(len(self.routing_times) * 0.95)], 2)
            },
            "confidence_distribution": self.confidence_distribution,
            "estimated_cost_savings_percent": round(self.estimated_cost_savings, 2),
            "cost_efficiency_score": round(self.cost_efficiency_score, 4)
        }


class RouterEvaluator:
    """
    Evaluates the performance of the intelligent router.
    Provides comprehensive metrics and benchmarking capabilities.
    """

    def __init__(self, router: Optional[IntelligentRouter] = None):
        self.router = router or IntelligentRouter()

    async def evaluate_on_dataset(
        self,
        test_examples: Optional[List[RoutingExample]] = None,
        n_examples: int = 100,
        user_priorities: Optional[List[UserPriority]] = None
    ) -> EvaluationMetrics:
        """
        Evaluate router performance on a test dataset.

        Args:
            test_examples: Custom test examples, uses TRAINING_EXAMPLES subset if None
            n_examples: Number of examples to test (if using default dataset)
            user_priorities: List of user priorities to test, tests all if None

        Returns:
            Comprehensive evaluation metrics
        """
        if test_examples is None:
            # Use subset of training examples for evaluation
            test_examples = TRAINING_EXAMPLES[:n_examples]

        if user_priorities is None:
            user_priorities = list(UserPriority)

        logger.info(f"Starting evaluation on {len(test_examples)} examples with {len(user_priorities)} priority settings")

        all_results = []

        # Evaluate each combination
        for priority in user_priorities:
            logger.info(f"Evaluating with user priority: {priority.value}")

            for example in test_examples:
                result = await self._evaluate_single_example(example, priority)
                all_results.append(result)

        # Calculate comprehensive metrics
        metrics = self._calculate_metrics(all_results)

        logger.info(f"Evaluation complete. Accuracy: {metrics.accuracy:.2%}")
        return metrics

    async def _evaluate_single_example(
        self,
        example: RoutingExample,
        user_priority: UserPriority
    ) -> EvaluationResult:
        """Evaluate a single routing example."""

        start_time = time.time()

        # Make routing decision
        decision = await self.router.route(
            query=example.query,
            context=example.context,
            user_priority=user_priority,
            force_model=None
        )

        routing_time = (time.time() - start_time) * 1000

        # Check correctness
        is_correct = decision.model == example.expected_model

        return EvaluationResult(
            query=example.query,
            expected_model=example.expected_model,
            predicted_model=decision.model,
            expected_task_type=example.task_type,
            predicted_task_type=decision.task_type,
            confidence=decision.confidence,
            is_correct=is_correct,
            routing_time_ms=routing_time,
            user_priority=user_priority.value,
            context_length=len(example.context) if example.context else 0
        )

    def _calculate_metrics(self, results: List[EvaluationResult]) -> EvaluationMetrics:
        """Calculate comprehensive evaluation metrics."""

        total = len(results)
        correct_predictions = sum(1 for r in results if r.is_correct)
        accuracy = correct_predictions / total if total > 0 else 0

        # Confidence metrics
        confidences = [r.confidence for r in results]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        # Routing time metrics
        routing_times = [r.routing_time_ms for r in results]
        avg_routing_time = sum(routing_times) / len(routing_times) if routing_times else 0

        # Per-model metrics
        model_stats = self._calculate_model_metrics(results)

        # Per-task metrics
        task_stats = self._calculate_task_metrics(results)

        # Confidence distribution
        confidence_dist = self._calculate_confidence_distribution(results)

        # Cost analysis
        cost_analysis = self._calculate_cost_analysis(results)

        # Calculate precision/recall (treating each model as a binary classification)
        # For simplicity, we'll use macro-averaged metrics
        precision = sum(model_stats["precision"].values()) / len(model_stats["precision"]) if model_stats["precision"] else 0
        recall = sum(model_stats["recall"].values()) / len(model_stats["recall"]) if model_stats["recall"] else 0
        f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        return EvaluationMetrics(
            total_evaluations=total,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            avg_confidence=avg_confidence,
            avg_routing_time_ms=avg_routing_time,
            model_accuracy=model_stats["accuracy"],
            model_precision=model_stats["precision"],
            model_recall=model_stats["recall"],
            task_accuracy=task_stats,
            routing_times=routing_times,
            confidence_distribution=confidence_dist,
            estimated_cost_savings=cost_analysis["estimated_savings_percent"],
            cost_efficiency_score=cost_analysis["efficiency_score"]
        )

    def _calculate_model_metrics(self, results: List[EvaluationResult]) -> Dict[str, Dict[str, float]]:
        """Calculate per-model accuracy, precision, and recall."""

        # Get all models that appear in results
        all_models = set(r.expected_model for r in results) | set(r.predicted_model for r in results)

        accuracy = {}
        precision = {}
        recall = {}

        for model in all_models:
            # Accuracy: correct predictions for this model / total predictions for this model
            model_predictions = [r for r in results if r.predicted_model == model]
            correct_predictions = [r for r in model_predictions if r.is_correct]
            accuracy[model] = len(correct_predictions) / len(model_predictions) if model_predictions else 0

            # Precision: true positives / (true positives + false positives)
            # True positives: predicted this model and was correct
            # False positives: predicted this model but was wrong
            true_positives = len(correct_predictions)
            false_positives = len([r for r in results if r.predicted_model == model and not r.is_correct])
            precision[model] = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0

            # Recall: true positives / (true positives + false negatives)
            # False negatives: should have predicted this model but didn't
            false_negatives = len([r for r in results if r.expected_model == model and r.predicted_model != model])
            recall[model] = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0

        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall
        }

    def _calculate_task_metrics(self, results: List[EvaluationResult]) -> Dict[str, float]:
        """Calculate per-task accuracy."""

        task_results = {}
        for result in results:
            task = result.expected_task_type
            if task not in task_results:
                task_results[task] = []
            task_results[task].append(result.is_correct)

        task_accuracy = {}
        for task, correctness_list in task_results.items():
            task_accuracy[task] = sum(correctness_list) / len(correctness_list)

        return task_accuracy

    def _calculate_confidence_distribution(self, results: List[EvaluationResult]) -> Dict[str, int]:
        """Calculate confidence score distribution."""

        bins = {
            "0.0-0.2": 0,
            "0.2-0.4": 0,
            "0.4-0.6": 0,
            "0.6-0.8": 0,
            "0.8-1.0": 0
        }

        for result in results:
            confidence = result.confidence
            if confidence < 0.2:
                bins["0.0-0.2"] += 1
            elif confidence < 0.4:
                bins["0.2-0.4"] += 1
            elif confidence < 0.6:
                bins["0.4-0.6"] += 1
            elif confidence < 0.8:
                bins["0.6-0.8"] += 1
            else:
                bins["0.8-1.0"] += 1

        return bins

    def _calculate_cost_analysis(self, results: List[EvaluationResult]) -> Dict[str, float]:
        """Calculate cost efficiency metrics."""

        # Get cost scores for models
        model_costs = {}
        for model_id, caps in MODEL_REGISTRY.items():
            model_costs[model_id] = caps.get_cost_score()

        # Calculate baseline cost (always using most expensive model)
        max_cost_model = max(model_costs.items(), key=lambda x: x[1])[0]
        baseline_cost = sum(model_costs[max_cost_model] for _ in results)

        # Calculate actual cost based on router decisions
        actual_cost = sum(model_costs.get(r.predicted_model, 1.0) for r in results)

        # Cost savings percentage
        savings_percent = (baseline_cost - actual_cost) / baseline_cost * 100 if baseline_cost > 0 else 0

        # Efficiency score (accuracy weighted by cost savings)
        accuracy = sum(1 for r in results if r.is_correct) / len(results)
        efficiency_score = accuracy * (1 + savings_percent / 100)

        return {
            "estimated_savings_percent": savings_percent,
            "efficiency_score": efficiency_score
        }

    async def benchmark_routing_speed(
        self,
        n_queries: int = 1000,
        concurrent_requests: int = 10
    ) -> Dict[str, Any]:
        """
        Benchmark routing speed and performance.

        Args:
            n_queries: Number of queries to test
            concurrent_requests: Number of concurrent requests

        Returns:
            Performance benchmark results
        """
        logger.info(f"Benchmarking routing speed with {n_queries} queries, {concurrent_requests} concurrent")

        # Generate test queries
        test_queries = []
        for i in range(n_queries):
            # Use variety of query types
            if i % 4 == 0:
                query = f"What is {i} + {i*2}?"
            elif i % 4 == 1:
                query = f"Write a function to calculate fibonacci({i})"
            elif i % 4 == 2:
                query = f"What are the latest developments in AI for {2024 + (i % 5)}?"
            else:
                query = f"Tell me about machine learning algorithm number {i}"

            test_queries.append(query)

        # Run benchmark
        start_time = time.time()
        latencies = []

        # Process in batches for concurrency
        for i in range(0, len(test_queries), concurrent_requests):
            batch = test_queries[i:i + concurrent_requests]

            batch_start = time.time()
            tasks = [
                self.router.route(query=q, user_priority=UserPriority.BALANCED)
                for q in batch
            ]
            await asyncio.gather(*tasks)
            batch_latency = (time.time() - batch_start) * 1000 / len(batch)
            latencies.extend([batch_latency] * len(batch))

        total_time = time.time() - start_time

        # Calculate statistics
        avg_latency = sum(latencies) / len(latencies)
        p50_latency = sorted(latencies)[len(latencies) // 2]
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
        max_latency = max(latencies)
        min_latency = min(latencies)

        throughput = n_queries / total_time  # queries per second

        return {
            "total_queries": n_queries,
            "total_time_seconds": round(total_time, 2),
            "throughput_qps": round(throughput, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "p50_latency_ms": round(p50_latency, 2),
            "p95_latency_ms": round(p95_latency, 2),
            "p99_latency_ms": round(p99_latency, 2),
            "min_latency_ms": round(min_latency, 2),
            "max_latency_ms": round(max_latency, 2),
            "concurrent_requests": concurrent_requests
        }

    async def evaluate_user_priority_impact(self) -> Dict[str, Any]:
        """
        Evaluate how different user priorities affect routing decisions.

        Returns:
            Analysis of priority impact
        """
        logger.info("Evaluating user priority impact...")

        # Use subset of examples
        test_examples = TRAINING_EXAMPLES[:50]

        priority_results = {}

        for priority in UserPriority:
            results = []
            for example in test_examples:
                decision = await self.router.route(
                    query=example.query,
                    context=example.context,
                    user_priority=priority
                )
                results.append({
                    "original_expected": example.expected_model,
                    "routed_model": decision.model,
                    "confidence": decision.confidence,
                    "reasoning": decision.reasoning
                })

            # Analyze results
            model_changes = sum(1 for r in results if r["original_expected"] != r["routed_model"])
            avg_confidence = sum(r["confidence"] for r in results) / len(results)

            priority_results[priority.value] = {
                "model_changes": model_changes,
                "change_rate": model_changes / len(results),
                "avg_confidence": avg_confidence,
                "sample_results": results[:5]  # First 5 examples
            }

        return priority_results

    def save_evaluation_results(
        self,
        metrics: EvaluationMetrics,
        filepath: str = "router_evaluation_results.json"
    ):
        """Save evaluation results to file."""

        results = {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics.to_dict(),
            "evaluation_type": "comprehensive_router_evaluation"
        }

        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"Saved evaluation results to {filepath}")

    async def run_full_evaluation_suite(
        self,
        output_dir: str = "evaluation_results"
    ) -> Dict[str, Any]:
        """
        Run a complete evaluation suite.

        Args:
            output_dir: Directory to save results

        Returns:
            Summary of all evaluation results
        """
        logger.info("Running full evaluation suite...")

        results = {}

        # 1. Accuracy evaluation
        logger.info("Running accuracy evaluation...")
        accuracy_metrics = await self.evaluate_on_dataset(n_examples=200)
        results["accuracy_evaluation"] = accuracy_metrics.to_dict()

        # 2. Speed benchmark
        logger.info("Running speed benchmark...")
        speed_results = await self.benchmark_routing_speed(n_queries=500)
        results["speed_benchmark"] = speed_results

        # 3. User priority impact
        logger.info("Evaluating user priority impact...")
        priority_impact = await self.evaluate_user_priority_impact()
        results["priority_impact"] = priority_impact

        # 4. Router metrics summary
        router_metrics = self.router.get_metrics_summary()
        results["router_metrics"] = router_metrics

        # Save comprehensive results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{output_dir}/full_evaluation_{timestamp}.json"

        os.makedirs(output_dir, exist_ok=True)

        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"Full evaluation suite complete. Results saved to {filename}")

        return results


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

async def quick_evaluation(router: Optional[IntelligentRouter] = None) -> EvaluationMetrics:
    """
    Quick evaluation using default settings.

    Args:
        router: Router to evaluate, creates new one if None

    Returns:
        Evaluation metrics
    """
    evaluator = RouterEvaluator(router)
    return await evaluator.evaluate_on_dataset(n_examples=50)


def compare_routers(
    router1: IntelligentRouter,
    router2: IntelligentRouter,
    test_examples: Optional[List[RoutingExample]] = None
) -> Dict[str, Any]:
    """
    Compare two router implementations.

    Args:
        router1: First router
        router2: Second router
        test_examples: Test examples to use

    Returns:
        Comparison results
    """
    if test_examples is None:
        test_examples = TRAINING_EXAMPLES[:100]

    async def evaluate_router(router, name):
        evaluator = RouterEvaluator(router)
        metrics = await evaluator.evaluate_on_dataset(test_examples, n_examples=len(test_examples))
        return {
            "name": name,
            "accuracy": metrics.accuracy,
            "avg_confidence": metrics.avg_confidence,
            "avg_routing_time": metrics.avg_routing_time_ms,
            "cost_savings": metrics.estimated_cost_savings
        }

    async def run_comparison():
        result1 = await evaluate_router(router1, "Router1")
        result2 = await evaluate_router(router2, "Router2")
        return [result1, result2]

    # Run comparison (would need to be called in async context)
    # For now, return placeholder
    return {
        "comparison_note": "Use in async context to run actual comparison",
        "example_usage": "results = await compare_routers(router1, router2)"
    }


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

router_evaluator = RouterEvaluator()

