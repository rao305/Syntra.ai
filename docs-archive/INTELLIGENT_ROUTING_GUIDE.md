---
title: Intelligent LLM Routing & Collaborative Memory System
summary: Documentation file
last_updated: '2025-11-12'
owner: DAC
tags:
- dac
- docs
---

# Intelligent LLM Routing & Collaborative Memory System

## Overview

This system implements intelligent LLM routing with cross-model context sharing, inspired by the **Collaborative Memory** research paper. The key innovation is that **memory is model-agnostic** - insights from one model can be used by any other model, creating a shared knowledge layer across all LLMs.

### Key Features

1. **Intelligent Query Classification** - Automatically determines the best LLM for each query
2. **Smart Routing** - Routes queries to optimal providers based on query type, complexity, and capabilities
3. **Cross-Model Memory** - Memory fragments created by one model can be read by any other model
4. **Two-Tier Memory System**:
   - **PRIVATE** - User-specific memories, not shared
   - **SHARED** - Organization-wide memories (after PII scrubbing)

## How It Works

### The Problem

Previously, when a user sent queries to different models:
- Query 1 → Perplexity
- Query 2 → OpenAI
- Query 3 → Perplexity

Each model only saw the raw message history. **Models didn't share learned context or insights.**

### The Solution

Now, with Collaborative Memory:

1. **Query 1 → Perplexity**
   - Perplexity answers and extracts key insights
   - Insights saved as memory fragments (with provenance: "created by Perplexity")

2. **Query 2 → OpenAI**
   - OpenAI retrieves ALL relevant memory fragments (including those from Perplexity!)
   - OpenAI sees context from previous interaction
   - OpenAI answers and saves its own insights

3. **Query 3 → Perplexity**
   - Perplexity retrieves memory fragments from BOTH previous interactions
   - Perplexity benefits from OpenAI's insights
   - Full cross-model context sharing achieved

## Architecture

### Services

1. **Query Classifier** (`app/services/query_classifier.py`)
   - Analyzes query content
   - Classifies by type: factual, reasoning, code, creative, etc.
   - Assesses complexity: low, medium, high
   - Returns recommended provider and model

2. **Intelligent Router** (`app/services/intelligent_router.py`)
   - Uses query classifier
   - Checks available providers for org
   - Makes routing decision
   - Tracks performance metrics

3. **Memory Service** (`app/services/memory_service.py`)
   - **READ**: Retrieves relevant memory fragments (from any model)
   - **WRITE**: Extracts and saves insights from responses
   - Uses Qdrant for vector search
   - Implements two-tier memory (PRIVATE/SHARED)

### Routing Logic

#### Query Type → Provider Mapping

- **Factual queries** (news, definitions, current events)
  → Perplexity (has web search & citations)

- **Reasoning queries** (complex logic, chain-of-thought)
  → OpenAI GPT-4o or Perplexity Sonar Reasoning

- **Code queries** (programming, debugging)
  → OpenAI GPT-4o or GPT-4o-mini

- **Creative queries** (writing, brainstorming)
  → OpenAI GPT-4o or Gemini Pro

- **Multilingual queries** (non-English)
  → Kimi (Chinese) or Gemini (general multilingual)

- **Simple queries** (quick Q&A)
  → Gemini Flash (fast & cheap) or GPT-4o-mini

- **Analysis queries** (data analysis, comparison)
  → OpenAI GPT-4o or Gemini Pro

## API Usage

### Automatic Routing (Recommended)

Let the system choose the best model:

```json
POST /api/threads/{thread_id}/messages
{
  "content": "What are the latest developments in quantum computing?",
  "use_memory": true
}
```

The system will:
1. Classify this as a **factual** query
2. Route to **Perplexity** (best for factual queries)
3. Retrieve relevant memory fragments
4. Generate response with full context
5. Save insights for future queries

### Manual Override

You can still specify provider/model:

```json
POST /api/threads/{thread_id}/messages
{
  "content": "What are the latest developments in quantum computing?",
  "provider": "openai",
  "model": "gpt-4o",
  "use_memory": true
}
```

### Disable Memory

To disable memory-based context:

```json
POST /api/threads/{thread_id}/messages
{
  "content": "Your query here",
  "use_memory": false
}
```

## Memory Tiers

### PRIVATE Memory
- User-specific
- Not shared with other users
- Contains personalized Q&A pairs
- Example: "User asked about their project deadline"

### SHARED Memory
- Organization-wide
- PII scrubbed (in production)
- Contains general knowledge
- Example: "Definition of machine learning extracted from response"

## Example: Cross-Model Context

### Scenario

A user asks three questions in sequence:

1. **"What is quantum computing?"**
   - Router: Classifies as FACTUAL → Perplexity
   - Perplexity: Answers with citations
   - Memory: Saves definition and key concepts

2. **"Write a Python function to simulate a qubit"**
   - Router: Classifies as CODE → OpenAI
   - OpenAI: Retrieves memory fragments about quantum computing (from Perplexity!)
   - OpenAI: Writes code with full context understanding
   - Memory: Saves code patterns and concepts

3. **"What are the latest quantum computing breakthroughs in 2025?"**
   - Router: Classifies as FACTUAL → Perplexity
   - Perplexity: Retrieves memories from BOTH previous queries
   - Perplexity: Answers with awareness of previous discussion AND code context
   - Memory: Saves new information

**Result**: Each model benefits from insights generated by other models!

## Performance Benefits

1. **Better Accuracy**: Right model for the right task
2. **Cost Optimization**: Use cheaper models for simple queries
3. **Speed**: Fast models for quick queries, powerful models for complex ones
4. **Context Continuity**: No context loss when switching models
5. **Knowledge Accumulation**: Builds shared knowledge base over time

## Configuration

### Environment Variables

Ensure these are set in your `.env`:

```env
# Qdrant (for memory storage)
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_key

# OpenAI (for embeddings)
OPENAI_API_KEY=your_openai_key

# Optional: Provider API keys for fallback
PERPLEXITY_API_KEY=your_key
GOOGLE_API_KEY=your_key
OPENROUTER_API_KEY=your_key
```

### Feature Flags

The system respects existing feature flags:

- `COALESCE_ENABLED=1` - Request deduplication (default: enabled)
- `STREAM_FANOUT_ENABLED=1` - Streaming fan-out (default: enabled)

## Monitoring

### Router Performance

Track which models are being selected:

```python
from app.services.intelligent_router import intelligent_router

# Get performance stats
stats = intelligent_router.get_performance_stats(
    provider=ProviderType.OPENAI,
    model="gpt-4o"
)

print(stats)
# {
#   "provider": "openai",
#   "model": "gpt-4o",
#   "success_rate": 0.98,
#   "avg_latency_ms": 1250.5,
#   "error_rate": 0.02,
#   "total_requests": 150
# }
```

### Memory Usage

Monitor memory fragment creation and retrieval:

- Fragments saved: Logged in console
- Retrieval time: Included in `MemoryContext` response
- Fragment count: Tracked per query

## Advanced: Custom Classification

You can extend the query classifier with domain-specific rules:

```python
# In app/services/query_classifier.py

class QueryClassifier:
    # Add your custom keywords
    CUSTOM_DOMAIN_KEYWORDS = [
        "your", "domain", "specific", "terms"
    ]

    def _detect_query_type(self, query_lower: str) -> QueryType:
        # Add custom classification logic
        if self._count_keywords(query_lower, self.CUSTOM_DOMAIN_KEYWORDS) > 0:
            return QueryType.CUSTOM_DOMAIN

        # ... rest of logic
```

## Troubleshooting

### Issue: Router not working

**Check:**
1. At least one provider API key configured for the org
2. Database connection healthy
3. No errors in logs

### Issue: Memory not saving

**Check:**
1. Qdrant connection healthy
2. `use_memory=true` in request
3. OpenAI API key configured (for embeddings)
4. Memory guard not disabled

### Issue: Wrong model selected

**Check:**
1. Query classification (may need to adjust keywords)
2. Available providers for org
3. Consider manual override for critical queries

## Future Enhancements

Potential improvements:

1. **LLM-based Insight Extraction**: Use an LLM to extract structured insights (currently uses heuristics)
2. **Memory Decay**: Implement time-based relevance decay
3. **Cross-Organization Sharing**: Share anonymized insights across orgs
4. **Fine-tuned Router**: Train a classifier on actual usage patterns
5. **A/B Testing**: Test different routing strategies

## References

- Research Paper: "Collaborative Memory: Multi-User Memory Sharing in LLM Agents with Dynamic Access Control" (arXiv:2505.18279)
- Original Concept: Distributed Cognition (Hutchins, 1995)

## Questions?

This is a sophisticated system that combines multiple ML concepts. Key takeaways:

✅ **Memory is model-agnostic** - any model can read any memory fragment
✅ **Intelligent routing** - right model for right task
✅ **Two-tier memory** - private + shared knowledge
✅ **Provenance tracking** - know which model created what
✅ **Performance optimization** - track and improve over time

Start with automatic routing and memory enabled, then customize as needed!
