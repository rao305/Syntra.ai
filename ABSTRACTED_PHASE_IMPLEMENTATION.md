# Abstracted Phase Implementation - Complete Guide

## Overview

This document describes the new **Abstracted Phase UI** system for the Collaborate pipeline. The system abstracts the internal 7-step process into a clean 5-phase user-facing interface while maintaining full backward compatibility with the detailed internal logging.

## The Problem (Solved)

Users were seeing:
- Raw "Analyst", "Researcher", "Creator" labels → confusing
- 7 steps displayed in the UI → overwhelming
- Technical internal names exposed to end users
- No clear model selection visibility

## The Solution

**5 Clean Phases** that group internal roles:

1. **Understanding your query** (analyst + creator) - GPT
2. **Researching recent data and trends** (researcher) - Perplexity
3. **Refining and organizing the answer** (critic + internal_synth) - GPT
4. **Cross-checking with other AI models** (council) - Perplexity, Gemini, GPT, Kimi, OpenRouter
5. **Synthesizing final report** (director) - GPT

**Backend still runs all 7 internal steps**, but UI only shows 5 phases.

---

## Architecture

### Backend Changes

**Location:** `backend/app/services/collaborate/streaming.py`

#### Phase Mapping
```python
ROLE_TO_PHASE = {
    "analyst": "understand",
    "creator": "understand",
    "researcher": "research",
    "critic": "reason_refine",
    "internal_synth": "reason_refine",
    "council": "crosscheck",
    "director": "synthesize",
}

PHASE_LABELS = {
    "understand": "Understanding your query",
    "research": "Researching recent data and trends",
    "reason_refine": "Refining and organizing the answer",
    "crosscheck": "Cross-checking with other AI models",
    "synthesize": "Synthesizing final report",
}

PHASE_INDICES = {
    "understand": 0,
    "research": 1,
    "reason_refine": 2,
    "crosscheck": 3,
    "synthesize": 4,
}
```

#### Event Emission

The backend now emits **both**:

1. **Detailed events** (for internal logging):
   - `stage_start`, `stage_delta`, `stage_end` - one per internal role
   - Includes role name, detailed model info, step index (0-6)

2. **Abstracted events** (for user-facing UI):
   - `phase_start` - when entering a new phase
   - `phase_delta` - preview text for the phase
   - `phase_end` - when exiting a phase
   - Includes phase name, label, model display name, step index (0-4)

Example event sequence:

```
→ phase_start (understand, GPT-4.1, step 0)
  → stage_start (analyst, ...)
  → stage_delta (analyst, preview text)
  → stage_end (analyst, latency)
  → stage_start (creator, ...)
  → stage_delta (creator, preview text)
  → stage_end (creator, latency)
→ phase_end (understand, latency)

→ phase_start (research, Perplexity, step 1)
  → stage_start (researcher, ...)
  ... (stage events)
→ phase_end (research, latency)

... (repeat for reason_refine, crosscheck, synthesize)

→ final_answer_delta (streaming text)
→ final_answer_done (complete response)
```

---

### Frontend Changes

#### 1. Event Types

**Location:** `frontend/types/collaborate-events.ts`

New abstract types:
```typescript
export type AbstractPhase =
  | "understand"
  | "research"
  | "reason_refine"
  | "crosscheck"
  | "synthesize";

export type CollaborateEventType =
  // ... existing types ...
  | "phase_start"
  | "phase_delta"
  | "phase_end";

export interface PhaseStartEvent extends BaseCollaborateEvent {
  type: "phase_start";
  phase: AbstractPhase;
  label: string;
  model_display: string;
  step_index: number;
}

export interface PhaseDeltaEvent extends BaseCollaborateEvent {
  type: "phase_delta";
  phase: AbstractPhase;
  text_delta: string;
}

export interface PhaseEndEvent extends BaseCollaborateEvent {
  type: "phase_end";
  phase: AbstractPhase;
  latency_ms?: number;
}
```

Helper functions:
```typescript
export function getRolePhase(role: StepRole): AbstractPhase
export function getPhaseLabel(phase: AbstractPhase): string
export function getPhaseFromEvent(event: CollaborateEvent): AbstractPhase | null

export const PHASE_LABELS: Record<AbstractPhase, string>
export const PHASE_INDICES: Record<AbstractPhase, number>
export const TOTAL_PHASES = 5 // Instead of 7
```

#### 2. ThinkingStrip Component

**Location:** `frontend/components/collaborate/ThinkingStrip.tsx`

Updated interface:
```typescript
export interface ThinkingStep {
  phase: AbstractPhase; // Changed from "role"
  label: string;
  modelDisplay?: string;
  status: "pending" | "active" | "done";
  preview: string;
  latency_ms?: number;
}
```

The component now:
- Shows 5 phases instead of 7 roles
- Displays phase labels directly from `PHASE_LABELS`
- Shows models involved (e.g., "Perplexity, Gemini, GPT, Kimi, OpenRouter" for crosscheck)
- Accumulates preview text as phases progress
- Shows council summary badges for the crosscheck phase

#### 3. useThinkingState Hook

**Location:** `frontend/hooks/useThinkingState.ts`

Updated to handle both stage and phase events:

```typescript
// Handles phase_start, phase_delta, phase_end events
// Falls back to stage events for backward compatibility

type ThinkingAction =
  | { type: "INIT" }
  | { type: "INIT_PHASES" } // New: Initialize 5-phase view
  | { type: "PHASE_START"; phase: AbstractPhase; ... }
  | { type: "PHASE_DELTA"; phase: AbstractPhase; ... }
  | { type: "PHASE_END"; phase: AbstractPhase; ... }
  | { type: "STAGE_START"; role: StepRole; ... } // Still supported
  | ... // Other existing actions
```

Auto-detection: First `phase_start` event triggers automatic switch to phase view.

#### 4. Alternative Hook: usePhaseCollaboration

**Location:** `frontend/hooks/use-phase-collaboration.ts`

Simpler hook specifically designed for phase-based events:

```typescript
const {
  phases,           // Record<AbstractPhase, ThinkingStep>
  councilSummary,   // Progress of reviews
  currentPhaseIndex,
  processEvent,     // Main handler for all events
  getPhasesList,    // Returns array for ThinkingStrip
} = usePhaseCollaboration({
  onPhaseUpdate,
  onCouncilProgress,
  onFinalAnswerStart,
  onFinalAnswerDelta,
  onFinalAnswerComplete,
  onError,
})
```

---

## Usage Examples

### Example 1: Using ChatWithThinking (Existing Pattern)

**Location:** `frontend/components/collaborate/ChatWithThinking.example.tsx`

```typescript
function ChatWithThinking({ threadId }: { threadId: string }) {
  const thinking = useThinkingState(); // Handles both phase and stage events

  async function handleCollaborate() {
    thinking.init(); // Initialize

    // Stream collaborate events
    const response = await fetch(`/api/threads/${threadId}/collaborate-stream`);

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const event = parseCollaborateEvent(line.slice(6));
        thinking.handleEvent(event); // Auto-handles phase or stage events
      }
    }
  }

  return (
    <>
      <ThinkingStrip
        steps={thinking.steps}           // Now shows 5 phases
        currentIndex={thinking.currentIndex}
        councilSummary={thinking.councilSummary}
      />
      {/* Final answer */}
    </>
  );
}
```

### Example 2: Using usePhaseCollaboration (New Pattern)

```typescript
function ChatWithPhases({ threadId }: { threadId: string }) {
  const {
    phases,
    councilSummary,
    processEvent,
    getPhasesList,
  } = usePhaseCollaboration({
    onPhaseUpdate: (phase, step) => {
      console.log(`Phase ${phase} updated:`, step);
    },
    onCouncilProgress: (summary) => {
      console.log(`Council: ${summary.completed}/${summary.total}`);
    },
    onFinalAnswerDelta: (text) => {
      // Append to chat bubble
    },
    onFinalAnswerComplete: (response) => {
      // Store final response
    },
  });

  const handleCollaborate = async () => {
    const response = await fetch(`/api/threads/${threadId}/collaborate-stream`);

    const reader = response.body?.getReader();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const event = parseCollaborateEvent(chunk);
      processEvent(event); // Handles all events
    }
  };

  return (
    <ThinkingStrip
      steps={getPhasesList()}
      currentIndex={...}
      councilSummary={councilSummary}
    />
  );
}
```

---

## Event Flow Example

For the question: *"Why are college grads struggling to find jobs?"*

### Actual Event Sequence

```json
1. {"type": "phase_start", "phase": "understand", "label": "Understanding your query", "model_display": "GPT-4.1", "step_index": 0}
2. {"type": "stage_start", "role": "analyst", "label": "Analyst", ...}
3. {"type": "phase_delta", "phase": "understand", "text_delta": "Clarifying timeframe..."}
4. {"type": "stage_end", "role": "analyst", "latency_ms": 3200}
5. {"type": "stage_start", "role": "creator", "label": "Creator", ...}
6. {"type": "phase_delta", "phase": "understand", "text_delta": "Designing answer structure..."}
7. {"type": "stage_end", "role": "creator", "latency_ms": 2800}
8. {"type": "phase_end", "phase": "understand", "latency_ms": 6000}

9. {"type": "phase_start", "phase": "research", "label": "Researching recent data and trends", "model_display": "Perplexity", "step_index": 1}
10. {"type": "stage_start", "role": "researcher", "label": "Researcher", ...}
11. {"type": "phase_delta", "phase": "research", "text_delta": "Pulling labor market stats..."}
12. {"type": "stage_end", "role": "researcher", "latency_ms": 4100}
13. {"type": "phase_end", "phase": "research", "latency_ms": 4100}

... (reason_refine, crosscheck, synthesize phases)

14. {"type": "phase_start", "phase": "synthesize", "label": "Synthesizing final report", "model_display": "GPT-4.1 (Director)", "step_index": 4}
15. {"type": "final_answer_delta", "text_delta": "Today's college undergraduates..."}
16. {"type": "final_answer_delta", "text_delta": " face a significantly..."}
... (more deltas)
17. {"type": "phase_end", "phase": "synthesize", "latency_ms": 8500}
18. {"type": "final_answer_done", "response": {...CollaborateResponse...}}
```

### What User Sees

**ThinkingStrip Timeline:**

```
Step 1 / 5 – Understanding your query… (Model: GPT-4.1)
  ✓ Clarifying timeframe… Designing answer structure… (6.0s)

Step 2 / 5 – Researching recent data and trends… (Model: Perplexity)
  ✓ Pulling labor market stats… (4.1s)

Step 3 / 5 – Refining and organizing the answer… (Model: GPT-4.1)
  ✓ Checking for missing factors… Combining research… (5.2s)

Step 4 / 5 – Cross-checking with other AI models…
  (Perplexity, Gemini, GPT, Kimi, OpenRouter)
  ⊙ 3/5 reviews complete · 2 agree · 1 mixed

Step 5 / 5 – Synthesizing final report… (Model: GPT-4.1 (Director))
  ◊ Merging internal reasoning and external reviews…
```

Then the final clean answer appears in the chat bubble.

---

## Backward Compatibility

✅ **Old code still works:**
- Detailed `stage_*` events are still emitted (for internal logging/observability)
- `useThinkingState` hook auto-detects and handles both phase and stage events
- Existing code that only looks for stage events continues to function

✅ **New code is cleaner:**
- Focus on `phase_*` events for user-facing UI
- `PHASE_LABELS` and helpers make rendering simple
- Five clean phases instead of seven confusing roles

---

## Files Modified/Created

### Backend
- ✏️ `backend/app/services/collaborate/streaming.py` - Added phase mapping and phase event emission

### Frontend Types
- ✏️ `frontend/types/collaborate-events.ts` - Added AbstractPhase type, phase events, helpers

### Frontend Components
- ✏️ `frontend/components/collaborate/ThinkingStrip.tsx` - Updated to use phases instead of roles

### Frontend Hooks
- ✏️ `frontend/hooks/useThinkingState.ts` - Enhanced to handle phase events
- ✨ `frontend/hooks/use-phase-collaboration.ts` - NEW: Simplified hook for phase-only events

### Examples
- `frontend/components/collaborate/ChatWithThinking.example.tsx` - Already works with both systems

---

## Key Benefits

| Aspect | Before | After |
|--------|--------|-------|
| **UI Complexity** | 7 confusing steps | 5 clear phases |
| **Model Visibility** | Hidden in role names | Explicitly shown |
| **User Experience** | "Why is there a Critic?" | Clear process flow |
| **Backend Flexibility** | Coupled to UI | Decoupled - can change internal steps |
| **Logging** | Only one event type | Rich detailed + high-level view |

---

## Testing

To verify the implementation:

1. **Backend emits phase events correctly:**
   ```python
   # Check streaming.py emits phase_start/end at right times
   # Verify phase_delta accumulates preview text
   # Confirm council_progress still works
   ```

2. **Frontend handles phase events:**
   ```typescript
   // Test useThinkingState with phase events
   // Test ThinkingStrip renders 5 phases
   // Test council summary displays correctly
   ```

3. **E2E test:**
   ```bash
   # Run collaborate endpoint
   # Verify phase events in stream
   # Verify UI shows correct phases and progress
   ```

---

## Future Enhancements

- Add "Show detailed reasoning" mode that expands to show all 7 stages
- Add per-phase confidence scores
- Add model comparison for council reviews
- Add phase-specific timing breakdowns
- Export phase-based reasoning as structured data

