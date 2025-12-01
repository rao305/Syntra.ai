# Dynamic Router Implementation

## Overview

This implementation replaces the hard-coded dictionary-based routing with a dynamic, LLM-powered routing system that scores all 5 models for each query and selects the best one.

## Architecture

### Components

1. **Model Configuration** (`backend/app/services/dynamic_router/models.py`)
   - Defines all 5 models with capabilities, cost, latency, and strengths
   - Centralized configuration for easy tuning

2. **Intent Classification** (`backend/app/services/dynamic_router/intent.py`)
   - Uses GPT-4o-mini as a "router LLM" to classify each query
   - Returns structured `RouterIntent` with task type, priority, and requirements

3. **Dynamic Scoring** (`backend/app/services/dynamic_router/score.py`)
   - Scores each model based on:
     - Capability match (does model have strengths for this task?)
     - Latency (normalized 500ms-4000ms)
     - Cost (normalized $0.0005-$0.005 per 1k tokens)
     - Historical reward (from feedback, defaults to 0.5)
   - Weights adjust based on priority (quality/speed/cost)

4. **Routing Logic** (`backend/app/services/dynamic_router/route_query.py`)
   - Combines intent classification + scoring
   - Returns best model with all candidate scores
   - Supports epsilon-greedy exploration (10% chance to try second-best)

5. **Integration** (`backend/app/services/dynamic_router/integration.py`)
   - Helper functions to get available providers
   - Wrapper for routing with org context

6. **Database Logging** (`backend/app/models/router_run.py`)
   - Logs every routing decision
   - Stores intent, chosen model, scores, performance metrics
   - Supports user feedback (rating, liked) for learning

## Integration

The dynamic router is integrated into `backend/app/api/threads.py` in the `add_message_streaming` endpoint:

1. **Routing Phase**: Calls `route_with_dynamic_router()` to get the best model
2. **Fallback**: Falls back to legacy `analyze_content()` if dynamic router fails
3. **Logging**: Logs router decision to `RouterRun` table after response completes

## Database Migration

Run the migration to create the `router_runs` table:

```bash
cd backend
alembic upgrade head
```

Or manually:

```bash
alembic upgrade 008
```

## Model Configuration

Models are defined in `backend/app/services/dynamic_router/models.py`:

- **Perplexity Sonar**: Web search, summarization, multi-doc RAG
- **GPT-4o Mini**: Reasoning, coding, math, creative writing
- **Gemini 2.5 Flash**: Fast reasoning, summarization, coding
- **Gemini 2.5 Pro**: Long context (1M tokens), document analysis
- **Kimi K2 Turbo**: Web search, creative writing, long context
- **OpenRouter**: Cost-effective fallback

## Scoring Logic

For each query:
1. Router LLM classifies task type and priority
2. All models are scored on:
   - **Capability** (40-60% weight): Does model have required strengths?
   - **Latency** (20-50% weight): How fast is the model?
   - **Cost** (20-50% weight): How expensive is the model?
   - **Historical** (30% of quality component): How well did this model perform on similar tasks?

3. Weights adjust based on priority:
   - **Quality**: 60% capability, 20% speed, 20% cost
   - **Speed**: 30% capability, 50% speed, 20% cost
   - **Cost**: 30% capability, 20% speed, 50% cost

## Feedback Loop (Future)

To enable learning from user feedback:

1. Add UI buttons for thumbs up/down or 1-5 rating
2. Create endpoint `POST /api/router-feedback` that updates `RouterRun.user_rating` or `RouterRun.user_liked`
3. Update `get_historical_rewards()` in `integration.py` to query average rewards per (model, task_type)
4. Historical rewards will automatically improve routing over time

## Example Usage

```python
from app.services.dynamic_router.integration import route_with_dynamic_router

decision = await route_with_dynamic_router(
    user_message="Write a Python function to sort a list",
    context_summary="Previous conversation: 3 turns",
    db=db,
    org_id=org_id,
)

# decision.chosen_model contains the best model
# decision.intent contains task classification
# decision.scores contains all candidate scores
```

## Benefits

1. **Dynamic**: Routes based on actual query content, not just keywords
2. **Adaptive**: Can learn from feedback over time
3. **Transparent**: Logs all decisions for analytics
4. **Flexible**: Easy to add new models or adjust weights
5. **Fallback**: Gracefully falls back to legacy router if needed

## Next Steps

1. Run migration to create `router_runs` table
2. Test with various query types
3. Monitor router decisions in database
4. Add feedback UI to collect user ratings
5. Implement historical reward calculation from feedback





