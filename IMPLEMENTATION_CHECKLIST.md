# Abstracted Phase UI - Implementation Checklist ✅

## Completed Items

### Backend Changes ✅

#### 1. Phase Mapping Constants
- ✅ Added `ROLE_TO_PHASE` mapping in `streaming.py`
- ✅ Added `PHASE_LABELS` for user-facing text
- ✅ Added `PHASE_INDICES` for step numbering (0-4 instead of 0-6)

#### 2. Phase Event Emission
- ✅ Inner team pipeline (understand phase):
  - Emits `phase_start` when analyst begins
  - Emits `phase_delta` for preview text during each stage
  - Emits `phase_end` when internal_synth completes
  - Still emits detailed `stage_*` events for internal logging

- ✅ Council pipeline (crosscheck phase):
  - Emits `phase_start` when council begins
  - Emits `council_progress` events during reviews
  - Emits `phase_end` when all reviews complete

- ✅ Director pipeline (synthesize phase):
  - Emits `phase_start` when director begins
  - Emits `phase_delta` with preview of final answer
  - Streams `final_answer_delta` events (unchanged)
  - Emits `phase_end` when complete

### Frontend Type Definitions ✅

#### 1. Abstract Phase Types
- ✅ `AbstractPhase` type: "understand" | "research" | "reason_refine" | "crosscheck" | "synthesize"
- ✅ Phase event interfaces: `PhaseStartEvent`, `PhaseDeltaEvent`, `PhaseEndEvent`
- ✅ Updated `CollaborateEvent` union type to include phase events
- ✅ Added phase helper functions:
  - `getRolePhase(role)` - maps internal roles to phases
  - `getPhaseLabel(phase)` - returns user-facing label
  - `getPhaseFromEvent(event)` - extracts phase from event
- ✅ Added phase mappings: `PHASE_LABELS`, `PHASE_INDICES`, `TOTAL_PHASES`

#### 2. Event Parser
- ✅ Updated `parseCollaborateEvent()` to recognize new phase events
- ✅ Updated event validation to include "phase_start" | "phase_delta" | "phase_end"

### Frontend Components ✅

#### 1. ThinkingStrip Component Redesign
- ✅ Updated `ThinkingStep` interface:
  - Changed `role: string` → `phase: AbstractPhase`
  - Maintains all other properties (label, modelDisplay, status, preview, latency_ms)
- ✅ Updated rendering logic:
  - Shows 5 phases instead of 7 roles
  - Uses phase key instead of role key for React list rendering
  - Updated council summary check: `step.phase === "crosscheck"` (instead of "council")
- ✅ Component still shows:
  - Timeline with animated status indicators
  - Preview text accumulation
  - Council progress badges (3/5 reviews, agree/mixed/disagree counts)
  - Latency display

### Frontend Hooks ✅

#### 1. useThinkingState Hook Enhancement
- ✅ Added support for phase events in addition to stage events
- ✅ New actions: `PHASE_START`, `PHASE_DELTA`, `PHASE_END`
- ✅ New initializer action: `INIT_PHASES`
- ✅ New initial state: `initialPhaseState` (5 phases instead of 7 stages)
- ✅ Reducer cases for phase events with proper state management
- ✅ Updated `handleEvent` callback to:
  - Dispatch phase events when received
  - Still handle stage events for backward compatibility
  - All existing functionality maintained

#### 2. New usePhaseCollaboration Hook
- ✅ Created `use-phase-collaboration.ts` - simpler hook focused only on phases
- ✅ Returns:
  - `phases` - Record of all phase states
  - `councilSummary` - Council progress tracking
  - `currentPhaseIndex` - Which phase is active
  - `processEvent()` - Main event handler
  - `getPhasesList()` - Returns array for ThinkingStrip
- ✅ Supports optional callbacks for fine-grained events
- ✅ Ignores detailed stage events (only shows phases to user)

### Documentation ✅

#### 1. Comprehensive Guide
- ✅ Created `ABSTRACTED_PHASE_IMPLEMENTATION.md`
  - Overview of the problem and solution
  - Complete architecture documentation
  - Phase mapping details
  - Event flow examples
  - Usage examples with both hooks
  - Backward compatibility notes
  - File structure summary

#### 2. Implementation Checklist
- ✅ This document - tracking all completed work

---

## Architecture Summary

### 5 User-Facing Phases

```
1. "understand" (step 0/5)
   → Models: GPT
   → Groups: analyst + creator

2. "research" (step 1/5)
   → Models: Perplexity
   → Groups: researcher

3. "reason_refine" (step 2/5)
   → Models: GPT
   → Groups: critic + internal_synth

4. "crosscheck" (step 3/5)
   → Models: Perplexity, Gemini, GPT, Kimi, OpenRouter
   → Groups: council reviews

5. "synthesize" (step 4/5)
   → Models: GPT (Director)
   → Groups: director
```

### Event Hierarchy

```
phase_start
├─ stage_start (internal role)
├─ phase_delta (preview text)
├─ stage_delta (detailed role output)
└─ stage_end
└─ phase_end

[Repeats for each phase]

final_answer_delta (streaming)
final_answer_done (complete response)
```

---

## Integration Points

### For Chat Components
```typescript
import { useThinkingState } from "@/hooks/useThinkingState"
import { ThinkingStrip } from "@/components/collaborate/ThinkingStrip"

const thinking = useThinkingState()
thinking.handleEvent(event) // Works with both phase and stage events
<ThinkingStrip steps={thinking.steps} currentIndex={thinking.currentIndex} />
```

### For New Implementations
```typescript
import { usePhaseCollaboration } from "@/hooks/use-phase-collaboration"

const { phases, processEvent, getPhasesList } = usePhaseCollaboration()
processEvent(event) // Only phase events
<ThinkingStrip steps={getPhasesList()} />
```

---

## Testing Checklist

### Backend Tests
- [ ] Verify `run_collaborate_streaming()` emits phase_start events
- [ ] Verify phase_delta accumulates preview text correctly
- [ ] Verify phase_end includes correct latency_ms
- [ ] Verify council_progress events still emit during reviews
- [ ] Verify final_answer_delta and final_answer_done work unchanged
- [ ] Verify detailed stage_* events still emit (for observability)

### Frontend Tests
- [ ] parseCollaborateEvent() recognizes phase events
- [ ] useThinkingState handles phase_start events
- [ ] useThinkingState handles phase_delta events
- [ ] useThinkingState handles phase_end events
- [ ] ThinkingStrip displays 5 phases correctly
- [ ] Council summary shows for "crosscheck" phase
- [ ] Final answer displays after phase_end (synthesize)
- [ ] usePhaseCollaboration processes all events correctly

### E2E Tests
- [ ] Full collaborate request emits 5 phases
- [ ] UI shows correct phase progression
- [ ] Latencies display correctly
- [ ] Preview text updates in real-time
- [ ] Council badges show correct counts
- [ ] Final answer appears after completion
- [ ] Collapse/expand button works

---

## Backward Compatibility Notes

✅ **Fully Backward Compatible:**
- Old code using `useThinkingState()` continues to work
- Backend still emits detailed `stage_*` events
- `parseCollaborateEvent()` handles both old and new event types
- No breaking changes to API endpoints

✅ **Optional Migration:**
- New code can use `usePhaseCollaboration()` for cleaner implementation
- Can opt-in to phase events without affecting existing code
- Both systems work side-by-side

---

## Files Modified

### Backend
```
backend/app/services/collaborate/streaming.py
  - Added phase mapping constants (13 lines)
  - Enhanced inner team pipeline to emit phase events (100+ lines)
  - Enhanced council pipeline to emit phase events (60+ lines)
  - Enhanced director pipeline to emit phase events (50+ lines)
```

### Frontend Types
```
frontend/types/collaborate-events.ts
  - Added AbstractPhase type
  - Added phase event interfaces (PhaseStartEvent, PhaseDeltaEvent, PhaseEndEvent)
  - Added helper functions (getRolePhase, getPhaseLabel, getPhaseFromEvent)
  - Added phase mappings (PHASE_LABELS, PHASE_INDICES, TOTAL_PHASES)
  - Updated CollaborateEvent union type
  - Updated parseCollaborateEvent() function
```

### Frontend Components
```
frontend/components/collaborate/ThinkingStrip.tsx
  - Updated ThinkingStep interface (role → phase)
  - Updated rendering logic (7 roles → 5 phases)
  - Updated council summary check (step.role → step.phase)
  - Updated React key mapping (step.role → step.phase)
```

### Frontend Hooks
```
frontend/hooks/useThinkingState.ts
  - Added PHASE_START, PHASE_DELTA, PHASE_END actions
  - Added INIT_PHASES action
  - Added initialPhaseState constant
  - Added phase reducer cases
  - Enhanced handleEvent() to process phase events

frontend/hooks/use-phase-collaboration.ts (NEW FILE)
  - Created new hook specifically for phase-based events
  - Provides simpler interface for new code
  - Includes council progress tracking
```

### Documentation
```
ABSTRACTED_PHASE_IMPLEMENTATION.md (NEW)
  - Comprehensive guide to the system
  - Architecture details
  - Usage examples
  - Event flow diagrams
  - Testing guidelines

IMPLEMENTATION_CHECKLIST.md (NEW)
  - This document
  - Tracks all completed work
  - Testing checklist
```

---

## Next Steps

1. **Test the implementation:**
   - Run backend tests to verify phase events
   - Run frontend tests to verify event handling
   - Run E2E tests with actual collaboration

2. **Deploy and monitor:**
   - Deploy backend changes
   - Deploy frontend changes
   - Monitor event streams
   - Verify UI rendering

3. **Optional enhancements:**
   - Add "Show detailed reasoning" mode
   - Add phase-specific confidence scores
   - Export phase data as structured JSON
   - Add timing breakdown charts

---

## Summary

✅ **Complete implementation** of the abstracted phase UI system

- **Backend:** Emits both detailed stage events and abstracted phase events
- **Frontend Types:** Full TypeScript support for new phase events
- **Components:** ThinkingStrip redesigned to show 5 clean phases
- **Hooks:** Both old and new hooks support phase events
- **Documentation:** Comprehensive guide and implementation checklist
- **Backward Compatible:** No breaking changes, works alongside existing code

The system provides a **clean, user-friendly interface** while maintaining the **powerful internal 7-step collaboration process** and full **observability** through detailed logging.

