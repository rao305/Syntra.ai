"""
Main Intelligent Router class.
Routes queries to optimal models using fine-tuned GPT-4o-mini.
"""

import json
import time
import hashlib
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import asyncio

import openai

from .config import (
    MODEL_REGISTRY,
    ROUTER_CONFIG,
    RouterConfig,
    generate_router_system_prompt,
    get_model,
    get_available_models,
    get_cheapest_model,
    get_fastest_model,
    UserPriority,
    TaskType,
    ModelCapabilities,
)
from .cost_optimizer import cost_optimizer

logger = logging. getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class RoutingDecision:
    """Result of a routing decision."""
    model: str
    task_type: str
    complexity: int
    confidence: float
    reasoning: str
    needs_web: bool
    estimated_tokens: int
    routing_time_ms: float
    method: str  # "fine_tuned", "rule_based", "fallback"
    model_info: Optional[Dict[str, Any]] = None
    alternatives: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RoutingMetrics:
    """Metrics for a routing decision."""
    timestamp: datetime
    query_hash: str
    decision:  RoutingDecision
    user_priority: str
    context_length: int
    cache_hit: bool


# =============================================================================
# INTELLIGENT ROUTER
# =============================================================================

class IntelligentRouter:
    """
    Routes queries to optimal AI models using fine-tuned classification.
    Extensible design allows easy addition of new models.
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        config: Optional[RouterConfig] = None
    ):
        self.config = config or ROUTER_CONFIG
        self.client = openai.OpenAI(api_key=openai_api_key)
        self.system_prompt = generate_router_system_prompt()

        # Caching
        self._cache:  Dict[str, Tuple[RoutingDecision, float]] = {}

        # Metrics
        self._metrics: List[RoutingMetrics] = []

        logger.info(f"IntelligentRouter initialized with {len(get_available_models())} models")

    # =========================================================================
    # MAIN ROUTING METHOD
    # =========================================================================

    async def route(
        self,
        query: str,
        context: Optional[str] = None,
        user_priority: UserPriority = UserPriority. BALANCED,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        force_model: Optional[str] = None
    ) -> RoutingDecision:
        """
        Route a query to the optimal model.

        Args:
            query: The user's query
            context:  Optional context from previous messages
            user_priority: User's preference (speed/cost/quality/balanced)
            conversation_history: Previous messages for context
            force_model: Force a specific model (bypasses routing)

        Returns:
            RoutingDecision with the selected model and metadata
        """
        start_time = time. time()

        # Force specific model if requested
        if force_model and force_model in MODEL_REGISTRY:
            return self._create_forced_decision(force_model, start_time)

        # Check cache
        cache_key = self._get_cache_key(query, context, user_priority)
        if self. config.enable_routing_cache:
            cached = self._get_from_cache(cache_key)
            if cached:
                cached. routing_time_ms = (time.time() - start_time) * 1000
                self._log_metrics(query, cached, user_priority, context, cache_hit=True)
                return cached

        # Try fine-tuned model routing
        try:
            decision = await self._route_with_fine_tuned_model(
                query, context, user_priority, start_time
            )
        except Exception as e:
            logger.warning(f"Fine-tuned routing failed: {e}, falling back to rules")
            decision = self._route_with_rules(query, context, user_priority, start_time)

        # Apply user priority adjustments
        decision = self._apply_user_priority(decision, user_priority)

        # Add alternatives
        decision.alternatives = self._get_alternative_models(decision)

        # Cache the result
        if self.config.enable_routing_cache:
            self._add_to_cache(cache_key, decision)

        # Log metrics
        self._log_metrics(query, decision, user_priority, context, cache_hit=False)

        return decision

    # =========================================================================
    # FINE-TUNED MODEL ROUTING
    # =========================================================================

    async def _route_with_fine_tuned_model(
        self,
        query: str,
        context:  Optional[str],
        user_priority:  UserPriority,
        start_time: float
    ) -> RoutingDecision:
        """Use the fine-tuned model for routing."""

        # Build the prompt
        user_content = f"Query:  {query}"
        if context:
            user_content += f"\nContext: {context[: 500]}"  # Truncate context
        user_content += f"\nUser Priority: {user_priority.value}"

        # Determine which model to use for routing
        router_model = (
            self.config.fine_tuned_model_id
            if self. config.use_fine_tuned and self.config.fine_tuned_model_id
            else self.config.router_model
        )

        # Call the router model
        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            model=router_model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role":  "user", "content": user_content}
            ],
            max_tokens=150,
            temperature=0,
            response_format={"type": "json_object"}
        )

        # Parse the response
        try:
            result = json.loads(response.choices[0].message.content)
        except json. JSONDecodeError:
            raise ValueError("Router model returned invalid JSON")

        # Validate the model exists
        selected_model = result. get("model", self.config.fallback_model)
        if selected_model not in MODEL_REGISTRY:
            logger.warning(f"Router selected unknown model: {selected_model}")
            selected_model = self. config.fallback_model

        # Get model info
        model_info = get_model(selected_model)

        return RoutingDecision(
            model=selected_model,
            task_type=result.get("task_type", "unknown"),
            complexity=result.get("complexity", 3),
            confidence=result.get("confidence", 0.8),
            reasoning=result.get("reasoning", ""),
            needs_web=result.get("needs_web", False),
            estimated_tokens=result.get("estimated_tokens", 500),
            routing_time_ms=(time.time() - start_time) * 1000,
            method="fine_tuned" if self.config. fine_tuned_model_id else "prompted",
            model_info={
                "display_name": model_info.display_name,
                "provider": model_info. provider,
                "cost_tier": model_info.cost_tier. value,
                "latency_tier": model_info.latency_tier. value,
                "supports_web": model_info.supports_web_search,
            } if model_info else None
        )

    # =========================================================================
    # RULE-BASED FALLBACK ROUTING
    # =========================================================================

    def _route_with_rules(
        self,
        query:  str,
        context: Optional[str],
        user_priority: UserPriority,
        start_time: float
    ) -> RoutingDecision:
        """Fallback rule-based routing when fine-tuned model fails."""

        query_lower = query.lower()

        # Detect task type and select model
        task_type = "simple_qa"
        selected_model = "gpt-4o-mini"
        complexity = 1
        confidence = 0.7
        reasoning = "Rule-based fallback routing"
        needs_web = False

        # Research indicators → Perplexity
        research_keywords = [
            "latest", "recent", "current", "today", "news", "2024", "2025",
            "stock price", "weather", "search", "find", "research", "papers",
            "what happened", "who won", "compare prices"
        ]
        if any(kw in query_lower for kw in research_keywords):
            selected_model = "perplexity-sonar-pro"
            task_type = "research"
            complexity = 3
            needs_web = True
            reasoning = "Query requires current/web information"

        # Coding indicators → GPT-4o or Kimi
        elif any(kw in query_lower for kw in [
            "code", "function", "implement", "debug", "programming",
            "python", "javascript", "java", "c++", "rust", "go", "typescript",
            "ruby", "php", "swift", "kotlin", "scala", "html", "css", "sql",
            "algorithm", "program", "script", "write a", "write an", "create a",
            "build a", "make a", "debug", "refactor", "optimize code"
        ]):
            selected_model = "gpt-4o"
            task_type = "coding"
            complexity = 3
            reasoning = "Query involves coding/programming"

        # Math indicators → GPT-4o or Kimi
        elif any(kw in query_lower for kw in [
            "prove", "proof", "theorem", "calculate", "equation",
            "derivative", "integral", "solve", "math"
        ]):
            selected_model = "gpt-4o"
            task_type = "math"
            complexity = 4
            reasoning = "Query involves mathematical reasoning"

        # Long content indicators → Gemini
        elif any(kw in query_lower for kw in [
            "summarize this document", "analyze this file",
            "read through", "entire", "whole", "full text", "analyze document",
            "process document", "parse file", "codebase analysis", "repository analysis"
        ]) or len(query) > 5000:
            selected_model = "gemini-2.5-flash"
            task_type = "long_context"
            complexity = 3
            reasoning = "Query involves long content processing"

        # Creative writing indicators
        elif any(kw in query_lower for kw in [
            "write", "story", "poem", "essay", "blog", "article", "creative",
            "novel", "narrative", "fiction", "brainstorm", "ideate"
        ]):
            selected_model = "gpt-4o"
            task_type = "creative"
            complexity = 3
            reasoning = "Query involves creative writing"

        # Simple greetings
        elif any(kw in query_lower for kw in [
            "hi", "hello", "hey", "thanks", "thank you",
            "bye", "goodbye", "how are you"
        ]):
            selected_model = "gpt-4o-mini"
            task_type = "conversation"
            complexity = 1
            confidence = 0.95
            reasoning = "Simple conversational query"

        # Apply user priority
        if user_priority == UserPriority. SPEED:
            if selected_model not in ["perplexity-sonar-pro"]:
                selected_model = get_fastest_model()
                reasoning += " (optimized for speed)"
        elif user_priority == UserPriority.COST:
            if selected_model not in ["perplexity-sonar-pro"]:
                selected_model = get_cheapest_model()
                reasoning += " (optimized for cost)"

        model_info = get_model(selected_model)

        return RoutingDecision(
            model=selected_model,
            task_type=task_type,
            complexity=complexity,
            confidence=confidence,
            reasoning=reasoning,
            needs_web=needs_web,
            estimated_tokens=self._estimate_tokens(query),
            routing_time_ms=(time.time() - start_time) * 1000,
            method="rule_based",
            model_info={
                "display_name": model_info.display_name,
                "provider":  model_info.provider,
                "cost_tier": model_info.cost_tier.value,
                "latency_tier": model_info.latency_tier.value,
                "supports_web": model_info.supports_web_search,
            } if model_info else None
        )

    # =========================================================================
    # COST TRACKING INTEGRATION
    # =========================================================================

    def record_model_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        query_type: str,
        was_routed: bool = True,
        could_have_used: Optional[str] = None
    ):
        """
        Record the cost of using a specific model.

        This should be called after the actual API call to track real costs.
        """
        try:
            cost_optimizer.record_cost(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                query_type=query_type,
                was_routed=was_routed,
                could_have_used=could_have_used
            )
        except Exception as e:
            logger.warning(f"Failed to record cost for {model}: {e}")

    def get_cost_efficiency_report(self) -> Dict[str, Any]:
        """Get cost efficiency report from the optimizer."""
        return cost_optimizer.get_cost_efficiency_report()

    def set_budget_limits(self, daily_usd: Optional[float] = None, monthly_usd: Optional[float] = None):
        """Set budget limits for cost control."""
        if daily_usd is not None:
            cost_optimizer.set_daily_budget(daily_usd)
        if monthly_usd is not None:
            cost_optimizer.set_monthly_budget(monthly_usd)

    def is_over_budget(self) -> bool:
        """Check if current spending exceeds budget limits."""
        return cost_optimizer.is_over_budget()

    def estimate_routing_cost(self, decision: RoutingDecision) -> float:
        """Estimate the cost of a routing decision."""
        return cost_optimizer.estimate_cost(
            model=decision.model,
            estimated_input_tokens=decision.estimated_tokens,
            estimated_output_tokens=decision.estimated_tokens  # Rough estimate
        )

    # =========================================================================
    # USER PRIORITY OPTIMIZATION
    # =========================================================================

    def _apply_user_priority(
        self,
        decision: RoutingDecision,
        user_priority: UserPriority
    ) -> RoutingDecision:
        """Apply user priority adjustments to the routing decision."""

        if user_priority == UserPriority.BALANCED or decision.confidence < 0.8:
            # Don't override high-confidence decisions or balanced priority
            return decision

        original_model = decision.model
        selected_model = original_model

        if user_priority == UserPriority.SPEED:
            # Override to fastest available model if confidence is reasonable
            if decision.confidence > 0.6 and original_model != "perplexity-sonar-pro":
                fastest = get_fastest_model()
                if fastest and fastest != original_model:
                    selected_model = fastest
                    decision.reasoning += f" (speed priority: {original_model} → {fastest})"

        elif user_priority == UserPriority.COST:
            # Override to cheapest available model if confidence is reasonable
            if decision.confidence > 0.6 and original_model != "perplexity-sonar-pro":
                cheapest = get_cheapest_model()
                if cheapest and cheapest != original_model:
                    selected_model = cheapest
                    decision.reasoning += f" (cost priority: {original_model} → {cheapest})"

        elif user_priority == UserPriority.QUALITY:
            # Override to highest quality model
            if decision.confidence > 0.6:
                # For quality, prefer GPT-4o or Kimi for complex tasks
                if decision.complexity >= 3 and original_model not in ["gpt-4o", "kimi-k2"]:
                    if "gpt-4o" in get_available_models():
                        selected_model = "gpt-4o"
                        decision.reasoning += f" (quality priority: {original_model} → gpt-4o)"
                    elif "kimi-k2" in get_available_models():
                        selected_model = "kimi-k2"
                        decision.reasoning += f" (quality priority: {original_model} → kimi-k2)"

        # Update model info if changed
        if selected_model != original_model:
            decision.model = selected_model
            model_info = get_model(selected_model)
            if model_info:
                decision.model_info = {
                    "display_name": model_info.display_name,
                    "provider": model_info.provider,
                    "cost_tier": model_info.cost_tier.value,
                    "latency_tier": model_info.latency_tier.value,
                    "supports_web": model_info.supports_web_search,
                }

        return decision

    # =========================================================================
    # ALTERNATIVE MODELS
    # =========================================================================

    def _get_alternative_models(self, decision: RoutingDecision) -> List[Dict[str, Any]]:
        """Get alternative models for fallback."""
        alternatives = []
        current_model = decision.model

        # Get models by priority: cost, speed, quality
        available = get_available_models()

        # Cheapest alternative
        cheapest = get_cheapest_model()
        if cheapest and cheapest != current_model and cheapest in available:
            model_info = get_model(cheapest)
            if model_info:
                alternatives.append({
                    "model": cheapest,
                    "reason": "Lowest cost option",
                    "priority": "cost",
                    "cost_score": model_info.get_cost_score(),
                    "latency_score": model_info.get_latency_score()
                })

        # Fastest alternative
        fastest = get_fastest_model()
        if fastest and fastest != current_model and fastest in available:
            model_info = get_model(fastest)
            if model_info:
                alternatives.append({
                    "model": fastest,
                    "reason": "Fastest response",
                    "priority": "speed",
                    "cost_score": model_info.get_cost_score(),
                    "latency_score": model_info.get_latency_score()
                })

        # Quality alternative (GPT-4o or Kimi)
        quality_models = ["gpt-4o", "kimi-k2"]
        for qm in quality_models:
            if qm != current_model and qm in available:
                model_info = get_model(qm)
                if model_info:
                    alternatives.append({
                        "model": qm,
                        "reason": "Highest quality",
                        "priority": "quality",
                        "cost_score": model_info.get_cost_score(),
                        "latency_score": model_info.get_latency_score()
                    })
                    break  # Just add one quality alternative

        return alternatives[:3]  # Return top 3 alternatives

    # =========================================================================
    # CACHING
    # =========================================================================

    def _get_cache_key(self, query: str, context: Optional[str], user_priority: UserPriority) -> str:
        """Generate cache key for routing decisions."""
        content = f"{query}|{context or ''}|{user_priority.value}"
        return hashlib.md5(content.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[RoutingDecision]:
        """Get cached routing decision if still valid."""
        if cache_key in self._cache:
            decision, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self.config.cache_ttl_seconds:
                return decision
            else:
                # Remove expired cache entry
                del self._cache[cache_key]
        return None

    def _add_to_cache(self, cache_key: str, decision: RoutingDecision):
        """Add routing decision to cache."""
        self._cache[cache_key] = (decision, time.time())

        # Clean up old cache entries if too many
        if len(self._cache) > 1000:
            # Remove oldest 20% of entries
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
            to_remove = len(sorted_items) // 5
            for key, _ in sorted_items[:to_remove]:
                del self._cache[key]

    # =========================================================================
    # METRICS & LOGGING
    # =========================================================================

    def _log_metrics(
        self,
        query: str,
        decision: RoutingDecision,
        user_priority: UserPriority,
        context: Optional[str],
        cache_hit: bool
    ):
        """Log routing metrics."""
        if not self.config.enable_metrics:
            return

        query_hash = hashlib.md5(query.encode()).hexdigest()
        context_length = len(context) if context else 0

        metrics = RoutingMetrics(
            timestamp=datetime.now(),
            query_hash=query_hash,
            decision=decision,
            user_priority=user_priority.value,
            context_length=context_length,
            cache_hit=cache_hit
        )

        self._metrics.append(metrics)

        # Keep only recent metrics
        if len(self._metrics) > 10000:
            self._metrics = self._metrics[-5000:]

        if self.config.log_routing_decisions:
            logger.info(
                f"Router Decision: {decision.model} ({decision.confidence:.2f}) "
                f"[{decision.method}] - {decision.reasoning[:100]}..."
            )

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of routing metrics."""
        if not self._metrics:
            return {"total_decisions": 0}

        total = len(self._metrics)
        cache_hits = sum(1 for m in self._metrics if m.cache_hit)
        avg_confidence = sum(m.decision.confidence for m in self._metrics) / total
        avg_latency = sum(m.decision.routing_time_ms for m in self._metrics) / total

        model_counts = {}
        method_counts = {}
        priority_counts = {}

        for m in self._metrics:
            model_counts[m.decision.model] = model_counts.get(m.decision.model, 0) + 1
            method_counts[m.decision.method] = method_counts.get(m.decision.method, 0) + 1
            priority_counts[m.user_priority] = priority_counts.get(m.user_priority, 0) + 1

        return {
            "total_decisions": total,
            "cache_hit_rate": cache_hits / total,
            "avg_confidence": avg_confidence,
            "avg_routing_latency_ms": avg_latency,
            "model_distribution": model_counts,
            "method_distribution": method_counts,
            "priority_distribution": priority_counts
        }

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def _create_forced_decision(self, model: str, start_time: float) -> RoutingDecision:
        """Create a routing decision for a forced model selection."""
        model_info = get_model(model)

        return RoutingDecision(
            model=model,
            task_type="forced",
            complexity=3,
            confidence=1.0,
            reasoning=f"Model forced by user/system: {model}",
            needs_web=False,
            estimated_tokens=500,
            routing_time_ms=(time.time() - start_time) * 1000,
            method="forced",
            model_info={
                "display_name": model_info.display_name,
                "provider": model_info.provider,
                "cost_tier": model_info.cost_tier.value,
                "latency_tier": model_info.latency_tier.value,
                "supports_web": model_info.supports_web_search,
            } if model_info else None
        )

    def _estimate_tokens(self, query: str) -> int:
        """Roughly estimate token count for a query."""
        # Simple estimation: ~4 characters per token
        return max(50, len(query) // 4)

    # =========================================================================
    # MODEL MANAGEMENT
    # =========================================================================

    def update_fine_tuned_model(self, model_id: str):
        """Update the fine-tuned model ID."""
        self.config.fine_tuned_model_id = model_id
        self.config.use_fine_tuned = True
        logger.info(f"Updated fine-tuned model to: {model_id}")

    def disable_fine_tuned_routing(self):
        """Disable fine-tuned routing, use rule-based fallback."""
        self.config.use_fine_tuned = False
        logger.info("Disabled fine-tuned routing, using rule-based fallback")

    def clear_cache(self):
        """Clear the routing cache."""
        self._cache.clear()
        logger.info("Cleared routing cache")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_entries": len(self._cache),
            "cache_size_limit": 1000,
            "cache_ttl_seconds": self.config.cache_ttl_seconds
        }


# =============================================================================
# USER KEY ROUTER
# =============================================================================

class UserKeyRouter:
    """
    Router that uses user-provided API keys for making API calls.
    """

    def __init__(self, db_session, user_id: str, config: RouterConfig):
        self.db = db_session
        self.user_id = user_id
        self.config = config
        self.api_key_service = None

        # Import here to avoid circular imports
        from app.services.api_key_service import APIKeyService
        self.api_key_service = APIKeyService(self.db, self.user_id)

    async def route_and_call(
        self,
        query: str,
        context: Optional[str] = None,
        user_priority: UserPriority = UserPriority.BALANCED,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        force_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Route query to best available model based on user's API keys and make the API call.
        """
        # Get user's active API keys
        user_keys = await self.api_key_service.get_api_keys(active_only=True)

        if not user_keys:
            raise ValueError(
                "No API keys configured. "
                "Please add at least one API key in Settings → API Keys."
            )

        # Get available providers
        available_providers = {key.provider for key in user_keys}

        # Route based on available providers and query
        routing_decision = await self._decide_best_provider(
            query,
            available_providers,
            user_priority
        )

        # Get the API key for selected provider
        selected_key = await self.api_key_service.get_active_key_for_provider(
            routing_decision['provider']
        )

        if not selected_key:
            # Fallback to any available provider
            selected_key = user_keys[0]

        # Decrypt the API key
        decrypted_key = await self.api_key_service.get_decrypted_key(
            selected_key.id
        )

        # Track usage (tokens will be updated after the call)
        await self.api_key_service.track_usage(
            selected_key.id,
            0,  # tokens used - will be updated after call
            "routing"
        )

        return {
            'provider': selected_key.provider,
            'model': routing_decision['model'],
            'api_key': decrypted_key,
            'user_api_key_id': selected_key.id,
            'reasoning': routing_decision['reasoning']
        }

    async def _decide_best_provider(
        self,
        query: str,
        available_providers: set,
        user_priority: UserPriority
    ) -> Dict[str, Any]:
        """Decide which provider to use based on query and availability."""
        # Simple routing logic - can be enhanced with ML later
        provider_priority = {
            UserPriority.SPEED: ['openai', 'gemini', 'anthropic', 'perplexity', 'kimi'],
            UserPriority.COST: ['openai', 'gemini', 'anthropic', 'kimi', 'perplexity'],
            UserPriority.QUALITY: ['anthropic', 'openai', 'gemini', 'perplexity', 'kimi'],
            UserPriority.BALANCED: ['openai', 'anthropic', 'gemini', 'perplexity', 'kimi']
        }

        for provider in provider_priority[user_priority.value]:
            if provider in available_providers:
                model = self._get_best_model_for_provider(provider, user_priority)
                return {
                    'provider': provider,
                    'model': model,
                    'reasoning': f"Selected {provider} based on {user_priority.value} priority and availability"
                }

        # Fallback to first available
        provider = list(available_providers)[0]
        model = self._get_best_model_for_provider(provider, user_priority)
        return {
            'provider': provider,
            'model': model,
            'reasoning': f"Fallback to {provider} - only available provider"
        }

    def _get_best_model_for_provider(self, provider: str, priority: UserPriority) -> str:
        """Get the best model for a provider based on priority."""
        provider_models = {
            'openai': {
                UserPriority.SPEED: 'gpt-4o-mini',
                UserPriority.COST: 'gpt-4o-mini',
                UserPriority.QUALITY: 'gpt-4o',
                UserPriority.BALANCED: 'gpt-4o-mini'
            },
            'anthropic': {
                UserPriority.SPEED: 'claude-3-haiku-20240307',
                UserPriority.COST: 'claude-3-haiku-20240307',
                UserPriority.QUALITY: 'claude-3-opus-20240229',
                UserPriority.BALANCED: 'claude-3-sonnet-20240229'
            },
            'gemini': {
                UserPriority.SPEED: 'gemini-pro',
                UserPriority.COST: 'gemini-pro',
                UserPriority.QUALITY: 'gemini-pro',
                UserPriority.BALANCED: 'gemini-pro'
            },
            'perplexity': {
                UserPriority.SPEED: 'sonar-small-online',
                UserPriority.COST: 'sonar-small-online',
                UserPriority.QUALITY: 'sonar-large-online',
                UserPriority.BALANCED: 'sonar-medium-online'
            },
            'kimi': {
                UserPriority.SPEED: 'moonshot-v1-8k',
                UserPriority.COST: 'moonshot-v1-8k',
                UserPriority.QUALITY: 'moonshot-v1-32k',
                UserPriority.BALANCED: 'moonshot-v1-8k'
            }
        }

        return provider_models.get(provider, {}).get(priority, 'default-model')


# Add method to base router
def with_user_keys(self, db_session, user_id: str):
    """
    Create a router instance that uses user-provided API keys.
    """
    return UserKeyRouter(db_session, user_id, self.config)

IntelligentRouter.with_user_keys = with_user_keys


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

# Create global router instance
intelligent_router = IntelligentRouter()
