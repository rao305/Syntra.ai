# Dynamic Router Test Plan

This document maps the test cases to the actual test files.

## Test Coverage Matrix

| Test # | Description | Test File | Status |
|--------|-------------|-----------|--------|
| 1 | Simple chat | `test_dynamic_router_intent.py::test_simple_chat` | ✅ |
| 2 | Deep strategy | `test_dynamic_router_intent.py::test_deep_strategy` | ✅ |
| 3 | Code generation | `test_dynamic_router_intent.py::test_code_generation` | ✅ |
| 4 | Debugging with code | `test_dynamic_router_intent.py::test_debugging_with_code` | ✅ |
| 5 | Pure math | `test_dynamic_router_intent.py::test_pure_math` | ✅ |
| 6 | Casual numeric | `test_dynamic_router_intent.py::test_casual_numeric_question` | ✅ |
| 7 | Summarization | `test_dynamic_router_intent.py::test_summarization` | ✅ |
| 8 | Document analysis | `test_dynamic_router_intent.py::test_document_analysis` | ✅ |
| 9 | Creative writing | `test_dynamic_router_intent.py::test_creative_writing` | ✅ |
| 10 | Web research news | `test_dynamic_router_intent.py::test_web_research_news` | ✅ |
| 11 | Web research papers | `test_dynamic_router_intent.py::test_web_research_papers` | ✅ |
| 12 | Search in algorithm | `test_dynamic_router_intent.py::test_search_in_algorithm_not_web` | ✅ |
| 13 | Today but timeless | `test_dynamic_router_intent.py::test_today_but_timeless` | ✅ |
| 14 | Speed priority | `test_dynamic_router_intent.py::test_speed_priority` | ✅ |
| 15 | Cost priority | `test_dynamic_router_intent.py::test_cost_priority` | ✅ |
| 16 | Quality priority | `test_dynamic_router_intent.py::test_quality_priority_important_decision` | ✅ |
| 17 | Massive input | `test_dynamic_router_intent.py::test_massive_input` | ✅ |
| 18 | Tiny input | `test_dynamic_router_intent.py::test_tiny_input` | ✅ |
| 5.1 | Non-JSON fallback | `test_dynamic_router_intent.py::test_non_json_response_fallback` | ✅ |
| 5.2 | Invalid taskType | `test_dynamic_router_intent.py::test_invalid_task_type_fallback` | ✅ |
| 5.3 | Missing tokens | `test_dynamic_router_intent.py::test_missing_estimated_tokens` | ✅ |
| 5.4 | No candidates | `test_dynamic_router_integration.py::test_fallback_when_no_candidates` | ✅ |
| 6.1 | Mixed intent | `test_dynamic_router_scoring.py::test_mixed_intent_coding_and_web` | ✅ |
| 7.1 | Non-English | `test_dynamic_router_intent.py::test_non_english` | ✅ |
| 7.2 | Emoji/slang | `test_dynamic_router_intent.py::test_emoji_slang` | ✅ |
| 7.3 | Empty message | `test_dynamic_router_intent.py::test_empty_message` | ✅ |
| 19-20 | Epsilon exploration | `test_dynamic_router_integration.py::test_epsilon_exploration` | ✅ |

## Scoring Tests

| Test | Description | Test File | Status |
|------|-------------|-----------|--------|
| Coding → GPT | Coding tasks route to GPT | `test_dynamic_router_scoring.py::test_coding_task_gpt_wins` | ✅ |
| Web → Perplexity | Web research routes to Perplexity | `test_dynamic_router_scoring.py::test_web_research_perplexity_wins` | ✅ |
| Creative → GPT/OpenRouter | Creative writing routes appropriately | `test_dynamic_router_scoring.py::test_creative_writing_gpt_or_openrouter_wins` | ✅ |
| Math → GPT | Math tasks route to GPT | `test_dynamic_router_scoring.py::test_math_task_gpt_wins` | ✅ |
| Speed priority | Fast models win with speed priority | `test_dynamic_router_scoring.py::test_speed_priority_favors_fast_models` | ✅ |
| Cost priority | Cheap models win with cost priority | `test_dynamic_router_scoring.py::test_cost_priority_favors_cheap_models` | ✅ |
| Quality priority | Capable models win with quality priority | `test_dynamic_router_scoring.py::test_quality_priority_favors_capable_models` | ✅ |
| Context filtering | Models filtered by context limits | `test_dynamic_router_scoring.py::test_context_filtering` | ✅ |

## Integration Tests

| Test | Description | Test File | Status |
|------|-------------|-----------|--------|
| Coding E2E | Coding queries route to GPT end-to-end | `test_dynamic_router_integration.py::test_coding_query_routes_to_gpt` | ✅ |
| Web E2E | Web research routes to web model | `test_dynamic_router_integration.py::test_web_research_routes_to_web_model` | ✅ |
| Creative E2E | Creative writing routes appropriately | `test_dynamic_router_integration.py::test_creative_writing_routes_appropriately` | ✅ |
| Scores included | Decision includes all candidate scores | `test_dynamic_router_integration.py::test_scores_included_in_decision` | ✅ |
| Provider filtering | Only available providers considered | `test_dynamic_router_integration.py::test_available_providers_filtering` | ✅ |
| Historical rewards | Historical rewards affect selection | `test_dynamic_router_integration.py::test_historical_rewards_affect_scoring` | ✅ |

## Running Specific Test Categories

```bash
# Intent classification tests
pytest tests/test_dynamic_router_intent.py -v

# Scoring logic tests
pytest tests/test_dynamic_router_scoring.py -v

# Integration tests
pytest tests/test_dynamic_router_integration.py -v

# Run a specific test
pytest tests/test_dynamic_router_intent.py::TestRouterIntentClassification::test_simple_chat -v

# Run with markers (if you add them)
pytest tests/test_dynamic_router*.py -m "not slow" -v
```

## Expected Behaviors

### Intent Classification
- Simple greetings → `generic_chat`, `speed` priority
- Complex reasoning → `deep_reasoning`, `quality` priority
- Code requests → `coding`, `quality` priority
- Math problems → `math`, `quality` priority
- Web queries → `web_research`, `requiresWeb=true`
- Creative writing → `creative_writing`, `quality` priority

### Model Selection
- Coding → GPT (has `coding` strength)
- Web research → Perplexity/Kimi (has `web_search` strength)
- Creative writing → GPT/OpenRouter (has `creative_writing` strength)
- Math → GPT (has `math` + `reasoning` strengths)
- Speed priority → Fast models (low `avgLatencyMs`)
- Cost priority → Cheap models (low `cost_per_1k_tokens`)

### Robustness
- Invalid JSON → Falls back to defaults
- Missing fields → Recomputes from message length
- No candidates → Falls back to first available model
- Empty input → Handles gracefully





