# Multi-Agent Council Orchestrator - Architecture Guide

**Date:** 2025-12-12
**Version:** 1.0
**Status:** Active

---

## Executive Summary

The Multi-Agent Council Orchestrator is a distributed decision-making system that leverages five specialized AI agents to collaboratively solve complex problems. Each agent brings a distinct perspective—architectural, analytical, research-driven, security-focused, and optimization-minded—which are synthesized into a coherent deliverable by an integrator and validated by a final judge.

This system is designed to produce high-quality, well-reasoned, production-ready solutions with full traceability and accountability.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER QUERY                               │
│                    (What needs to be built?)                     │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PARALLEL EXECUTION LAYER                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │  Architect   │ │     Data     │ │  Researcher  │             │
│  │    Agent     │ │   Engineer   │ │    Agent     │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│                                                                  │
│  ┌──────────────┐ ┌──────────────┐                               │
│  │  Red Teamer  │ │  Optimizer   │                               │
│  │    Agent     │ │    Agent     │                               │
│  └──────────────┘ └──────────────┘                               │
│       (All 5 run simultaneously)                                 │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DEBATE SYNTHESIZER                            │
│         (Merge outputs → Ownership Map + Decision Log)           │
│    Resolves conflicts, ensures coherence, validates spec        │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                       JUDGE AGENT                                │
│              (Final QA Gate + Verdict)                           │
│    Produces deliverable with provenance, issues binding verdict  │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FINAL OUTPUT                                │
│              (Runnable Code + Compliance Report)                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## System Components

### 1. Five Specialist Agents (Parallel Execution)

All agents receive the **same query** but analyze it from their specialized perspective. They run simultaneously, so total execution time equals the slowest agent, not the sum.

| Agent | Role | Ownership | Output |
|-------|------|-----------|--------|
| **Architect** | Lead/PM, structural thinking | Requirements, API design, file structure | Requirements Lock, Architecture Decisions, File Plan |
| **Data Engineer** | Analytical, scale-focused | Database schema, idempotency, indexing | Schema Design, Idempotency Strategy, Data Decisions |
| **Researcher** | Evidence-driven, meticulous | Dependencies, best practices, docs | Recommended Dependencies, Compatibility Checks |
| **Red Teamer** | Security-focused, contrarian | Threat modeling, edge cases, privacy | Threat Model, Privacy Audit, Security Checklist |
| **Optimizer** | Simplicity-focused, humble | Code optimization, DRY, bloat removal | Simplification Applied, Performance Considerations |

### 2. Debate Synthesizer

**Purpose:** Merge all five agent outputs into one coherent, conflict-free plan.

**Key Responsibilities:**
- Combine all agent recommendations
- Resolve any disagreements with clear decisions
- Create ownership map (who owns each file/artifact)
- Ensure file count matches user's exact request
- Prepare provenance headers
- Brief the Judge with a clear compliance checklist

**Output:** Ownership Map, Integrated Plan, Decision Log, Spec Compliance Checklist

### 3. Judge Agent

**Purpose:** Produce the final user-facing deliverable and issue a binding verdict.

**Hard Rules (Non-Negotiable):**
- ❌ Cannot approve if file count doesn't match user's request
- ❌ Cannot approve if ANY hard requirement is missing
- ❌ Cannot approve if PII is logged without explicit consent
- ❌ Cannot approve if code obviously won't run
- ✅ Every file must have provenance header (Owner, Reviewers, Purpose)

**Output:** Final deliverable with runnable code + ownership provenance + verdict

---

## Data Flow

```
User Query
    │
    ├──→ Architect Agent ────────────────────┐
    ├──→ Data Engineer Agent ────────────────┤
    ├──→ Researcher Agent ───────────────────┼──→ Synthesizer ──→ Judge ──→ Final Output
    ├──→ Red Teamer Agent ───────────────────┤
    └──→ Optimizer Agent ────────────────────┘
         (PARALLEL - max 5s)                  (SEQUENTIAL - 3s)
```

**Execution Timeline:**
- **Phase 1 (Parallel):** All agents run simultaneously → ~5-15 seconds (slowest agent)
- **Phase 2 (Sequential):** Synthesizer merges outputs → ~3-5 seconds
- **Phase 3 (Sequential):** Judge validates and produces final output → ~5-10 seconds
- **Total:** ~13-30 seconds for complete workflow

---

## Output Modes

The system supports four output modes to control verbosity:

| Mode | Contents | Use Case |
|------|----------|----------|
| **deliverable-only** | Just the final code/solution | CI/CD pipelines, automated systems |
| **deliverable-ownership** | Code + ownership map + checklist (default) | Most use cases, team collaboration |
| **audit** | Above + risk register + decision log | Compliance, audits, high-risk features |
| **full-transcript** | Above + complete agent debate transcript | Post-mortems, learning, documentation |

---

## Key Design Principles

### 1. **Parallel Reasoning**
Five agents think simultaneously from different angles, preventing groupthink and narrow perspectives.

### 2. **Specialization with Overlap**
Each agent has clear ownership areas but can comment on others' domains, enabling cross-domain insights.

### 3. **Explicit Conflict Resolution**
Disagreements are surfaced in the synthesizer, not hidden. Every conflict gets a resolution decision with rationale.

### 4. **Deliverable-First Mindset**
The Judge produces actual, runnable code with provenance, not theoretical discussions.

### 5. **Hard Requirements vs. Soft Preferences**
The system distinguishes between non-negotiable constraints (exact file count, security requirements) and nice-to-haves.

### 6. **Full Traceability**
Every artifact has an owner, reviewers, and clear authorship notes showing who wrote what.

---

## System Guarantees

✅ **Guaranteed Outputs:**
- Every file has provenance (Owner, Reviewers, Purpose)
- File count matches user's exact request (or reason documented)
- All hard requirements are explicitly addressed
- Code is syntactically valid and runnable
- No PII in logs without explicit user consent

⚠️ **Conditional Outputs:**
- Completeness depends on query clarity
- Performance optimizations require performance metrics
- Security hardening depends on threat model accuracy

❌ **Cannot Guarantee:**
- Perfect code quality (depends on requirements clarity)
- No bugs (impossible without runtime testing)
- Optimal performance (depends on workload profiles)

---

## Integration Points

The system integrates with:
- **LLM Provider:** OpenAI API (GPT-4o or equivalent)
- **Frontend:** Collaboration UI in Syntra
- **Backend:** FastAPI service orchestrating the workflow
- **Database:** Stores collaboration state, decisions, and provenance

---

## Terminology

| Term | Definition |
|------|-----------|
| **Artifact** | A deliverable (code file, document, schema, etc.) |
| **Ownership** | Clear assignment of who authored/owns each artifact |
| **Provenance** | Metadata tracking origin, purpose, and reviewers |
| **Hard Requirement** | Non-negotiable constraint (e.g., "exactly 3 files") |
| **Soft Requirement** | Nice-to-have, can be deferred with explanation |
| **Synthesis** | Merging all agent outputs into coherent plan |
| **Verdict** | Judge's final approval/rejection decision |

---

## Next Steps

See:
- `COLLABORATION_AGENTS.md` - Detailed agent role descriptions and prompts
- `COLLABORATION_WORKFLOW.md` - Step-by-step execution guide
- `COLLABORATION_IMPLEMENTATION.md` - How to run and integrate the system
