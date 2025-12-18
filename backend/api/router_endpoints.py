"""
REST API endpoints for the Intelligent Router.
Provides routing, metrics, training, and management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio

from app.database import get_db
from app.api.deps import require_org_id
from app.services.model_registry import get_valid_models

# Import router components
from router import intelligent_router, router_metrics, router_evaluator
from router.config import UserPriority, MODEL_REGISTRY, get_available_models
from router.training.fine_tune import router_tuner, FineTuneConfig
from router.training.evaluate import RouterEvaluator

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class RouteRequest(BaseModel):
    """Request to route a query."""
    query: str = Field(..., min_length=1, description="User query to route")
    context: Optional[str] = Field(None, description="Previous conversation context")
    user_priority: UserPriority = Field(UserPriority.BALANCED, description="User's routing priority")
    force_model: Optional[str] = Field(None, description="Force specific model (bypasses routing)")


class RouteResponse(BaseModel):
    """Response from routing decision."""
    model: str
    task_type: str
    complexity: int
    confidence: float
    reasoning: str
    needs_web: bool
    estimated_tokens: int
    routing_time_ms: float
    method: str
    model_info: Optional[Dict[str, Any]]
    alternatives: Optional[List[Dict[str, Any]]]


class MetricsResponse(BaseModel):
    """Router metrics response."""
    total_requests: int
    avg_routing_time_ms: float
    cache_hit_rate: float
    accuracy: float
    model_usage: Dict[str, int]
    task_distribution: Dict[str, int]
    priority_distribution: Dict[str, int]
    performance_stats: Dict[str, Any]
    error_count: int
    recent_errors: List[Dict[str, Any]]


class EvaluationRequest(BaseModel):
    """Request to run router evaluation."""
    n_examples: int = Field(100, ge=10, le=1000, description="Number of examples to evaluate")
    user_priorities: Optional[List[UserPriority]] = Field(None, description="Priorities to test")


class EvaluationResponse(BaseModel):
    """Response from evaluation."""
    total_evaluations: int
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    avg_confidence: float
    avg_routing_time_ms: float
    model_accuracy: Dict[str, float]
    task_accuracy: Dict[str, float]
    cost_efficiency_score: float
    estimated_cost_savings_percent: float


class FineTuneRequest(BaseModel):
    """Request to start fine-tuning."""
    base_model: str = Field("gpt-4o-mini", description="Base model for fine-tuning")
    n_epochs: int = Field(3, ge=1, le=10, description="Number of training epochs")
    batch_size: int = Field(16, ge=1, le=64, description="Training batch size")
    learning_rate_multiplier: float = Field(2.0, ge=0.1, le=5.0, description="Learning rate multiplier")
    suffix: Optional[str] = Field(None, description="Model suffix")


class FineTuneResponse(BaseModel):
    """Response from fine-tuning request."""
    job_id: str
    status: str
    message: str
    estimated_cost: float


class ModelRegistryResponse(BaseModel):
    """Response with available models."""
    models: Dict[str, Dict[str, Any]]
    available_models: List[str]
    total_models: int


class RouterStatusResponse(BaseModel):
    """Router system status."""
    router_config: Dict[str, Any]
    metrics_summary: Dict[str, Any]
    available_models: List[str]
    fine_tuned_model: Optional[str]
    cache_stats: Dict[str, Any]


# =============================================================================
# ROUTING ENDPOINTS
# =============================================================================

@router.post("/route", response_model=RouteResponse)
async def route_query(
    request: RouteRequest,
    background_tasks: BackgroundTasks,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Route a user query to the optimal AI model.

    This endpoint uses the intelligent router to make routing decisions
    based on query analysis, cost optimization, and user preferences.
    """
    try:
        start_time = asyncio.get_event_loop().time()

        # Make routing decision
        decision = await intelligent_router.route(
            query=request.query,
            context=request.context,
            user_priority=request.user_priority,
            force_model=request.force_model
        )

        routing_time = (asyncio.get_event_loop().time() - start_time) * 1000

        # Update metrics in background
        background_tasks.add_task(
            router_metrics.record_request,
            routing_time_ms=routing_time,
            model=decision.model,
            task_type=decision.task_type,
            user_priority=request.user_priority.value,
            confidence=decision.confidence,
            cache_hit=False  # Would need to track this in the router
        )

        return RouteResponse(
            model=decision.model,
            task_type=decision.task_type,
            complexity=decision.complexity,
            confidence=decision.confidence,
            reasoning=decision.reasoning,
            needs_web=decision.needs_web,
            estimated_tokens=decision.estimated_tokens,
            routing_time_ms=decision.routing_time_ms,
            method=decision.method,
            model_info=decision.model_info,
            alternatives=decision.alternatives
        )

    except Exception as e:
        # Record error
        router_metrics.record_error(
            error_type="routing_error",
            error_message=str(e),
            query=request.query[:100]
        )

        raise HTTPException(
            status_code=500,
            detail=f"Routing failed: {str(e)}"
        )


@router.post("/route/batch")
async def route_batch_queries(
    requests: List[RouteRequest],
    background_tasks: BackgroundTasks,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Route multiple queries in batch.

    Useful for processing multiple queries efficiently.
    """
    if len(requests) > 50:
        raise HTTPException(
            status_code=400,
            detail="Batch size limited to 50 queries"
        )

    try:
        # Process batch
        tasks = [
            intelligent_router.route(
                query=req.query,
                context=req.context,
                user_priority=req.user_priority,
                force_model=req.force_model
            )
            for req in requests
        ]

        decisions = await asyncio.gather(*tasks)

        # Update metrics
        for req, decision in zip(requests, decisions):
            background_tasks.add_task(
                router_metrics.record_request,
                routing_time_ms=decision.routing_time_ms,
                model=decision.model,
                task_type=decision.task_type,
                user_priority=req.user_priority.value,
                confidence=decision.confidence
            )

        return {
            "results": [
                RouteResponse(
                    model=d.model,
                    task_type=d.task_type,
                    complexity=d.complexity,
                    confidence=d.confidence,
                    reasoning=d.reasoning,
                    needs_web=d.needs_web,
                    estimated_tokens=d.estimated_tokens,
                    routing_time_ms=d.routing_time_ms,
                    method=d.method,
                    model_info=d.model_info,
                    alternatives=d.alternatives
                ).dict()
                for d in decisions
            ],
            "batch_size": len(requests),
            "total_time_ms": sum(d.routing_time_ms for d in decisions)
        }

    except Exception as e:
        router_metrics.record_error(
            error_type="batch_routing_error",
            error_message=str(e)
        )

        raise HTTPException(
            status_code=500,
            detail=f"Batch routing failed: {str(e)}"
        )


# =============================================================================
# METRICS ENDPOINTS
# =============================================================================

@router.get("/metrics", response_model=MetricsResponse)
async def get_router_metrics():
    """Get comprehensive router performance metrics."""
    try:
        summary = router_metrics.get_summary()

        return MetricsResponse(
            total_requests=summary["total_requests"],
            avg_routing_time_ms=summary["avg_routing_time_ms"],
            cache_hit_rate=summary["cache_hit_rate"],
            accuracy=summary["accuracy"],
            model_usage=summary["model_usage"],
            task_distribution=summary["task_distribution"],
            priority_distribution=summary["priority_distribution"],
            performance_stats=summary["performance_stats"],
            error_count=summary["error_count"],
            recent_errors=summary["recent_errors"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics: {str(e)}"
        )


@router.get("/metrics/detailed")
async def get_detailed_metrics():
    """Get detailed router metrics and analytics."""
    try:
        return router_metrics.get_detailed_report()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get detailed metrics: {str(e)}"
        )


@router.post("/metrics/export")
async def export_metrics(filepath: str = "router_metrics_export.json"):
    """Export metrics to file."""
    try:
        router_metrics.export_metrics(filepath)
        return {"message": f"Metrics exported to {filepath}", "filepath": filepath}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export metrics: {str(e)}"
        )


# =============================================================================
# EVALUATION ENDPOINTS
# =============================================================================

@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_router(request: EvaluationRequest):
    """Run router evaluation on test dataset."""
    try:
        metrics = await router_evaluator.evaluate_on_dataset(
            n_examples=request.n_examples,
            user_priorities=request.user_priorities
        )

        return EvaluationResponse(
            total_evaluations=metrics.total_evaluations,
            accuracy=metrics.accuracy,
            precision=metrics.precision,
            recall=metrics.recall,
            f1_score=metrics.f1_score,
            avg_confidence=metrics.avg_confidence,
            avg_routing_time_ms=metrics.avg_routing_time_ms,
            model_accuracy=metrics.model_accuracy,
            task_accuracy=metrics.task_accuracy,
            cost_efficiency_score=metrics.cost_efficiency_score,
            estimated_cost_savings_percent=metrics.estimated_cost_savings
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Evaluation failed: {str(e)}"
        )


@router.post("/evaluate/benchmark")
async def benchmark_router(
    n_queries: int = 1000,
    concurrent_requests: int = 10
):
    """Run performance benchmark."""
    try:
        results = await router_evaluator.benchmark_routing_speed(
            n_queries=n_queries,
            concurrent_requests=concurrent_requests
        )

        return results

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Benchmark failed: {str(e)}"
        )


# =============================================================================
# TRAINING ENDPOINTS
# =============================================================================

@router.post("/train/prepare-data")
async def prepare_training_data(
    include_augmentation: bool = True,
    output_file: str = "router_training_data.jsonl"
):
    """Prepare training data for fine-tuning."""
    try:
        filepath = router_tuner.prepare_training_data(
            output_file=output_file,
            include_augmentation=include_augmentation
        )

        return {
            "message": "Training data prepared",
            "filepath": filepath,
            "include_augmentation": include_augmentation
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to prepare training data: {str(e)}"
        )


@router.post("/train/start", response_model=FineTuneResponse)
async def start_fine_tuning(request: FineTuneRequest):
    """Start fine-tuning job."""
    try:
        # Prepare config
        config = FineTuneConfig(
            base_model=request.base_model,
            n_epochs=request.n_epochs,
            batch_size=request.batch_size,
            learning_rate_multiplier=request.learning_rate_multiplier,
            suffix=request.suffix
        )

        # Start training
        job = router_tuner.quick_train_and_deploy(config)

        if not job:
            raise HTTPException(
                status_code=500,
                detail="Failed to start fine-tuning job"
            )

        # Estimate cost
        from router.training.fine_tune import estimate_training_cost
        cost_est = estimate_training_cost(
            n_examples=1000,  # Rough estimate
            base_model=request.base_model,
            n_epochs=request.n_epochs
        )

        return FineTuneResponse(
            job_id=job,
            status="started",
            message="Fine-tuning job started. Monitor with /train/status/{job_id}",
            estimated_cost=cost_est["estimated_cost_usd"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start fine-tuning: {str(e)}"
        )


@router.get("/train/status/{job_id}")
async def get_training_status(job_id: str):
    """Get status of fine-tuning job."""
    try:
        job = router_tuner.check_job_status(job_id)

        return {
            "job_id": job.job_id,
            "status": job.status,
            "model": job.model,
            "created_at": job.created_at.isoformat(),
            "fine_tuned_model": job.fine_tuned_model,
            "metrics": job.metrics
        }

    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found or error: {str(e)}"
        )


@router.post("/train/deploy/{job_id}")
async def deploy_fine_tuned_model(job_id: str):
    """Deploy a completed fine-tuned model."""
    try:
        model_id = router_tuner.deploy_model(job_id)

        if model_id:
            return {
                "message": f"Deployed fine-tuned model: {model_id}",
                "model_id": model_id,
                "status": "active"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to deploy model - job may not be completed"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deploy model: {str(e)}"
        )


@router.get("/train/jobs")
async def list_training_jobs(status_filter: Optional[str] = None):
    """List fine-tuning jobs."""
    try:
        jobs = router_tuner.list_jobs(status_filter=status_filter)

        return {
            "jobs": [
                {
                    "job_id": job.job_id,
                    "status": job.status,
                    "model": job.model,
                    "created_at": job.created_at.isoformat(),
                    "fine_tuned_model": job.fine_tuned_model
                }
                for job in jobs
            ],
            "total": len(jobs),
            "filter": status_filter
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list jobs: {str(e)}"
        )


# =============================================================================
# SYSTEM MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/models", response_model=ModelRegistryResponse)
async def get_available_models():
    """Get information about available models."""
    try:
        models_info = {}
        available = get_available_models()

        for model_id in available:
            caps = MODEL_REGISTRY.get(model_id)
            if caps:
                models_info[model_id] = {
                    "display_name": caps.display_name,
                    "provider": caps.provider,
                    "description": caps.description,
                    "cost_tier": caps.cost_tier.value,
                    "latency_tier": caps.latency_tier.value,
                    "supports_vision": caps.supports_vision,
                    "supports_web_search": caps.supports_web_search,
                    "best_for": [t.value for t in caps.best_for]
                }

        return ModelRegistryResponse(
            models=models_info,
            available_models=available,
            total_models=len(models_info)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get model registry: {str(e)}"
        )


@router.get("/status", response_model=RouterStatusResponse)
async def get_router_status():
    """Get comprehensive router system status."""
    try:
        from router.config import ROUTER_CONFIG

        return RouterStatusResponse(
            router_config={
                "fine_tuned_model_id": ROUTER_CONFIG.fine_tuned_model_id,
                "use_fine_tuned": ROUTER_CONFIG.use_fine_tuned,
                "fallback_model": ROUTER_CONFIG.fallback_model,
                "confidence_threshold": ROUTER_CONFIG.confidence_threshold,
                "enable_caching": ROUTER_CONFIG.enable_routing_cache
            },
            metrics_summary=router_metrics.get_summary(),
            available_models=get_available_models(),
            fine_tuned_model=ROUTER_CONFIG.fine_tuned_model_id,
            cache_stats=intelligent_router.get_cache_stats()
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get router status: {str(e)}"
        )


@router.post("/cache/clear")
async def clear_router_cache():
    """Clear the routing cache."""
    try:
        intelligent_router.clear_cache()
        return {"message": "Router cache cleared"}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )


@router.post("/reset-metrics")
async def reset_router_metrics():
    """Reset router metrics (admin operation)."""
    try:
        router_metrics.reset()
        return {"message": "Router metrics reset"}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset metrics: {str(e)}"
        )


# =============================================================================
# COST MONITORING ENDPOINTS
# =============================================================================

@router.get("/costs/summary")
async def get_cost_summary(hours: int = 24):
    """Get cost summary for the specified period."""
    try:
        from router.cost_optimizer import cost_optimizer
        summary = cost_optimizer.get_summary(hours=hours)

        return {
            "total_cost": summary.total_cost_usd,
            "total_requests": summary.total_requests,
            "avg_cost_per_request": summary.avg_cost_per_request,
            "estimated_savings_from_routing": summary.estimated_savings_usd,
            "cost_by_model": summary.cost_by_model,
            "tokens_by_model": summary.tokens_by_model,
            "period_start": summary.period_start.isoformat(),
            "period_end": summary.period_end.isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cost summary: {str(e)}"
        )


@router.get("/costs/efficiency")
async def get_cost_efficiency_report():
    """Get comprehensive cost efficiency report."""
    try:
        efficiency_report = intelligent_router.get_cost_efficiency_report()
        return efficiency_report

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cost efficiency report: {str(e)}"
        )


@router.post("/costs/budget/daily")
async def set_daily_budget(budget_usd: float):
    """Set daily budget limit."""
    try:
        if budget_usd <= 0:
            raise HTTPException(status_code=400, detail="Budget must be positive")

        intelligent_router.set_budget_limits(daily_usd=budget_usd)
        return {"message": f"Daily budget set to ${budget_usd:.2f}"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set daily budget: {str(e)}"
        )


@router.post("/costs/budget/monthly")
async def set_monthly_budget(budget_usd: float):
    """Set monthly budget limit."""
    try:
        if budget_usd <= 0:
            raise HTTPException(status_code=400, detail="Budget must be positive")

        intelligent_router.set_budget_limits(monthly_usd=budget_usd)
        return {"message": f"Monthly budget set to ${budget_usd:.2f}"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set monthly budget: {str(e)}"
        )


@router.get("/costs/budget/status")
async def get_budget_status():
    """Get current budget status."""
    try:
        from router.cost_optimizer import cost_optimizer
        return cost_optimizer.get_budget_status()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get budget status: {str(e)}"
        )


@router.get("/costs/compare")
async def compare_model_costs(input_tokens: int = 1000, output_tokens: int = 500):
    """Compare costs across all available models."""
    try:
        from router.cost_optimizer import cost_optimizer
        costs = cost_optimizer.compare_model_costs(input_tokens, output_tokens)

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "model_costs": costs,
            "cheapest_model": min(costs.items(), key=lambda x: x[1])[0] if costs else None,
            "most_expensive_model": max(costs.items(), key=lambda x: x[1])[0] if costs else None
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compare model costs: {str(e)}"
        )


@router.post("/costs/record")
async def record_api_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    query_type: str,
    was_routed: bool = True,
    could_have_used: Optional[str] = None
):
    """Manually record an API call cost (for integration with actual API calls)."""
    try:
        record = intelligent_router.record_model_usage(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            query_type=query_type,
            was_routed=was_routed,
            could_have_used=could_have_used
        )

        return {
            "recorded": True,
            "cost_usd": record.cost_usd,
            "timestamp": record.timestamp.isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record cost: {str(e)}"
        )
