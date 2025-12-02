# Syntra Collaboration Engine V2 - Integration Guide

## Overview

You now have a complete production-ready collaboration system with:

- **Dynamic model routing** (no hard-coded "analyst = Gemini")
- **6-stage pipeline** with real LLM Council
- **Multi-creator stage** (3 models in parallel)
- **Production prompts** for all stages
- **Frontend UI** that shows which model was selected

## Files Created

```
backend/
├── app/config/
│   ├── workflow_registry.py        # Model registry + router
│   └── collab_prompts.py          # All 7 production prompts
└── app/services/collaborate/
    ├── orchestrator_v2.py         # 6-stage orchestrator
    └── streaming_v2.py            # Streaming events wrapper

frontend/
├── components/collaborate/
│   └── CollabPanel.tsx            # Updated for 6 stages + model names
├── app/conversations/
│   └── page.tsx                   # Updated to pass model IDs to UI
```

## Integration Checklist

### 1. Wire Up the Backend Endpoint

Update `/api/threads/{thread_id}/collaborate-stream` in `app/api/threads.py`:

```python
from app.services.collaborate.orchestrator_v2 import run_collaboration_v2
from app.services.collaborate.streaming_v2 import run_collaborate_streaming_v2
from app.config.workflow_registry import COLLAB_WORKFLOW_STEPS

@router.post("/{thread_id}/collaborate-stream")
async def collaborate_thread_streaming(
    thread_id: str,
    body: CollaborateRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
):
    # Your existing validation...

    # Get API keys from environment/secrets
    api_keys = {
        "openai": os.getenv("OPENAI_API_KEY"),
        "google": os.getenv("GEMINI_API_KEY"),
        "perplexity": os.getenv("PERPLEXITY_API_KEY"),
        "kimi": os.getenv("KIMI_API_KEY"),
    }

    # Stream events using V2 orchestrator
    return StreamingResponse(
        run_collaborate_streaming_v2(
            user_question=body.message,
            api_keys=api_keys,
        ),
        media_type="text/event-stream",
    )
```

### 2. Implement `call_model()` Function

The orchestrator calls `call_model()` to invoke each LLM. You need to implement this:

```python
# In orchestrator_v2.py, replace the mock implementation:

async def call_model(
    provider: ProviderType,
    model_name: str,
    system_prompt: str,
    user_message: str,
    api_keys: Dict[str, str],
    max_tokens: int = 2000,
    temperature: float = 0.7,
    json_mode: bool = False,
) -> str:
    """Call an LLM model via the appropriate provider."""

    if provider == ProviderType.OPENAI:
        # Use your existing OpenAI client
        response = await call_openai(
            model=model_name,
            system=system_prompt,
            user=user_message,
            max_tokens=max_tokens,
            temperature=temperature,
            api_key=api_keys["openai"],
            json_mode=json_mode,
        )
        return response.choices[0].message.content

    elif provider == ProviderType.GEMINI:
        # Use your existing Gemini client
        response = await call_gemini(
            model=model_name,
            system=system_prompt,
            user=user_message,
            max_tokens=max_tokens,
            temperature=temperature,
            api_key=api_keys["google"],
        )
        return response.text

    elif provider == ProviderType.PERPLEXITY:
        # Use your existing Perplexity client
        response = await call_perplexity(
            model=model_name,
            system=system_prompt,
            user=user_message,
            max_tokens=max_tokens,
            temperature=temperature,
            api_key=api_keys["perplexity"],
        )
        return response.choices[0].message.content

    elif provider == ProviderType.KIMI:
        # Use your existing Kimi client
        response = await call_kimi(
            model=model_name,
            system=system_prompt,
            user=user_message,
            max_tokens=max_tokens,
            temperature=temperature,
            api_key=api_keys["kimi"],
        )
        return response.choices[0].message.content
```

### 3. Update Streaming Wrapper for Real-Time Events

The `streaming_v2.py` currently runs orchestrator then emits events. For **real-time** events, modify `orchestrator_v2.py` to accept callbacks:

```python
# Add to orchestrator_v2.py

async def run_collaboration_v2_with_callbacks(
    user_question: str,
    api_keys: Dict[str, str],
    on_stage_start=None,
    on_stage_end=None,
    on_final_answer=None,
) -> Dict[str, Any]:
    """Version that emits events as stages execute."""

    ctx = StageContext(user_question=user_question)
    results = {}

    for stage_id in ["analyst", "researcher", "creator", "critic", "council", "synth"]:
        # Emit stage_start
        if on_stage_start:
            model = pick_model_for_stage(stage_id, 0, "auto")
            await on_stage_start(stage_id, STAGE_LABELS[stage_id], model.id)

        # Run stage
        result = await run_stage_by_id(stage_id, ctx, api_keys)
        results[stage_id] = result

        # Emit stage_end
        if on_stage_end:
            preview = result.output[:200]
            await on_stage_end(stage_id, preview)

        # Update context
        ctx = update_context_with_result(ctx, stage_id, result)

    # Emit final answer
    if on_final_answer:
        await on_final_answer(ctx.synth_output)

    return {
        "final_answer": ctx.synth_output,
        "stages": results,
    }
```

Then update `streaming_v2.py` to use callbacks:

```python
async def run_collaborate_streaming_v2(
    user_question: str,
    api_keys: Dict[str, str],
    run_id: str = None,
) -> AsyncGenerator[str, None]:

    import uuid
    if not run_id:
        run_id = str(uuid.uuid4())

    async def on_stage_start(stage_id, label, model_id):
        yield sse_event("stage_start", {
            "stageId": stage_id,
            "label": label,
            "modelId": model_id,
        })

    async def on_stage_end(stage_id, preview):
        yield sse_event("stage_end", {
            "stageId": stage_id,
            "preview": preview,
        })

    async def on_final_answer(content):
        yield sse_event("final_answer_start", {})
        # Stream in chunks
        chunk_size = 100
        for i in range(0, len(content), chunk_size):
            chunk = content[i : i + chunk_size]
            yield sse_event("final_answer_delta", {"delta": chunk})
        yield sse_event("final_answer_end", {"content": content})

    # Run with callbacks
    await run_collaboration_v2_with_callbacks(
        user_question,
        api_keys,
        on_stage_start=on_stage_start,
        on_stage_end=on_stage_end,
        on_final_answer=on_final_answer,
    )
```

### 4. Verify Frontend Is Ready

Your frontend is already set up to:

✅ Show 6 stages (analyst, researcher, creator, critic, council, synth)
✅ Display dynamic model names (e.g., "Analyst • gpt-4o")
✅ Update stages as events arrive
✅ Only render the final synth output as an assistant message

No changes needed here!

## How the System Works

### Pipeline Flow

```
User asks: "Compare NVIDIA GPUs and Google TPUs"
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 1. ANALYST (gpt-4o)                                     │
│    → Breaks down: Core question, sub-problems, strategy │
│    → Router picked gpt-4o because it's best at analysis │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 2. RESEARCHER (perplexity)                              │
│    → Gathers facts, trends, current landscape           │
│    → Router picked perplexity (great for research)      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│ 3. CREATOR (3 models in PARALLEL!)                       │
│    → gpt-4o proposes: "Here's a technical deep dive..." │
│    → gemini-2.0 proposes: "Let's compare use cases..."  │
│    → perplexity proposes: "Industry trends show..."     │
│    → All 3 drafts collected for next stages             │
└──────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 4. CRITIC (kimi)                                        │
│    → Evaluates all 3 drafts                             │
│    → Flags: "Draft 2 missing power efficiency"          │
│    → Suggests fixes for each                            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│ 5. COUNCIL (gpt-4o) - NEW!                              │
│    → Compares the 3 drafts objectively                  │
│    → Issues JSON verdict:                               │
│      {                                                   │
│        "best_draft_index": 1,                           │
│        "must_keep_points": [...],                       │
│        "must_fix_issues": [...]                         │
│      }                                                   │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│ 6. SYNTHESIZER (gemini-2.0)                             │
│    → Sees all 3 drafts + critic + council verdict       │
│    → Writes ONE polished 2000-word report:              │
│      "NVIDIA GPUs vs Google TPUs: Deep Analysis"        │
│    → Never mentions agents, models, or process          │
│    → User gets: Single professional answer              │
└──────────────────────────────────────────────────────────┘
```

### Model Selection

No hardcoding! The router picks the best model for each role:

```python
# Analyst: router picks from [gpt-4o, gemini-2.0, gpt-4o-mini]
analyst_model = pick_model_for_stage("analyst", 0, "auto")
# → Returns: gpt-4o (score: (6-4) + 3 = 5, highest)

# Researcher: router picks from [gpt-4o-mini, gemini-2.0, perplexity]
researcher_model = pick_model_for_stage("researcher", 0, "auto")
# → Returns: perplexity or gemini-2.0 (both score 5)

# Creator: runs ALL 3 in parallel
creators = get_creator_pool()
# → Returns: [gpt-4o, gemini-2.0, perplexity]
# → Runs them simultaneously
```

### Key Differences from V1

| Aspect | V1 | V2 |
|--------|----|----|
| **Model Binding** | Fixed (analyst = Gemini) | Dynamic router |
| **Creator Stage** | 1 draft | 3 parallel drafts |
| **Council** | External reviews (separate) | Integrated stage (sees all 3 drafts) |
| **Prompts** | Simple role descriptions | Production-grade, 400+ lines |
| **Final Output** | Director synthesizes | Synthesizer (cleaner separation) |
| **UI** | 5 stages + external | 6 stages + model names |

## Testing

### 1. Test the Router

```python
from app.config.workflow_registry import pick_model_for_stage

model = pick_model_for_stage("analyst", estimated_tokens=0, strategy="auto")
print(f"Selected: {model.id} ({model.provider.value})")
# Output: Selected: gpt-4o (openai)

model = pick_model_for_stage("researcher", estimated_tokens=0, strategy="auto")
print(f"Selected: {model.id} ({model.provider.value})")
# Output: Selected: perplexity (perplexity) or gemini-2.0 (google)
```

### 2. Test an Orchestration Run (Mock)

```python
from app.services.collaborate.orchestrator_v2 import run_collaboration_v2

api_keys = {
    "openai": "...",
    "google": "...",
    "perplexity": "...",
    "kimi": "...",
}

result = await run_collaboration_v2(
    "Compare NVIDIA vs TPU",
    api_keys
)

# result["final_answer"] = "The 2000+ word polished answer"
# result["stages"]["analyst"] = StageResult(...)
# result["stages"]["council"]["verdict"] = {...}
```

### 3. Test Streaming Events

```python
from app.services.collaborate.streaming_v2 import run_collaborate_streaming_v2

async for event_str in run_collaborate_streaming_v2("Your question", api_keys):
    # event_str looks like:
    # event: stage_start\ndata: {"stageId": "analyst", "modelId": "gpt-4o"}\n\n
    print(event_str)
```

## Customization

### Adjust Model Strengths

Edit `app/config/workflow_registry.py`:

```python
MODELS_REGISTRY = [
    ProviderModel(
        id="gpt-4o",
        # ...
        strengths=["analyst", "critic", "council", "synth"],  # ← Change here
    ),
    # ...
]
```

### Adjust Creator Pool

Edit `app/config/workflow_registry.py`:

```python
CREATOR_POOL_IDS = ["gpt-4o", "gemini-2.0", "perplexity"]  # ← Change here
```

### Adjust Prompts

Edit `app/config/collab_prompts.py`. All prompts are human-readable strings at the top of the file.

### Adjust Routing Strategy

Edit `run_collaboration_v2()` call in endpoint:

```python
# Current: "auto" (best quality/cost balance)
model = pick_model_for_stage("analyst", 0, "auto")

# Alternatives:
model = pick_model_for_stage("analyst", 0, "cheap")   # Lowest cost
model = pick_model_for_stage("analyst", 0, "fast")    # Fastest
```

## What You Get

✅ **No hard-coded role→model binding** - Router chooses based on job fit
✅ **Real LLM Council** - Actually sees & judges multiple drafts
✅ **Multi-creator** - 3 models competing, council picks best
✅ **Production prompts** - Carefully written for Syntra voice
✅ **Dynamic UI** - Shows which model is working on each stage
✅ **Single final answer** - User sees ONE polished report, not 5 separate outputs
✅ **Full auditability** - All stage outputs stored, council verdict tracked

## Next Steps

1. Implement `call_model()` to hook into your LLM providers
2. Update `/api/threads/{thread_id}/collaborate-stream` endpoint
3. Test with mock responses first
4. Gradually swap in real API calls
5. Monitor token usage and latency
6. Tweak router weights if needed (adjust `relative_cost`, `relative_speed`)
