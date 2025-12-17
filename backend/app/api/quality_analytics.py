"""
Quality Analytics API endpoints

Provides endpoints for retrieving and analyzing quality metrics
from collaboration runs.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.security import set_rls_context
from app.api.deps import require_org_id
from app.models.collaborate import CollaborateRun

router = APIRouter()
logger = logging.getLogger(__name__)


class QualityMetricsResponse(BaseModel):
    """Individual quality metrics for a collaboration run."""
    run_id: str
    timestamp: datetime
    query_complexity: int
    overall_score: float
    substance_score: float
    completeness_score: float
    depth_score: float
    accuracy_score: float
    quality_gate_passed: bool
    duration_ms: Optional[int] = None


class QualityAnalyticsSummary(BaseModel):
    """Summary statistics for quality metrics."""
    total_runs: int
    avg_overall_score: float
    avg_substance_score: float
    avg_completeness_score: float
    avg_depth_score: float
    avg_accuracy_score: float
    pass_rate: float
    avg_complexity: float
    runs_by_complexity: Dict[int, int]
    runs_by_status: Dict[str, int]


class QualityAnalyticsResponse(BaseModel):
    """Response containing quality analytics data."""
    data: List[QualityMetricsResponse]
    summary: QualityAnalyticsSummary
    total_count: int
    page: int
    page_size: int


@router.get("/quality", response_model=QualityAnalyticsResponse)
async def get_quality_analytics(
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
    thread_id: Optional[str] = Query(None, description="Filter by thread ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Items per page"),
    min_quality_score: Optional[float] = Query(None, ge=0, le=10, description="Minimum overall quality score"),
    complexity_level: Optional[int] = Query(None, ge=1, le=5, description="Filter by complexity level"),
    passed_only: bool = Query(False, description="Only include runs that passed quality gate"),
):
    """
    Retrieve quality metrics analytics.

    Returns paginated quality metrics for collaboration runs with optional filtering.
    Includes summary statistics and distribution data.
    """
    await set_rls_context(db, org_id)

    try:
        # Build base query
        since_date = datetime.utcnow() - timedelta(days=days)

        query = select(CollaborateRun).where(
            and_(
                CollaborateRun.started_at >= since_date,
                CollaborateRun.status == "success",
                CollaborateRun.overall_quality_score.isnot(None)  # Only runs with quality scores
            )
        )

        # Apply filters
        if thread_id:
            query = query.where(CollaborateRun.thread_id == thread_id)

        if min_quality_score is not None:
            query = query.where(CollaborateRun.overall_quality_score >= min_quality_score)

        if complexity_level is not None:
            query = query.where(CollaborateRun.query_complexity == complexity_level)

        if passed_only:
            query = query.where(CollaborateRun.quality_gate_passed == True)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total_count = count_result.scalar() or 0

        # Apply pagination
        query = query.order_by(desc(CollaborateRun.started_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute query
        result = await db.execute(query)
        runs = result.scalars().all()

        # Convert to response models
        data = [
            QualityMetricsResponse(
                run_id=run.id,
                timestamp=run.started_at,
                query_complexity=run.query_complexity or 3,
                overall_score=run.overall_quality_score or 0.0,
                substance_score=run.substance_score or 0.0,
                completeness_score=run.completeness_score or 0.0,
                depth_score=run.depth_score or 0.0,
                accuracy_score=run.accuracy_score or 0.0,
                quality_gate_passed=run.quality_gate_passed or False,
                duration_ms=run.duration_ms,
            )
            for run in runs
        ]

        # Calculate summary statistics (on all filtered data, not just current page)
        summary_query = select(CollaborateRun).where(
            and_(
                CollaborateRun.started_at >= since_date,
                CollaborateRun.status == "success",
                CollaborateRun.overall_quality_score.isnot(None)
            )
        )

        # Apply same filters to summary query
        if thread_id:
            summary_query = summary_query.where(CollaborateRun.thread_id == thread_id)
        if min_quality_score is not None:
            summary_query = summary_query.where(CollaborateRun.overall_quality_score >= min_quality_score)
        if complexity_level is not None:
            summary_query = summary_query.where(CollaborateRun.query_complexity == complexity_level)
        if passed_only:
            summary_query = summary_query.where(CollaborateRun.quality_gate_passed == True)

        summary_result = await db.execute(summary_query)
        all_runs = summary_result.scalars().all()

        if len(all_runs) > 0:
            total_runs = len(all_runs)
            passed_runs = sum(1 for r in all_runs if r.quality_gate_passed)

            # Calculate averages
            avg_overall = sum(r.overall_quality_score or 0 for r in all_runs) / total_runs
            avg_substance = sum(r.substance_score or 0 for r in all_runs) / total_runs
            avg_completeness = sum(r.completeness_score or 0 for r in all_runs) / total_runs
            avg_depth = sum(r.depth_score or 0 for r in all_runs) / total_runs
            avg_accuracy = sum(r.accuracy_score or 0 for r in all_runs) / total_runs
            avg_complexity = sum(r.query_complexity or 3 for r in all_runs) / total_runs

            # Distribution by complexity
            complexity_dist = {}
            for run in all_runs:
                level = run.query_complexity or 3
                complexity_dist[level] = complexity_dist.get(level, 0) + 1

            # Distribution by status
            status_dist = {}
            for run in all_runs:
                status = "passed" if run.quality_gate_passed else "failed"
                status_dist[status] = status_dist.get(status, 0) + 1

            summary = QualityAnalyticsSummary(
                total_runs=total_runs,
                avg_overall_score=round(avg_overall, 2),
                avg_substance_score=round(avg_substance, 2),
                avg_completeness_score=round(avg_completeness, 2),
                avg_depth_score=round(avg_depth, 2),
                avg_accuracy_score=round(avg_accuracy, 2),
                pass_rate=round((passed_runs / total_runs) * 100, 1),
                avg_complexity=round(avg_complexity, 1),
                runs_by_complexity=complexity_dist,
                runs_by_status=status_dist,
            )
        else:
            # No data
            summary = QualityAnalyticsSummary(
                total_runs=0,
                avg_overall_score=0.0,
                avg_substance_score=0.0,
                avg_completeness_score=0.0,
                avg_depth_score=0.0,
                avg_accuracy_score=0.0,
                pass_rate=0.0,
                avg_complexity=0.0,
                runs_by_complexity={},
                runs_by_status={},
            )

        return QualityAnalyticsResponse(
            data=data,
            summary=summary,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        logger.error(f"Error fetching quality analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch quality analytics: {str(e)}"
        )


@router.get("/quality/trends", response_model=Dict[str, Any])
async def get_quality_trends(
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
    thread_id: Optional[str] = Query(None, description="Filter by thread ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    interval: str = Query("day", regex="^(hour|day|week)$", description="Grouping interval"),
):
    """
    Get quality trends over time.

    Returns time-series data showing how quality metrics have changed over the specified period.
    """
    await set_rls_context(db, org_id)

    # TODO: Implement time-series aggregation
    # This would group results by time interval and show trends
    # For now, return a simple response
    return {
        "message": "Quality trends endpoint - to be implemented",
        "interval": interval,
        "days": days,
    }


@router.get("/quality/leaderboard", response_model=List[Dict[str, Any]])
async def get_quality_leaderboard(
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, ge=1, le=365, description="Number of days to consider"),
    limit: int = Query(10, ge=1, le=100, description="Number of top results"),
):
    """
    Get top-performing queries/threads by quality scores.

    Returns the highest-quality collaboration runs in the specified time period.
    """
    await set_rls_context(db, org_id)

    try:
        since_date = datetime.utcnow() - timedelta(days=days)

        query = (
            select(CollaborateRun)
            .where(
                and_(
                    CollaborateRun.started_at >= since_date,
                    CollaborateRun.status == "success",
                    CollaborateRun.overall_quality_score.isnot(None)
                )
            )
            .order_by(desc(CollaborateRun.overall_quality_score))
            .limit(limit)
        )

        result = await db.execute(query)
        runs = result.scalars().all()

        leaderboard = [
            {
                "run_id": run.id,
                "thread_id": run.thread_id,
                "overall_score": run.overall_quality_score,
                "query_complexity": run.query_complexity,
                "quality_gate_passed": run.quality_gate_passed,
                "timestamp": run.started_at.isoformat(),
            }
            for run in runs
        ]

        return leaderboard

    except Exception as e:
        logger.error(f"Error fetching quality leaderboard: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch quality leaderboard: {str(e)}"
        )
