# Abstracted Phase UI - Visual Guide

## The User Experience

When a user asks: *"Why are college grads struggling to find jobs compared to 2018?"*

### What They See

```
┌─────────────────────────────────────────────────────────────────┐
│ 🧠 AI Team Collaborating                            [Hide]      │
│    Step 1 of 5 — Understanding your query                      │
├─────────────────────────────────────────────────────────────────┤
│ ◆ Understanding your query         · GPT          ✓ 6.0s      │
│   Clarifying timeframe… designing structure…                   │
│                                                                 │
│ ◇ Researching recent data           · Perplexity  ⊗ Pending  │
│                                                                 │
│ ◇ Refining and organizing           · GPT         ⊗ Pending  │
│                                                                 │
│ ◇ Cross-checking with other AIs     · Council     ⊗ Pending  │
│                                                                 │
│ ◇ Synthesizing final report         · GPT         ⊗ Pending  │
└─────────────────────────────────────────────────────────────────┘

[... a few seconds pass ...]

┌─────────────────────────────────────────────────────────────────┐
│ 🧠 AI Team Collaborating                            [Hide]      │
│    Step 2 of 5 — Researching recent data                       │
├─────────────────────────────────────────────────────────────────┤
│ ✓ Understanding your query         · GPT          ✓ 6.0s      │
│                                                                 │
│ ◆ Researching recent data           · Perplexity  ⊙ Thinking │
│   Pulling labor market stats… unemployment trends…             │
│                                                                 │
│ ◇ Refining and organizing           · GPT         ⊗ Pending  │
│                                                                 │
│ ◇ Cross-checking with other AIs     · Council     ⊗ Pending  │
│                                                                 │
│ ◇ Synthesizing final report         · GPT         ⊗ Pending  │
└─────────────────────────────────────────────────────────────────┘

[... research completes ...]

┌─────────────────────────────────────────────────────────────────┐
│ 🧠 AI Team Collaborating                            [Hide]      │
│    Step 4 of 5 — Cross-checking with other AI models           │
├─────────────────────────────────────────────────────────────────┤
│ ✓ Understanding your query         · GPT          ✓ 6.0s      │
│ ✓ Researching recent data           · Perplexity  ✓ 4.1s      │
│ ✓ Refining and organizing           · GPT         ✓ 5.2s      │
│                                                                 │
│ ◆ Cross-checking with other AIs                                │
│   Perplexity, Gemini, GPT, Kimi, OpenRouter                   │
│   3/5 reviews complete                                         │
│   ✓ 2 agree    ◆ 1 mixed    ✕ 0 disagree                      │
│                                                                 │
│ ◇ Synthesizing final report         · GPT         ⊗ Pending  │
└─────────────────────────────────────────────────────────────────┘

[... all reviews complete ...]

┌─────────────────────────────────────────────────────────────────┐
│ 🧠 AI Team Collaborating                            [Hide]      │
│    Step 5 of 5 — Synthesizing final report                     │
├─────────────────────────────────────────────────────────────────┤
│ ✓ Understanding your query         · GPT          ✓ 6.0s      │
│ ✓ Researching recent data           · Perplexity  ✓ 4.1s      │
│ ✓ Refining and organizing           · GPT         ✓ 5.2s      │
│ ✓ Cross-checking with other AIs     · Council     ✓ 7.8s      │
│                                                                 │
│ ◆ Synthesizing final report         · GPT         ⊙ Thinking │
│   Merging internal reasoning and external reviews…             │
└─────────────────────────────────────────────────────────────────┘

[... synthesis completes ...]
```

### Then the Final Answer Appears

```
Today's college undergraduates face a significantly tougher job market
than their 2018 counterparts, driven by:

1. RISING UNEMPLOYMENT & UNDEREMPLOYMENT
   • Unemployment for Class of 2023: 4.2% (vs 2.3% in 2018)
   • Underemployment: 52% (up from 43%)
   • "Working at coffee shop with degree" phenomenon widespread

[... complete answer with tables and graphs ...]
```

---

## Backend Event Stream (Raw)

```json
=== Phase 1: "understand" (Understanding your query) ===

→ phase_start
{
  "type": "phase_start",
  "run_id": "run_abc123",
  "timestamp": "2025-11-30T18:00:00.000Z",
  "phase": "understand",
  "label": "Understanding your query",
  "model_display": "GPT-4.1",
  "step_index": 0
}

  → stage_start (analyst)
  {
    "type": "stage_start",
    "role": "analyst",
    "label": "Analyst",
    "model_display": "GPT-4.1",
    "step_index": 0
  }

  → phase_delta
  {
    "type": "phase_delta",
    "phase": "understand",
    "text_delta": "Clarifying timeframe (2018–2025) and focus..."
  }

  → stage_end (analyst)
  {
    "type": "stage_end",
    "role": "analyst",
    "latency_ms": 3200
  }

  → stage_start (creator)
  {
    "type": "stage_start",
    "role": "creator",
    "label": "Creator",
    "model_display": "GPT-4.1",
    "step_index": 2
  }

  → phase_delta
  {
    "type": "phase_delta",
    "phase": "understand",
    "text_delta": "Designing answer structure: intro, sections..."
  }

  → stage_end (creator)
  {
    "type": "stage_end",
    "role": "creator",
    "latency_ms": 2800
  }

← phase_end
{
  "type": "phase_end",
  "phase": "understand",
  "latency_ms": 6000
}


=== Phase 2: "research" (Researching recent data) ===

→ phase_start
{
  "type": "phase_start",
  "phase": "research",
  "label": "Researching recent data and trends",
  "model_display": "Perplexity Sonar",
  "step_index": 1
}

  → stage_start (researcher)
  {
    "type": "stage_start",
    "role": "researcher",
    "label": "Researcher",
    "model_display": "Perplexity Sonar",
    "step_index": 1
  }

  → phase_delta
  {
    "type": "phase_delta",
    "phase": "research",
    "text_delta": "Pulling stats on unemployment (4.2%), underemployment..."
  }

  → stage_end (researcher)
  {
    "type": "stage_end",
    "role": "researcher",
    "latency_ms": 4100
  }

← phase_end
{
  "type": "phase_end",
  "phase": "research",
  "latency_ms": 4100
}


=== Phase 3: "reason_refine" (Refining and organizing) ===

→ phase_start
{
  "type": "phase_start",
  "phase": "reason_refine",
  "label": "Refining and organizing the answer",
  "model_display": "GPT-4.1",
  "step_index": 2
}

  [... stage events for critic and internal_synth ...]

← phase_end
{
  "type": "phase_end",
  "phase": "reason_refine",
  "latency_ms": 5200
}


=== Phase 4: "crosscheck" (Cross-checking with other AIs) ===

→ phase_start
{
  "type": "phase_start",
  "phase": "crosscheck",
  "label": "Cross-checking with other AI models",
  "model_display": "Perplexity, Gemini, GPT, Kimi, OpenRouter",
  "step_index": 3
}

  → stage_start (council)

  → council_progress
  {
    "type": "council_progress",
    "completed": 1,
    "total": 5,
    "stance_counts": {
      "agree": 1,
      "mixed": 0,
      "disagree": 0
    }
  }

  → council_progress
  {
    "type": "council_progress",
    "completed": 3,
    "total": 5,
    "stance_counts": {
      "agree": 2,
      "mixed": 1,
      "disagree": 0
    }
  }

  → council_progress
  {
    "type": "council_progress",
    "completed": 5,
    "total": 5,
    "stance_counts": {
      "agree": 3,
      "mixed": 2,
      "disagree": 0
    }
  }

  → stage_end (council)

← phase_end
{
  "type": "phase_end",
  "phase": "crosscheck",
  "latency_ms": 7800
}


=== Phase 5: "synthesize" (Synthesizing final report) ===

→ phase_start
{
  "type": "phase_start",
  "phase": "synthesize",
  "label": "Synthesizing final report",
  "model_display": "GPT-4.1 (Director)",
  "step_index": 4
}

  → stage_start (director)

  → phase_delta
  {
    "type": "phase_delta",
    "phase": "synthesize",
    "text_delta": "Merging internal reasoning and external reviews..."
  }

  [... final_answer_delta events (character by character) ...]

  → final_answer_delta
  {
    "type": "final_answer_delta",
    "text_delta": "Today's college undergraduates face a..."
  }

  → final_answer_delta
  {
    "type": "final_answer_delta",
    "text_delta": " significantly tougher job market than..."
  }

  [... more deltas ...]

  → final_answer_done
  {
    "type": "final_answer_done",
    "response": {
      "final_answer": {
        "content": "Today's college undergraduates...[full answer]...",
        "model": {"provider": "openai", "model_slug": "gpt-4.1"},
        "created_at": "2025-11-30T18:00:12.000Z"
      },
      "internal_pipeline": {
        "stages": [
          {"role": "analyst", "content": "..."},
          {"role": "researcher", "content": "..."},
          ...
        ]
      },
      "external_reviews": [
        {"source": "perplexity", "stance": "agree", "content": "..."},
        ...
      ],
      "meta": {
        "run_id": "run_abc123",
        "total_latency_ms": 26100,
        "models_involved": [...]
      }
    }
  }

← phase_end
{
  "type": "phase_end",
  "phase": "synthesize",
  "latency_ms": 8500
}
```

---

## Frontend State Management

### Using useThinkingState Hook

```typescript
// Initial state (before any events)
{
  steps: [
    { phase: "understand", label: "Understanding your query", status: "pending", preview: "" },
    { phase: "research", label: "Researching recent data...", status: "pending", preview: "" },
    { phase: "reason_refine", label: "Refining and organizing...", status: "pending", preview: "" },
    { phase: "crosscheck", label: "Cross-checking with other AIs...", status: "pending", preview: "" },
    { phase: "synthesize", label: "Synthesizing final report", status: "pending", preview: "" }
  ],
  currentIndex: 0,
  councilSummary: undefined,
  isCollapsed: false
}

// After phase_start (understand)
{
  steps: [
    {
      phase: "understand",
      label: "Understanding your query",
      modelDisplay: "GPT-4.1",
      status: "active",
      preview: ""
    },
    // ... (others unchanged)
  ],
  currentIndex: 0
}

// After phase_delta events accumulate
{
  steps: [
    {
      phase: "understand",
      label: "Understanding your query",
      modelDisplay: "GPT-4.1",
      status: "active",
      preview: "Clarifying timeframe... Designing answer structure..."
    },
    // ...
  ]
}

// After phase_end (understand)
{
  steps: [
    {
      phase: "understand",
      label: "Understanding your query",
      modelDisplay: "GPT-4.1",
      status: "done",
      latency_ms: 6000,
      preview: "..."
    },
    {
      phase: "research",
      label: "Researching recent data...",
      modelDisplay: "Perplexity Sonar",
      status: "active",
      preview: ""
    },
    // ...
  ],
  currentIndex: 1
}

// After council_progress events
{
  councilSummary: {
    completed: 3,
    total: 5,
    stanceCounts: {
      agree: 2,
      mixed: 1,
      disagree: 0
    }
  }
}

// Final state (after phase_end synthesize)
{
  steps: [
    { phase: "understand", status: "done", latency_ms: 6000, ... },
    { phase: "research", status: "done", latency_ms: 4100, ... },
    { phase: "reason_refine", status: "done", latency_ms: 5200, ... },
    { phase: "crosscheck", status: "done", latency_ms: 7800, ... },
    { phase: "synthesize", status: "done", latency_ms: 8500, ... }
  ],
  currentIndex: 4
}
```

---

## Timeline: Events → UI Update → User Sees

```
Time  Backend                         Frontend State              User Sees
──────────────────────────────────────────────────────────────────────────

0ms   phase_start (understand)        → currentIndex = 0          ◇ ◇ ◇ ◇ ◇
                                      → status = active           Step 1: Understanding

100ms phase_delta                     → preview updated          (blank)
      Clarifying timeframe...

2000ms phase_delta                    → preview updated          Clarifying...
       Designing structure...

3200ms stage_end (analyst)
      (internal only)

4000ms phase_delta                    → preview updated          Clarifying... Designing...
       Designing structure...

6000ms phase_end (understand)         → status = done            ✓ Understanding (6.0s)
                                      → currentIndex = 1         ◆ Researching...
                                      → status = active

6100ms phase_start (research)         → step[1].status = active  Step 2: Researching
       Perplexity

6200ms phase_delta                    → preview updated          (blank)
       Pulling stats...

10100ms phase_end (research)          → status = done            ✓ Researching (4.1s)
                                      → currentIndex = 2         ◆ Refining...

... (reason_refine and crosscheck phases)

25300ms phase_start (synthesize)      → status = active          Step 5: Synthesizing
        GPT Director                  → currentIndex = 4         ⊙ Merging reasoning...

25400ms phase_delta                   → preview = "Merging..."
        Merging internal reasoning...

25500ms final_answer_delta            → answer += "Today's"      Final answer starts
        Today's                                                    appearing in bubble

26000ms final_answer_delta            → answer += " college..."
        college...

... (more deltas for 5+ seconds)

34000ms final_answer_done             → response stored          Final answer complete
        {response: {...}}              → UI can show details      All phases marked done

34000ms phase_end (synthesize)        → status = done            Thinking strip collapsed
                                      → all steps status = done   Final answer displayed
```

---

## TypeScript Type Flow

```typescript
// Event comes from backend as JSON string
const jsonString = '{"type":"phase_start","phase":"understand",...}'

// Parse it
const event = parseCollaborateEvent(jsonString)
// → PhaseStartEvent { type: "phase_start", phase: "understand", ... }

// Process with hook
thinking.handleEvent(event)
// → Dispatch "PHASE_START" action

// Reducer updates state
const newState = thinkingReducer(state, {
  type: "PHASE_START",
  phase: "understand",
  label: "Understanding your query",
  modelDisplay: "GPT-4.1",
  stepIndex: 0
})

// ThinkingStrip receives updated steps
<ThinkingStrip
  steps={newState.steps}  // Array of ThinkingStep with phase: AbstractPhase
  currentIndex={newState.currentIndex}
/>

// Component renders 5 phases
```

---

## Key Differences: Old vs New

| Aspect | Old (7 Stages) | New (5 Phases) |
|--------|---|---|
| **Event Types** | `stage_*` only | `phase_*` + `stage_*` |
| **UI Complexity** | 7 steps shown | 5 steps shown |
| **Step Key** | `role: "analyst"` | `phase: "understand"` |
| **Model Display** | Single per role | "Perplexity, Gemini, GPT..." for council |
| **Status Bar** | "Step 2 of 7" | "Step 2 of 5" |
| **Preview** | One preview per role | One preview per phase (accumulates) |
| **Council View** | Separate step | Integrated into crosscheck phase |
| **Hook Usage** | `useThinkingState()` | `useThinkingState()` or `usePhaseCollaboration()` |

---

## Summary

The abstracted phase UI provides:

✅ **Clean User Experience**
- 5 clear phases instead of 7 confusing roles
- Obvious model involvement
- Smooth animated progress

✅ **Powerful Backend**
- Still runs full 7-step internal pipeline
- All detailed events logged for observability
- Can evolve internal process without UI changes

✅ **Full Transparency**
- Users see exactly which models are involved
- Council review progress visible
- Timing breaks down per phase
- Final answer fully sourced

