"""
Cost optimization and tracking for the intelligent router.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

from .config import MODEL_REGISTRY, get_model, CostTier

logger = logging.getLogger(__name__)


@dataclass
class CostRecord:
    """Record of a single API call cost."""
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    query_type: str
    was_routed: bool  # True if router selected this model
    could_have_used: Optional[str] = None  # Cheaper alternative that could have worked


@dataclass
class CostSummary:
    """Summary of costs over a period."""
    period_start: datetime
    period_end: datetime
    total_cost_usd: float
    total_requests: int
    cost_by_model: Dict[str, float]
    tokens_by_model: Dict[str, int]
    estimated_savings_usd: float  # Savings from intelligent routing
    avg_cost_per_request: float


class CostOptimizer:
    """
    Tracks and optimizes API costs across all models.
    """

    def __init__(self):
        self._records: List[CostRecord] = []
        self._daily_budget_usd: Optional[float] = None
        self._monthly_budget_usd: Optional[float] = None
        self._alerts_sent: Dict[str, datetime] = {}

    # =========================================================================
    # COST CALCULATION
    # =========================================================================

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate the cost of an API call."""
        model_info = get_model(model)
        if not model_info:
            logger.warning(f"Unknown model for cost calculation: {model}")
            return 0.0

        input_cost = (input_tokens / 1000) * model_info.cost_per_1k_input
        output_cost = (output_tokens / 1000) * model_info.cost_per_1k_output

        return input_cost + output_cost

    def estimate_cost(
        self,
        model: str,
        estimated_input_tokens: int,
        estimated_output_tokens: int = 500
    ) -> float:
        """Estimate cost before making a call."""
        return self.calculate_cost(model, estimated_input_tokens, estimated_output_tokens)

    def compare_model_costs(
        self,
        input_tokens: int,
        output_tokens: int = 500
    ) -> Dict[str, float]:
        """Compare costs across all available models."""
        costs = {}
        for model_id in MODEL_REGISTRY:
            costs[model_id] = self.calculate_cost(model_id, input_tokens, output_tokens)
        return dict(sorted(costs.items(), key=lambda x: x[1]))

    # =========================================================================
    # COST TRACKING
    # =========================================================================

    def record_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        query_type: str,
        was_routed: bool = True,
        could_have_used: Optional[str] = None
    ) -> CostRecord:
        """Record an API call cost."""
        cost = self.calculate_cost(model, input_tokens, output_tokens)

        record = CostRecord(
            timestamp=datetime.now(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            query_type=query_type,
            was_routed=was_routed,
            could_have_used=could_have_used
        )

        self._records.append(record)

        # Check budgets
        self._check_budget_alerts()

        return record

    def get_summary(
        self,
        hours: int = 24
    ) -> CostSummary:
        """Get cost summary for the last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_records = [r for r in self._records if r.timestamp > cutoff]

        if not recent_records:
            return CostSummary(
                period_start=cutoff,
                period_end=datetime.now(),
                total_cost_usd=0.0,
                total_requests=0,
                cost_by_model={},
                tokens_by_model={},
                estimated_savings_usd=0.0,
                avg_cost_per_request=0.0
            )

        # Aggregate by model
        cost_by_model: Dict[str, float] = {}
        tokens_by_model: Dict[str, int] = {}
        total_cost = 0.0
        estimated_savings = 0.0

        for record in recent_records:
            cost_by_model[record.model] = cost_by_model.get(record.model, 0) + record.cost_usd
            tokens_by_model[record.model] = tokens_by_model.get(record.model, 0) + record.input_tokens + record.output_tokens
            total_cost += record.cost_usd

            # Calculate savings (what it would have cost with GPT-4o)
            if record.model != "gpt-4o" and record.was_routed:
                gpt4o_cost = self.calculate_cost("gpt-4o", record.input_tokens, record.output_tokens)
                estimated_savings += (gpt4o_cost - record.cost_usd)

        return CostSummary(
            period_start=cutoff,
            period_end=datetime.now(),
            total_cost_usd=total_cost,
            total_requests=len(recent_records),
            cost_by_model=cost_by_model,
            tokens_by_model=tokens_by_model,
            estimated_savings_usd=max(0, estimated_savings),
            avg_cost_per_request=total_cost / len(recent_records) if recent_records else 0
        )

    # =========================================================================
    # BUDGET MANAGEMENT
    # =========================================================================

    def set_daily_budget(self, budget_usd: float):
        """Set a daily spending limit."""
        self._daily_budget_usd = budget_usd
        logger.info(f"Daily budget set to ${budget_usd:.2f}")

    def set_monthly_budget(self, budget_usd: float):
        """Set a monthly spending limit."""
        self._monthly_budget_usd = budget_usd
        logger.info(f"Monthly budget set to ${budget_usd:.2f}")

    def get_daily_spend(self) -> float:
        """Get total spend for today."""
        today = datetime.now().date()
        return sum(
            r.cost_usd for r in self._records
            if r.timestamp.date() == today
        )

    def get_monthly_spend(self) -> float:
        """Get total spend for this month."""
        now = datetime.now()
        return sum(
            r.cost_usd for r in self._records
            if r.timestamp.year == now.year and r.timestamp.month == now.month
        )

    def get_budget_status(self) -> Dict[str, any]:
        """Get current budget status."""
        daily_spend = self.get_daily_spend()
        monthly_spend = self.get_monthly_spend()

        return {
            "daily": {
                "spent": daily_spend,
                "budget": self._daily_budget_usd,
                "remaining": (self._daily_budget_usd - daily_spend) if self._daily_budget_usd else None,
                "percentage": (daily_spend / self._daily_budget_usd * 100) if self._daily_budget_usd else None
            },
            "monthly": {
                "spent": monthly_spend,
                "budget": self._monthly_budget_usd,
                "remaining": (self._monthly_budget_usd - monthly_spend) if self._monthly_budget_usd else None,
                "percentage": (monthly_spend / self._monthly_budget_usd * 100) if self._monthly_budget_usd else None
            }
        }

    def is_over_budget(self) -> bool:
        """Check if spending exceeds any budget."""
        if self._daily_budget_usd and self.get_daily_spend() >= self._daily_budget_usd:
            return True
        if self._monthly_budget_usd and self.get_monthly_spend() >= self._monthly_budget_usd:
            return True
        return False

    def _check_budget_alerts(self):
        """Check and send budget alerts."""
        if self._daily_budget_usd:
            daily_spend = self.get_daily_spend()
            percentage = daily_spend / self._daily_budget_usd * 100

            if percentage >= 90 and "daily_90" not in self._alerts_sent:
                logger.warning(f"⚠️ Daily budget 90% used: ${daily_spend:.2f} / ${self._daily_budget_usd:.2f}")
                self._alerts_sent["daily_90"] = datetime.now()

            if percentage >= 100 and "daily_100" not in self._alerts_sent:
                logger.error(f"🚨 Daily budget exceeded: ${daily_spend:.2f} / ${self._daily_budget_usd:.2f}")
                self._alerts_sent["daily_100"] = datetime.now()

    # =========================================================================
    # COST-AWARE ROUTING SUGGESTIONS
    # =========================================================================

    def suggest_cheaper_model(
        self,
        current_model: str,
        task_type: str,
        complexity: int
    ) -> Optional[str]:
        """Suggest a cheaper model if appropriate."""
        current_info = get_model(current_model)
        if not current_info or current_info.cost_tier == CostTier.LOW:
            return None  # Already cheap

        # For simple tasks, suggest cheaper models
        if complexity <= 2:
            if task_type in ["simple_qa", "conversation", "translation"]:
                return "gpt-4o-mini"
            if task_type == "summarization":
                return "gemini-2.5-flash"

        return None

    def get_cost_efficiency_report(self) -> Dict[str, any]:
        """Generate a cost efficiency report."""
        summary = self.get_summary(hours=24)

        # Calculate efficiency metrics
        if summary.total_requests == 0:
            return {"message": "No requests in the last 24 hours"}

        # Model usage distribution
        model_usage = {
            model: (cost / summary.total_cost_usd * 100) if summary.total_cost_usd > 0 else 0
            for model, cost in summary.cost_by_model.items()
        }

        # Identify optimization opportunities
        opportunities = []

        # Check if expensive models are overused
        gpt4o_percentage = model_usage.get("gpt-4o", 0)
        if gpt4o_percentage > 50:
            opportunities.append({
                "type": "reduce_gpt4o_usage",
                "message": f"GPT-4o accounts for {gpt4o_percentage:.1f}% of costs. Consider if some queries could use cheaper models.",
                "potential_savings": summary.total_cost_usd * 0.3  # Rough estimate
            })

        return {
            "period": "last_24_hours",
            "total_cost": summary.total_cost_usd,
            "total_requests": summary.total_requests,
            "avg_cost_per_request": summary.avg_cost_per_request,
            "estimated_savings_from_routing": summary.estimated_savings_usd,
            "model_cost_distribution": model_usage,
            "optimization_opportunities": opportunities,
            "budget_status": self.get_budget_status()
        }


# =============================================================================
# COST-AWARE ROUTING WRAPPER
# =============================================================================

class CostAwareRouter:
    """
    Wrapper that adds cost awareness to routing decisions.
    """

    def __init__(self, router, cost_optimizer: CostOptimizer):
        self.router = router
        self.cost_optimizer = cost_optimizer

    async def route(
        self,
        query: str,
        context: Optional[str] = None,
        user_priority: str = "balanced",
        max_cost_usd: Optional[float] = None,
        **kwargs
    ):
        """
        Route with cost constraints.

        Args:
            max_cost_usd: Maximum acceptable cost for this request
        """
        # Check if over budget
        if self.cost_optimizer.is_over_budget():
            logger.warning("Over budget - forcing cheapest model")
            from .config import get_cheapest_model
            return await self.router.route(
                query, context,
                user_priority="cost",
                force_model=get_cheapest_model(),
                **kwargs
            )

        # Get routing decision
        decision = await self.router.route(query, context, user_priority, **kwargs)

        # Check if estimated cost exceeds max
        if max_cost_usd:
            estimated_cost = self.cost_optimizer.estimate_cost(
                decision.model,
                decision.estimated_tokens,
                decision.estimated_tokens  # Rough output estimate
            )

            if estimated_cost > max_cost_usd:
                # Find a cheaper alternative
                cheaper = self.cost_optimizer.suggest_cheaper_model(
                    decision.model,
                    decision.task_type,
                    decision.complexity
                )
                if cheaper:
                    logger.info(f"Cost constraint: switching from {decision.model} to {cheaper}")
                    decision.model = cheaper
                    decision.reasoning += f" (downgraded for cost: max ${max_cost_usd})"

        return decision


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

cost_optimizer = CostOptimizer()
