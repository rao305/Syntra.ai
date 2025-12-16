# Syntra SuperBenchmark Collaboration System Implementation

## Overview

This document describes the implementation of the Syntra SuperBenchmark Collaboration System Prompt (V1), which governs all stages of the multi-agent council orchestration.

## Key Features Implemented

### 1. Base System Prompt (`base_system_prompt.py`)

The canonical system prompt that governs ALL stages:
- **Non-Negotiable Principles**: Final answers must be executable, hard constraints beat helpfulness, structured state, quality gating, no pipeline leakage
- **Canonical State Blocks**: Context Pack, Lexicon Lock, Output Contract
- **Stage Responsibilities**: Clear roles for Specialists, Critic/Red Team, Council/Judge, Synthesizer/Director
- **Hard Quality Gates**: 5 gates (A-E) that must pass before final output
- **Provenance & Transparency**: Optional transparency mode for showing internal stages

### 2. Context Pack Builder

The `build_context_pack()` function creates a canonical context pack (max 250 tokens) that includes:
- Goal
- Locked decisions
- Glossary / Lexicon Lock
- Open questions
- Output contract (required headings, file counts, format constraints)
- Style rules

### 3. Prompt Injection

The `inject_base_prompt()` function combines:
1. Base system prompt (always included)
2. Context pack (if provided)
3. Transparency mode note (if enabled)
4. Agent-specific prompt (role details)

This ensures all agents receive the same foundational rules while maintaining their specific roles.

### 4. Quality Gates (`quality_gates.py`)

Five hard quality gates implemented:

#### Gate A: Greeting/Persona Gate
- Prevents greeting unless user greeted first
- Checks for common greetings in output vs user message

#### Gate B: Lexicon Gate
- Enforces forbidden terms (must not appear)
- Can enforce allowed terms (if strict lock)
- Uses word boundary matching to avoid partial matches

#### Gate C: Output Contract Gate
- Validates required headings exist
- Checks file count matches exactly
- Validates format constraints

#### Gate D: Completeness Gate (Domain-Agnostic)
- Requires clear structure (headings)
- Requires concrete steps/actions
- Checks for duplicated sections
- Validates explicit assumptions and risks

#### Gate E: Domain Completeness Gate
- Detects domain (incident management, code deliverable, etc.)
- Validates domain-specific requirements
- Example: Incident management requires severity criteria, escalation, comms templates, roles/RACI

### 5. API Integration

Updated `CouncilRequest` model to accept:
- `context_pack`: Dict with locked_decisions, glossary, open_questions, style_rules
- `lexicon_lock`: Dict with 'allowed_terms' and/or 'forbidden_terms'
- `output_contract`: Dict with required_headings, file_count, format
- `transparency_mode`: Boolean to enable transparency

### 6. Orchestrator Integration

Updated `CouncilOrchestrator` to:
- Build context pack from config at start
- Inject base prompt into all agent calls (specialists, synthesizer, judge)
- Pass context pack and lexicon lock through all stages
- Support transparency mode

## Usage Example

```python
from app.services.council import CouncilOrchestrator, CouncilConfig
from app.services.council.config import OutputMode

config = CouncilConfig(
    query="Design an incident severity framework with P1, P2, P3 only",
    output_mode=OutputMode.DELIVERABLE_OWNERSHIP,
    api_keys={"openai": "key", "gemini": "key"},
    context_pack={
        "locked_decisions": ["Only P1, P2, P3 severities", "Only roles: IC, Comms Lead, On-call Engineer"],
        "open_questions": ["What are the MTTA targets?"]
    },
    lexicon_lock={
        "forbidden_terms": ["P0", "SEV0", "Scribe", "Incident Liaison"],
        "allowed_terms": ["P1", "P2", "P3", "IC", "Comms Lead", "On-call Engineer", "Eng Manager", "Support"]
    },
    output_contract={
        "required_headings": ["AGENT OUTPUTS", "SYNTHESIZED FINAL", "JUDGE CHECK"],
        "file_count": None  # Not applicable for this query
    },
    transparency_mode=False
)

orchestrator = CouncilOrchestrator()
result = await orchestrator.run(config)
```

## API Request Example

```json
{
  "query": "Design an incident severity framework...",
  "output_mode": "deliverable-ownership",
  "context_pack": {
    "locked_decisions": ["Only P1, P2, P3 severities"],
    "open_questions": ["What are the MTTA targets?"]
  },
  "lexicon_lock": {
    "forbidden_terms": ["P0", "SEV0"],
    "allowed_terms": ["P1", "P2", "P3"]
  },
  "output_contract": {
    "required_headings": ["AGENT OUTPUTS", "SYNTHESIZED FINAL"],
    "file_count": null
  },
  "transparency_mode": false
}
```

## Quality Gate Validation

The quality gates can be run independently:

```python
from app.services.council.quality_gates import validate_all_gates

all_passed, violations = validate_all_gates(
    output=final_output,
    user_message=query,
    lexicon_lock=lexicon_lock,
    output_contract=output_contract
)

if not all_passed:
    print("Quality gate violations:")
    for violation in violations:
        print(f"  - {violation}")
```

## Files Modified/Created

1. **Created**: `backend/app/services/council/base_system_prompt.py`
   - Base system prompt
   - Context pack builder
   - Prompt injection function

2. **Created**: `backend/app/services/council/quality_gates.py`
   - All 5 quality gates (A-E)
   - Validation function

3. **Modified**: `backend/app/services/council/orchestrator.py`
   - Added context pack building
   - Added prompt injection to all agents
   - Added new config fields

4. **Modified**: `backend/app/api/council.py`
   - Added new request fields
   - Updated async runner to pass new params

## Next Steps (Future Enhancements)

1. **Automatic Quality Gate Enforcement**: Integrate quality gates into judge agent to automatically repair failing outputs
2. **Repair Logic**: Implement automatic repair when gates fail (rewrite to satisfy gates without changing meaning)
3. **Fallback Mechanism**: Add fallback to strongest model if repair fails
4. **Audit Trail**: Store quality gate results in database for analysis
5. **Cost Tracking**: Track tokens/cost per agent for optimization

## Testing

To test the implementation:

1. Send a request with lexicon_lock containing forbidden terms
2. Verify output doesn't contain forbidden terms
3. Send a request with output_contract requiring specific headings
4. Verify output contains required headings
5. Enable transparency_mode and verify transparency header appears

## Notes

- The base system prompt is injected into ALL agent calls, ensuring consistent behavior
- Context pack is limited to ~250 tokens to stay within limits
- Quality gates are currently informational - automatic enforcement can be added later
- Transparency mode is opt-in and only shows minimal metadata (not full prompts)

