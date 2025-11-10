"""Metrics API endpoints."""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.observability import metrics_collector

router = APIRouter()


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """
    Get system-wide metrics summary.

    Returns request counts, latency stats, and error breakdown.
    """
    return metrics_collector.get_summary()


@router.get("/metrics/org/{org_id}")
async def get_org_metrics(org_id: str) -> Dict[str, Any]:
    """
    Get metrics for a specific organization.

    Useful for per-org dashboards and usage monitoring.
    """
    return metrics_collector.get_org_metrics(org_id)
