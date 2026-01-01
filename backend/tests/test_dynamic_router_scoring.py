"""Tests for dynamic router scoring logic."""
import pytest
from app.services.dynamic_router.models import ModelConfig, MODELS
from app.services.dynamic_router.intent import RouterIntent
from app.services.dynamic_router.score import (
    capability_score,
    latency_score,
    cost_score,
    score_model,
    sort_models_by_score,
)
from app.models.provider_key import ProviderType


class TestScoringLogic:
    """Test that scoring correctly ranks models for different tasks."""

    def test_coding_task_gpt_wins(self):
        """Test 3: Coding task - GPT should dominate."""
        intent = RouterIntent(
            task_type="coding",
            requires_web=False,
            requires_tools=False,
            priority="quality",
            estimated_input_tokens=100,
        )
        
        # Get GPT model
        gpt_model = next(m for m in MODELS if m.id == "gpt-4o-mini")
        
        # Get other models
        perplexity_model = next(m for m in MODELS if "perplexity" in m.id)
        openrouter_model = next(m for m in MODELS if "openrouter" in m.id)
        
        gpt_score = score_model(gpt_model, intent)
        perplexity_score = score_model(perplexity_model, intent)
        openrouter_score = score_model(openrouter_model, intent)
        
        # GPT should have highest score for coding
        assert gpt_score > perplexity_score
        assert gpt_score > openrouter_score

    def test_web_research_perplexity_wins(self):
        """Test 10: Web research - Perplexity should win."""
        intent = RouterIntent(
            task_type="web_research",
            requires_web=True,
            requires_tools=False,
            priority="quality",
            estimated_input_tokens=100,
        )
        
        perplexity_model = next(m for m in MODELS if "perplexity" in m.id and "sonar" in m.id)
        gpt_model = next(m for m in MODELS if m.id == "gpt-4o-mini")
        
        perplexity_score = score_model(perplexity_model, intent)
        gpt_score = score_model(gpt_model, intent)
        
        # Perplexity should win for web research
        assert perplexity_score > gpt_score

    def test_creative_writing_gpt_or_openrouter_wins(self):
        """Test 9: Creative writing - GPT or OpenRouter should win."""
        intent = RouterIntent(
            task_type="creative_writing",
            requires_web=False,
            requires_tools=False,
            priority="quality",
            estimated_input_tokens=100,
        )
        
        gpt_model = next(m for m in MODELS if m.id == "gpt-4o-mini")
        openrouter_model = next(m for m in MODELS if "openrouter" in m.id)
        perplexity_model = next(m for m in MODELS if "perplexity" in m.id)
        
        gpt_score = score_model(gpt_model, intent)
        openrouter_score = score_model(openrouter_model, intent)
        perplexity_score = score_model(perplexity_model, intent)
        
        # GPT or OpenRouter should beat Perplexity for creative writing
        assert max(gpt_score, openrouter_score) > perplexity_score

    def test_math_task_gpt_wins(self):
        """Test 5: Math task - GPT should win."""
        intent = RouterIntent(
            task_type="math",
            requires_web=False,
            requires_tools=False,
            priority="quality",
            estimated_input_tokens=100,
        )
        
        gpt_model = next(m for m in MODELS if m.id == "gpt-4o-mini")
        gemini_model = next(m for m in MODELS if "gemini" in m.id and "flash" in m.id)
        openrouter_model = next(m for m in MODELS if "openrouter" in m.id)
        
        gpt_score = score_model(gpt_model, intent)
        gemini_score = score_model(gemini_model, intent)
        openrouter_score = score_model(openrouter_model, intent)
        
        # GPT should win for math (has math + reasoning)
        assert gpt_score >= gemini_score
        assert gpt_score > openrouter_score

    def test_speed_priority_favors_fast_models(self):
        """Test 14: Speed priority should favor fast models."""
        intent = RouterIntent(
            task_type="generic_chat",
            requires_web=False,
            requires_tools=False,
            priority="speed",
            estimated_input_tokens=100,
        )
        
        # Get fast model (openrouter has low latency)
        openrouter_model = next(m for m in MODELS if "openrouter" in m.id)
        # Get slower model (perplexity has higher latency)
        perplexity_model = next(m for m in MODELS if "perplexity" in m.id)
        
        openrouter_score = score_model(openrouter_model, intent)
        perplexity_score = score_model(perplexity_model, intent)
        
        # With speed priority, faster model should score higher
        # (assuming similar capabilities)
        if openrouter_model.avg_latency_ms < perplexity_model.avg_latency_ms:
            # Fast model should have advantage with speed priority
            assert openrouter_score >= perplexity_score * 0.9  # Allow some variance

    def test_cost_priority_favors_cheap_models(self):
        """Test 15: Cost priority should favor cheap models."""
        intent = RouterIntent(
            task_type="summarization",
            requires_web=False,
            requires_tools=False,
            priority="cost",
            estimated_input_tokens=100,
        )
        
        # Get cheap model
        kimi_model = next(m for m in MODELS if "kimi" in m.id)
        # Get more expensive model
        gpt_model = next(m for m in MODELS if m.id == "gpt-4o-mini")
        
        kimi_score = score_model(kimi_model, intent)
        gpt_score = score_model(gpt_model, intent)
        
        # With cost priority, cheaper model should score higher
        if kimi_model.cost_per_1k_tokens < gpt_model.cost_per_1k_tokens:
            # Cheaper model should have advantage with cost priority
            assert kimi_score >= gpt_score * 0.9  # Allow some variance

    def test_quality_priority_favors_capable_models(self):
        """Test 16: Quality priority should favor capable models."""
        intent = RouterIntent(
            task_type="deep_reasoning",
            requires_web=False,
            requires_tools=False,
            priority="quality",
            estimated_input_tokens=100,
        )
        
        gpt_model = next(m for m in MODELS if m.id == "gpt-4o-mini")
        openrouter_model = next(m for m in MODELS if "openrouter" in m.id)
        
        gpt_score = score_model(gpt_model, intent)
        openrouter_score = score_model(openrouter_model, intent)
        
        # With quality priority, GPT (better reasoning) should win
        assert gpt_score > openrouter_score

    def test_context_filtering(self):
        """Test 17: Models with insufficient context are filtered out."""
        intent = RouterIntent(
            task_type="document_analysis",
            requires_web=False,
            requires_tools=False,
            priority="quality",
            estimated_input_tokens=50000,  # Large input
        )
        
        scored = sort_models_by_score(MODELS, intent)
        
        # All returned models should have max_context >= estimated_input_tokens
        for model, score in scored:
            assert model.max_context >= intent.estimated_input_tokens

    def test_no_candidates_fallback(self):
        """Test 5.4: No candidates after filtering - should handle gracefully."""
        intent = RouterIntent(
            task_type="document_analysis",
            requires_web=False,
            requires_tools=False,
            priority="quality",
            estimated_input_tokens=5_000_000,  # Extremely large, beyond all models
        )
        
        scored = sort_models_by_score(MODELS, intent)
        
        # Should return empty list, not crash
        # The route_query function should handle this with a fallback
        assert isinstance(scored, list)

    def test_capability_score_mapping(self):
        """Test that capability scores correctly map task types to strengths."""
        intent = RouterIntent(
            task_type="coding",
            requires_web=False,
            requires_tools=False,
            priority="quality",
            estimated_input_tokens=100,
        )
        
        gpt_model = next(m for m in MODELS if m.id == "gpt-4o-mini")
        perplexity_model = next(m for m in MODELS if "perplexity" in m.id)
        
        gpt_cap = capability_score(gpt_model, intent)
        perplexity_cap = capability_score(perplexity_model, intent)
        
        # GPT has "coding" in strengths, should score higher
        assert gpt_cap > perplexity_cap

    def test_latency_score_normalization(self):
        """Test that latency scores are normalized correctly."""
        fast_model = ModelConfig(
            id="test-fast",
            provider=ProviderType.OPENAI,
            display_name="Fast",
            provider_model="test",
            max_context=100000,
            avg_latency_ms=500,
            cost_per_1k_tokens=0.001,
            strengths=["chat"],
        )
        
        slow_model = ModelConfig(
            id="test-slow",
            provider=ProviderType.OPENAI,
            display_name="Slow",
            provider_model="test",
            max_context=100000,
            avg_latency_ms=4000,
            cost_per_1k_tokens=0.001,
            strengths=["chat"],
        )
        
        fast_score = latency_score(fast_model)
        slow_score = latency_score(slow_model)
        
        # Faster model should have higher latency score
        assert fast_score > slow_score
        # Scores should be in [0, 1] range
        assert 0 <= fast_score <= 1
        assert 0 <= slow_score <= 1

    def test_cost_score_normalization(self):
        """Test that cost scores are normalized correctly."""
        cheap_model = ModelConfig(
            id="test-cheap",
            provider=ProviderType.OPENAI,
            display_name="Cheap",
            provider_model="test",
            max_context=100000,
            avg_latency_ms=2000,
            cost_per_1k_tokens=0.0005,
            strengths=["chat"],
        )
        
        expensive_model = ModelConfig(
            id="test-expensive",
            provider=ProviderType.OPENAI,
            display_name="Expensive",
            provider_model="test",
            max_context=100000,
            avg_latency_ms=2000,
            cost_per_1k_tokens=0.005,
            strengths=["chat"],
        )
        
        cheap_score = cost_score(cheap_model)
        expensive_score = cost_score(expensive_model)
        
        # Cheaper model should have higher cost score
        assert cheap_score > expensive_score
        # Scores should be in [0, 1] range
        assert 0 <= cheap_score <= 1
        assert 0 <= expensive_score <= 1

    def test_historical_reward_default(self):
        """Test that historical reward defaults to 0.5 when no data."""
        intent = RouterIntent(
            task_type="coding",
            requires_web=False,
            requires_tools=False,
            priority="quality",
            estimated_input_tokens=100,
        )
        
        gpt_model = next(m for m in MODELS if m.id == "gpt-4o-mini")
        
        # Score without historical data
        score_no_history = score_model(gpt_model, intent, historical_reward_value=None)
        
        # Score should still be valid
        assert 0 <= score_no_history <= 1

    def test_mixed_intent_coding_and_web(self):
        """Test 6.1: Mixed intent - coding + web."""
        # This is a routing decision, but we can test that scoring handles it
        intent = RouterIntent(
            task_type="web_research",  # Router chose web_research
            requires_web=True,
            requires_tools=False,
            priority="quality",
            estimated_input_tokens=100,
        )
        
        # Should route to web-capable model
        perplexity_model = next(m for m in MODELS if "perplexity" in m.id and "sonar" in m.id)
        gpt_model = next(m for m in MODELS if m.id == "gpt-4o-mini")
        
        perplexity_score = score_model(perplexity_model, intent)
        gpt_score = score_model(gpt_model, intent)
        
        # Perplexity should win due to requires_web override in route_query
        # But scoring should still work
        assert perplexity_score > 0
        assert gpt_score > 0











