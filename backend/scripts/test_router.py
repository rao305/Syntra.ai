#!/usr/bin/env python3
"""
Test and Evaluate the Intelligent Router

This script provides comprehensive testing and evaluation capabilities:
1. Accuracy evaluation on test datasets
2. Performance benchmarking
3. User priority impact analysis
4. Full evaluation suite

Usage:
    python scripts/test_router.py --help
"""

import argparse
import logging
import sys
import json
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from router.training.evaluate import router_evaluator, RouterEvaluator
from router import intelligent_router
from router.config import UserPriority
import asyncio

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Test and Evaluate the Intelligent Router")
    parser.add_argument(
        "--mode",
        choices=["accuracy", "benchmark", "priority", "full", "quick"],
        default="quick",
        help="Testing mode"
    )
    parser.add_argument(
        "--examples",
        type=int,
        default=100,
        help="Number of examples for evaluation"
    )
    parser.add_argument(
        "--queries",
        type=int,
        default=500,
        help="Number of queries for benchmarking"
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=10,
        help="Concurrent requests for benchmarking"
    )
    parser.add_argument(
        "--output",
        default="evaluation_results",
        help="Output directory for results"
    )
    parser.add_argument(
        "--priorities",
        nargs="+",
        choices=["speed", "cost", "quality", "balanced"],
        help="User priorities to test"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    try:
        if args.mode == "accuracy":
            await test_accuracy(args)
        elif args.mode == "benchmark":
            await test_performance(args)
        elif args.mode == "priority":
            await test_priority_impact(args)
        elif args.mode == "full":
            await run_full_evaluation(args)
        elif args.mode == "quick":
            await quick_test(args)

    except Exception as e:
        logger.error(f"Testing failed: {e}")
        sys.exit(1)


async def quick_test(args):
    """Quick test with basic metrics."""
    logger.info("🧪 Running quick router test...")

    # Simple accuracy test
    logger.info("Testing accuracy...")
    metrics = await router_evaluator.evaluate_on_dataset(n_examples=50)

    print("\n" + "="*50)
    print("ROUTER QUICK TEST RESULTS")
    print("="*50)
    print(".2f")
    print(".2f")
    print(".2f")
    print(".2f")
    print(".2f")
    print(".2f")
    print(".1f")
    print("\n📊 Top Model Performance:")
    for model, acc in sorted(metrics.model_accuracy.items(), key=lambda x: x[1], reverse=True)[:3]:
        print(".2f")
    print("\n📈 Top Task Performance:")
    for task, acc in sorted(metrics.task_accuracy.items(), key=lambda x: x[1], reverse=True)[:3]:
        print(".2f")
    print("="*50)

    # Performance benchmark
    logger.info("Testing performance...")
    perf_results = await router_evaluator.benchmark_routing_speed(n_queries=100)

    print("PERFORMANCE BENCHMARK (100 queries)")
    print("-" * 30)
    print(".2f")
    print(".2f")
    print(".2f")
    print(".2f")
    print(".2f")
    print(".2f")
    print(".2f")
    # Simple pass/fail
    if metrics.accuracy >= 0.7:
        print("✅ ACCURACY: PASS (≥70%)")
    else:
        print("❌ ACCURACY: FAIL (<70%)")

    if perf_results["p95_latency_ms"] <= 1000:
        print("✅ LATENCY: PASS (≤1000ms p95)")
    else:
        print("❌ LATENCY: FAIL (>1000ms p95)")

    print("="*50)


async def test_accuracy(args):
    """Test router accuracy."""
    logger.info(f"🎯 Testing router accuracy with {args.examples} examples...")

    # Parse priorities
    priorities = None
    if args.priorities:
        priorities = [UserPriority(p) for p in args.priorities]

    # Run evaluation
    metrics = await router_evaluator.evaluate_on_dataset(
        n_examples=args.examples,
        user_priorities=priorities
    )

    # Print results
    print("\n" + "="*60)
    print("ROUTER ACCURACY EVALUATION RESULTS")
    print("="*60)
    print(f"Total Evaluations: {metrics.total_evaluations}")
    print(f"Overall Accuracy: {metrics.accuracy:.2%}")
    print(f"Precision: {metrics.precision:.2%}")
    print(f"Recall: {metrics.recall:.2%}")
    print(f"F1 Score: {metrics.f1_score:.2%}")
    print(f"Avg Confidence: {metrics.avg_confidence:.2%}")
    print(f"Avg Routing Time: {metrics.avg_routing_time_ms:.2f}ms")
    print(f"Cost Efficiency Score: {metrics.cost_efficiency_score:.2%}")
    print(f"Estimated Cost Savings: {metrics.estimated_cost_savings:.1f}%")

    print("\n📊 MODEL PERFORMANCE:")
    print("-" * 30)
    for model, acc in sorted(metrics.model_accuracy.items(), key=lambda x: x[1], reverse=True):
        print(".2f")
    print("\n📈 TASK PERFORMANCE:")
    print("-" * 30)
    for task, acc in sorted(metrics.task_accuracy.items(), key=lambda x: x[1], reverse=True):
        print(".2f")
    print("\n⚡ PERFORMANCE STATS:")
    print("-" * 30)
    perf = metrics.routing_times
    print(f"Min Latency: {min(perf):.2f}ms")
    print(f"Max Latency: {max(perf):.2f}ms")
    print(f"Median Latency: {sorted(perf)[len(perf)//2]:.2f}ms")
    print(f"P95 Latency: {sorted(perf)[int(len(perf)*0.95)]:.2f}ms")

    print("\n🎯 CONFIDENCE DISTRIBUTION:")
    print("-" * 30)
    for bucket, count in metrics.confidence_distribution.items():
        pct = (count / metrics.total_evaluations) * 100
        print("2d")
    # Save detailed results
    if args.output:
        router_evaluator.save_evaluation_results(metrics, f"{args.output}/accuracy_test.json")
        logger.info(f"📄 Detailed results saved to {args.output}/accuracy_test.json")


async def test_performance(args):
    """Test router performance."""
    logger.info(f"⚡ Benchmarking router performance with {args.queries} queries...")

    results = await router_evaluator.benchmark_routing_speed(
        n_queries=args.queries,
        concurrent_requests=args.concurrent
    )

    print("\n" + "="*50)
    print("ROUTER PERFORMANCE BENCHMARK")
    print("="*50)
    print(f"Total Queries: {results['total_queries']}")
    print(f"Concurrent Requests: {results['concurrent_requests']}")
    print(f"Total Time: {results['total_time_seconds']:.2f}s")
    print(f"Throughput: {results['throughput_qps']:.1f} queries/second")

    print("\n⚡ LATENCY METRICS:")
    print("-" * 30)
    print(f"Average: {results['avg_latency_ms']:.2f}ms")
    print(f"P50 (Median): {results['p50_latency_ms']:.2f}ms")
    print(f"P95: {results['p95_latency_ms']:.2f}ms")
    print(f"P99: {results['p99_latency_ms']:.2f}ms")
    print(f"Min: {results['min_latency_ms']:.2f}ms")
    print(f"Max: {results['max_latency_ms']:.2f}ms")

    # Performance assessment
    print("\n📊 PERFORMANCE ASSESSMENT:")
    print("-" * 30)

    if results['throughput_qps'] >= 50:
        print("✅ THROUGHPUT: EXCELLENT (≥50 qps)")
    elif results['throughput_qps'] >= 20:
        print("✅ THROUGHPUT: GOOD (≥20 qps)")
    else:
        print("⚠️  THROUGHPUT: MODERATE (<20 qps)")

    if results['p95_latency_ms'] <= 500:
        print("✅ LATENCY: EXCELLENT (≤500ms p95)")
    elif results['p95_latency_ms'] <= 1000:
        print("✅ LATENCY: GOOD (≤1000ms p95)")
    else:
        print("⚠️  LATENCY: HIGH (>1000ms p95)")

    # Save results
    if args.output:
        with open(f"{args.output}/performance_benchmark.json", 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"📄 Results saved to {args.output}/performance_benchmark.json")


async def test_priority_impact(args):
    """Test user priority impact."""
    logger.info("🎛️  Testing user priority impact...")

    impact = await router_evaluator.evaluate_user_priority_impact()

    print("\n" + "="*50)
    print("USER PRIORITY IMPACT ANALYSIS")
    print("="*50)

    for priority, data in impact.items():
        print(f"\n🎯 PRIORITY: {priority.upper()}")
        print("-" * 30)
        print(f"Model Changes: {data['model_changes']}")
        print(f"Change Rate: {data['change_rate']:.1%}")
        print(f"Avg Confidence: {data['avg_confidence']:.2%}")

        if data['sample_results']:
            print("Sample Results:")
            for i, result in enumerate(data['sample_results'][:3]):
                print(f"  {i+1}. Expected: {result['original_expected']} → Routed: {result['routed_model']}")
                print(f"     Reason: {result['reasoning'][:60]}...")

    # Save results
    if args.output:
        with open(f"{args.output}/priority_impact.json", 'w') as f:
            json.dump(impact, f, indent=2)
        logger.info(f"📄 Results saved to {args.output}/priority_impact.json")


async def run_full_evaluation(args):
    """Run complete evaluation suite."""
    logger.info("🔬 Running full evaluation suite...")

    results = await router_evaluator.run_full_evaluation_suite(
        output_dir=args.output
    )

    print("\n" + "="*60)
    print("FULL ROUTER EVALUATION SUITE RESULTS")
    print("="*60)

    # Accuracy results
    acc = results.get("accuracy_evaluation", {})
    print("🎯 ACCURACY EVALUATION:")
    print(f"   Accuracy: {acc.get('accuracy', 0):.2%}")
    print(f"   F1 Score: {acc.get('f1_score', 0):.2%}")
    print(f"   Cost Savings: {acc.get('estimated_cost_savings_percent', 0):.1f}%")

    # Performance results
    perf = results.get("speed_benchmark", {})
    print("⚡ PERFORMANCE BENCHMARK:")
    print(f"   Throughput: {perf.get('throughput_qps', 0):.1f} qps")
    print(f"   P95 Latency: {perf.get('p95_latency_ms', 0):.1f}ms")

    # Router metrics
    metrics = results.get("router_metrics", {})
    print("📊 ROUTER METRICS:")
    print(f"   Total Requests: {metrics.get('total_requests', 0)}")
    print(f"   Cache Hit Rate: {metrics.get('cache_hit_rate', 0):.1%}")
    print(f"   Avg Latency: {metrics.get('avg_routing_time_ms', 0):.1f}ms")

    print(f"\n📄 Full results saved to {args.output}/")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
