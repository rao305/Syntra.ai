# Multi-Agent Council - Workflow & Execution Guide

**Date:** 2025-12-12
**Version:** 1.0
**Status:** Active

---

## Overview

The Multi-Agent Council workflow is a three-phase process:

1. **Phase 1 (PARALLEL):** Five specialist agents analyze the query simultaneously
2. **Phase 2 (SEQUENTIAL):** Debate Synthesizer merges outputs into coherent plan
3. **Phase 3 (SEQUENTIAL):** Judge Agent validates and produces final deliverable

**Total Execution Time:** ~13-30 seconds

---

## Phase 1: Parallel Agent Execution

### Timeline
- **Start:** All five agents receive the same query
- **Duration:** ~5-15 seconds (time of slowest agent)
- **End:** All agents complete and return their outputs

### Agents Involved
1. Architect Agent (🤖)
2. Data Engineer Agent (🌌)
3. Researcher Agent (🦅)
4. Red Teamer Agent (🚀)
5. Optimizer Agent (🌙)

### Process

```python
# Pseudo-code: Phase 1 execution
async def phase_1_parallel_agents(query: str):
    architect_task = run_agent(ARCHITECT_PROMPT, query)
    data_eng_task = run_agent(DATA_ENGINEER_PROMPT, query)
    researcher_task = run_agent(RESEARCHER_PROMPT, query)
    red_team_task = run_agent(RED_TEAMER_PROMPT, query)
    optimizer_task = run_agent(OPTIMIZER_PROMPT, query)

    # Run all simultaneously, wait for all to complete
    results = await asyncio.gather(
        architect_task,
        data_eng_task,
        researcher_task,
        red_team_task,
        optimizer_task
    )

    return {
        "architect": results[0],
        "data_engineer": results[1],
        "researcher": results[2],
        "red_teamer": results[3],
        "optimizer": results[4],
    }
```

### Input to Each Agent

**Agent System Prompt:** Role-specific instructions (see `COLLABORATION_AGENTS.md`)

**User Message:** The original query, e.g.,
```
Create a production-ready Python FastAPI microservice that exposes
POST /v1/leads to ingest lead events and GET /health for readiness,
persisting data to SQLite via SQLAlchemy with idempotency using an
Idempotency-Key header, and include a minimal OpenAPI description and
structured JSON logging. Output exactly three files—app/main.py, app/db.py,
and README.md—with runnable code and clear local run instructions.
```

### Output from Each Agent

Each agent produces structured output (see formats in `COLLABORATION_AGENTS.md`):

**Architect Output Example:**
```
## 🤖 Architect Output

### Requirements Lock
| # | Requirement | Type | Constraint | Status |
|---|---|---|---|---|
| 1 | POST /v1/leads endpoint | Hard | Must ingest events | Addressed |
| 2 | GET /health endpoint | Hard | Readiness check | Addressed |
| 3 | Exactly 3 files | Hard | app/main.py, app/db.py, README.md | Addressed |

### Architecture Decisions
- **Decision:** Single-file FastAPI app with SQLAlchemy ORM
  - **Why:** Lightweight, idiomatic, clear concerns
  - **Tradeoff:** Monolithic vs. microservices

### File Plan (Exact)
| File | Purpose | Owner |
|---|---|---|
| app/main.py | FastAPI app, endpoints | Architect |
| app/db.py | SQLAlchemy models, DB setup | Data Engineer |
| README.md | Setup, run instructions | Researcher |

### Needs From Other Agents
- **Data Engineer:** Confirm idempotency strategy fits in db.py
- **Red Teamer:** Validate API endpoint security
```

**Data Engineer Output Example:**
```
## 🌌 Data Engineer Output

### Schema Design
```sql
CREATE TABLE leads (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    phone TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE idempotency_keys (
    idempotency_key TEXT PRIMARY KEY,
    lead_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);
```

### Idempotency Strategy
- **Mechanism:** Request header `Idempotency-Key` + database lookup
- **Key storage:** `idempotency_keys` table
- **TTL:** 24 hours

### Needs From Other Agents
- **Architect:** Confirm file structure fits (app/db.py)
- **Optimizer:** Suggest indexing optimizations
```

**Researcher Output Example:**
```
## 🦅 Researcher Output

### Recommended Dependencies
| Package | Version | Why |
|---|---|---|
| fastapi | 0.104.1 | Standard async API framework |
| sqlalchemy | 2.0.23 | ORM best practice |
| pydantic | 2.5.0 | Data validation standard |

### Best Practices Applied
- **Practice:** Request validation via Pydantic models
  - **Implementation:** Define Pydantic model for lead schema
- **Practice:** Structured JSON logging
  - **Implementation:** Use stdlib json for log formatting
- **Practice:** Idempotency header (Idempotency-Key)
  - **Implementation:** Accept header, store in database

### Compatibility Checks
| Item | Status |
|---|---|
| Python 3.9+ | ✅ Supported |
| FastAPI 0.104 | ✅ Latest |

### Needs From Other Agents
- **Architect:** Confirm README.md file ownership
- **Red Teamer:** Validate security of all dependencies
```

**Red Teamer Output Example:**
```
## 🚀 Red Teamer Output

### Threat Model
| Threat | Mitigation | Status |
|---|---|---|
| Idempotency key collision | UUID4 + DB unique constraint | ✅ Mitigated |
| Replay attacks | Idempotency-Key header + 24h TTL | ✅ Mitigated |
| SQL injection | Parameterized queries via SQLAlchemy | ✅ Mitigated |

### Privacy & Logging Audit
| Data Type | Logged? | Risk | Action |
|---|---|---|---|
| PII (email, phone, name) | ❌ Never | High | Log only IDs, never raw PII |
| Idempotency keys | ✅ Truncated | Low | Log first 8 chars for debugging |

### Security Checklist
- [x] Input validation: Pydantic models
- [x] No PII in logs: Email/phone never logged
- [x] Safe error messages: Generic to client, detailed in logs
- [x] SQL injection: Parameterized queries

### Needs From Other Agents
- **Architect:** Confirm error handling approach
- **Data Engineer:** Validate idempotency TTL logic
```

**Optimizer Output Example:**
```
## 🌙 Optimizer Output

### Simplification Applied
| Before | After | Benefit |
|---|---|---|
| 50-line custom idempotency class | 8-line dict lookup + DB insert | Simpler, fewer bugs |
| Multiple error handler decorators | Single FastAPI exception handler | Less boilerplate |

### Code Quality Decisions
- **Decision:** Use Pydantic for request/response validation
  - **Why:** Framework-native, less code
  - **Lines saved:** ~30

### Performance Considerations
| Operation | Complexity | Optimization |
|---|---|---|
| Lead insertion | O(1) | Direct INSERT, no loops |
| Idempotency lookup | O(log N) | Index on idempotency_key |

### Needs From Other Agents
- **Architect:** Confirm file count (exactly 3) — no extras
- **Data Engineer:** Validate simplicity of idempotency logic
```

### Phase 1 Completion Criteria
✅ All five agents have returned outputs
✅ Each output follows its format specification
✅ All "Needs From Other Agents" questions are collected

---

## Phase 2: Debate Synthesizer

### Timeline
- **Start:** Receives all five agent outputs
- **Duration:** ~3-5 seconds
- **End:** Returns integrated plan with Ownership Map and Decision Log

### Purpose
Merge all five agent perspectives into ONE coherent, conflict-free plan that:
- Combines all recommendations
- Resolves disagreements explicitly
- Ensures file count matches user's exact request
- Creates provenance headers for each file
- Briefs the Judge with a clear checklist

### Process

```python
# Pseudo-code: Phase 2 synthesizer
async def phase_2_synthesizer(query: str, phase1_results: dict):
    synthesizer_input = f"""
Original Query: {query}

---

🤖 ARCHITECT'S ANALYSIS:
{phase1_results["architect"]}

---

🌌 DATA ENGINEER'S ANALYSIS:
{phase1_results["data_engineer"]}

---

🦅 RESEARCHER'S ANALYSIS:
{phase1_results["researcher"]}

---

🚀 RED TEAMER'S ANALYSIS:
{phase1_results["red_teamer"]}

---

🌙 OPTIMIZER'S ANALYSIS:
{phase1_results["optimizer"]}
"""

    synthesis = await run_agent(
        SYNTHESIZER_PROMPT,
        synthesizer_input,
        max_tokens=3000
    )

    return synthesis
```

### Input to Synthesizer

**System Prompt:** Synthesizer role instructions (detailed below)

**User Message:** All five agent outputs concatenated with clear section headers

### Output Format

```
## Ownership Map (Final)
| Artifact | Owner | Reviewers | Purpose |
|---|---|---|---|
| app/main.py | Architect | Data Engineer, Red Teamer | FastAPI endpoints, request models |
| app/db.py | Data Engineer | Optimizer, Red Teamer | SQLAlchemy models, idempotency logic |
| README.md | Researcher | Architect, Optimizer | Setup, run instructions, API examples |

## Integrated Plan
[Merged approach from all agents — no contradictions]

## Provenance Headers (for each file)
```
# File: app/main.py
# Owner: Architect
# Reviewers: Data Engineer, Red Teamer
# Purpose: FastAPI app with POST /v1/leads and GET /health endpoints
```

## Decision Log
| Conflict | Options | Resolution | Owner |
|---|---|---|---|
| Idempotency: in-memory cache vs. database | A: Fast but non-durable; B: Persistent | **B (database).** Durability > speed for lead ingestion. | Synthesizer |

## Spec Compliance Checklist (Hard Requirements Only)
| # | Requirement | Constraint | Status | Owner |
|---|---|---|---|---|
| 1 | POST /v1/leads endpoint | Must ingest events | ✅ | Architect |
| 2 | GET /health endpoint | Readiness check | ✅ | Architect |
| 3 | SQLite persistence | Via SQLAlchemy | ✅ | Data Engineer |
| 4 | Idempotency support | Idempotency-Key header | ✅ | Data Engineer |
| 5 | OpenAPI documentation | Minimal spec | ✅ | Architect |
| 6 | Exactly 3 files | app/main.py, app/db.py, README.md | ✅ | Synthesizer |

## Brief for Judge
**File count check:** 3 files requested, 3 files planned ✅
**Hard requirements met:** Yes ✅
**Blocking issues:** None
**Top 3 risks:**
1. Idempotency key collision (mitigated by UUID4 + DB constraint)
2. SQLite concurrency under high load (mitigated by WAL mode)
3. PII in logs (mitigated by logging only IDs and truncated keys)
```

### Synthesizer Hard Rules

The Synthesizer **MUST:**
- ✅ Check file count: If user said "exactly 3 files", plan for exactly 3
- ✅ Resolve all conflicts: No ambiguity for the Judge
- ✅ Create Ownership Map: Every artifact has clear owner + reviewers
- ✅ Generate Provenance Headers: Owner, Reviewers, Purpose for each file
- ✅ Verify hard requirements: Every hard requirement addressed in Spec Compliance Checklist

### Phase 2 Completion Criteria
✅ Ownership Map is complete (all artifacts assigned)
✅ Provenance Headers are generated for each file
✅ All agent disagreements are resolved in Decision Log
✅ File count matches user's exact request
✅ Spec Compliance Checklist shows all hard requirements as ✅

---

## Phase 3: Judge Agent

### Timeline
- **Start:** Receives synthesized debate + optionally full transcript
- **Duration:** ~5-10 seconds
- **End:** Returns final deliverable with binding verdict

### Purpose
Produce the **final user-facing deliverable** and issue a **binding verdict**:
1. Verify ALL hard requirements are met
2. Produce actual RUNNABLE CODE with provenance
3. Issue verdict: APPROVED ✅ / NEEDS REVISION ⚠️ / APPROVED WITH WAIVERS ⚡

### Process

```python
# Pseudo-code: Phase 3 judge
async def phase_3_judge(query: str, synthesis: str, phase1_results: dict, output_mode: str):
    judge_input = f"""
Original Query: {query}

Output Mode: {output_mode}

---

SYNTHESIZED DEBATE:
{synthesis}"""

    # If full-transcript mode, include all agent outputs
    if output_mode == "full-transcript":
        judge_input += f"""

---
FULL COUNCIL TRANSCRIPT:

🤖 ARCHITECT:
{phase1_results["architect"]}

🌌 DATA ENGINEER:
{phase1_results["data_engineer"]}

... [etc for other agents]
"""

    final_output = await run_agent(
        get_judge_prompt(output_mode),
        judge_input,
        max_tokens=8000
    )

    return final_output
```

### Input to Judge

**System Prompt:** Judge role instructions with conditional sections based on output mode

**User Message:**
- Original query
- Output mode preference
- Synthesized debate output
- (If full-transcript mode): All five agent outputs

### Output Format

#### For All Modes (Deliverable-First)

```
# [Descriptive Title]

## Final Deliverable

### `app/main.py`
```python
# Owner: Architect
# Reviewers: Data Engineer, Red Teamer
# Purpose: FastAPI app with POST /v1/leads and GET /health endpoints

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import json
import logging
from datetime import datetime
import uuid

# ... [COMPLETE, RUNNABLE CODE] ...
```

### `app/db.py`
```python
# Owner: Data Engineer
# Reviewers: Optimizer, Red Teamer
# Purpose: SQLAlchemy models, database setup, idempotency logic

from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
# ... [COMPLETE, RUNNABLE CODE] ...
```

### `README.md`
```markdown
# Lead Ingestion Service

## Setup
...

## Running Locally
...
```

## How to Run
```bash
pip install fastapi sqlalchemy pydantic
python -m uvicorn app.main:app --reload
```

## Ownership & Provenance
| File | Owner | Reviewers | Purpose |
|---|---|---|---|
| app/main.py | Architect | Data Engineer, Red Teamer | FastAPI endpoints |
| app/db.py | Data Engineer | Optimizer, Red Teamer | Database layer |
| README.md | Researcher | Architect, Optimizer | Documentation |

## Key Decisions
| Decision | Rationale | Owner |
|---|---|---|
| Single FastAPI app | Lightweight, idiomatic | Architect |
| SQLAlchemy ORM | Industry standard, type-safe | Data Engineer |
| Pydantic validation | Framework-native, minimal code | Researcher |

## Spec Compliance Checklist
| # | Hard Requirement | Constraint | Status |
|---|---|---|---|
| 1 | POST /v1/leads endpoint | Must ingest events | ✅ |
| 2 | GET /health endpoint | Readiness check | ✅ |
| 3 | SQLite persistence | Via SQLAlchemy | ✅ |
| 4 | Idempotency support | Idempotency-Key header | ✅ |
| 5 | OpenAPI documentation | Minimal spec | ✅ |
| 6 | Exactly 3 files | app/main.py, app/db.py, README.md | ✅ |

## Judge Verdict

**VERDICT: APPROVED ✅**

**File Count Check:** 3 requested, 3 delivered ✅

**Blocking Issues:** None

**Top 3 Risks:**
1. Idempotency key collision (mitigated by UUID4 + DB constraint)
2. SQLite concurrency under high load (mitigated by WAL mode)
3. PII in logs (mitigated by only logging IDs, not personal data)
```

#### For "deliverable-ownership" Mode (Adds)
```
## Decision Log
| Conflict | Resolution | Owner |
|---|---|---|
| Idempotency: in-memory cache vs. database | Database (durability > speed) | Synthesizer |
```

#### For "audit" Mode (Adds)
```
## Risk Register
| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
| Idempotency key collision | Low | High | UUID4 + DB constraint | Data Engineer |
| Replay attacks | High | Medium | Idempotency-Key header + 24h TTL | Red Teamer |
| SQL injection | Low | High | Parameterized queries via SQLAlchemy | Red Teamer |
```

#### For "full-transcript" Mode (Adds)
```
---
## Appendix: Council Transcript

### 🤖 Architect's Full Analysis
[Complete architect output]

### 🌌 Data Engineer's Full Analysis
[Complete data engineer output]

... [etc for other agents] ...
```

### Judge Hard Rules (Non-Negotiable)

1. ❌ **CANNOT approve** if file count doesn't match user's request
2. ❌ **CANNOT approve** if ANY hard requirement is missing
3. ❌ **CANNOT approve** if PII is logged without explicit user consent
4. ❌ **CANNOT approve** if code obviously won't run (syntax errors, missing imports)
5. ✅ **CAN approve** with waivers ONLY if user explicitly agreed to defer items
6. ✅ Every file **MUST** have provenance header (Owner, Reviewers, Purpose)

### Judge Verdict Options

| Verdict | Meaning | When to Use |
|---------|---------|-------------|
| **APPROVED ✅** | All hard rules met, code is ready | No blocking issues |
| **NEEDS REVISION ⚠️** | One or more hard rules violated | Must be fixed before use |
| **APPROVED WITH WAIVERS ⚡** | Hard rules met, but user deferred some items | User explicitly accepted risk |

### Phase 3 Completion Criteria
✅ Final Deliverable section contains complete, runnable code
✅ Every file has provenance header (Owner, Reviewers, Purpose)
✅ Spec Compliance Checklist shows all hard requirements as ✅ or documented reason
✅ Judge Verdict is one of: APPROVED ✅, NEEDS REVISION ⚠️, APPROVED WITH WAIVERS ⚡
✅ Top 3 Risks are listed with mitigations

---

## Output Modes & Content

The user can request different output modes to control verbosity:

### 1. `deliverable-only`
**Contents:** Final Deliverable code only
**Use Case:** CI/CD pipelines, automated systems, minimal overhead

**What's Included:**
- Final Deliverable (code files with provenance headers)
- How to Run

### 2. `deliverable-ownership` (Default)
**Contents:** Code + ownership map + compliance checklist
**Use Case:** Most real-world scenarios, team collaboration

**What's Included:**
- Final Deliverable
- How to Run
- Ownership & Provenance
- Key Decisions
- Spec Compliance Checklist
- Judge Verdict

### 3. `audit`
**Contents:** Above + risk register + decision log
**Use Case:** Compliance audits, high-risk features, security-sensitive decisions

**What's Included:**
- Everything from deliverable-ownership
- Decision Log (how conflicts were resolved)
- Risk Register (threats, mitigations, ownership)

### 4. `full-transcript`
**Contents:** Above + complete agent debate transcript
**Use Case:** Post-mortems, learning, documentation, full transparency

**What's Included:**
- Everything from audit mode
- Appendix: Full output from all five agents
- Complete debate transcript for analysis

---

## Error Handling & Recovery

### If Phase 1 Agent Fails
- Retry the failing agent (exponential backoff)
- If still failing, synthesizer proceeds without that agent's output
- Judge notes missing agent in Verdict

### If Phase 2 Synthesizer Fails
- Retry the synthesizer
- Judge receives individual agent outputs + error log
- Judge must manually note unresolved conflicts

### If Phase 3 Judge Fails
- Return Phase 2 synthesis output + error message
- User can request retry or accept intermediate result

---

## Monitoring & Logging

Each phase should log:
- Start time, end time, duration
- Number of tokens consumed
- Any retries or errors
- Agent status (success/failure)

Example logging structure:
```json
{
  "workflow_id": "uuid",
  "timestamp": "2025-12-12T10:00:00Z",
  "phase": "1",
  "status": "success",
  "agents": {
    "architect": {"status": "success", "duration_ms": 2300, "tokens": 1200},
    "data_engineer": {"status": "success", "duration_ms": 2100, "tokens": 1150},
    "researcher": {"status": "success", "duration_ms": 1900, "tokens": 1100},
    "red_teamer": {"status": "success", "duration_ms": 2400, "tokens": 1300},
    "optimizer": {"status": "success", "duration_ms": 1800, "tokens": 950}
  },
  "max_duration_ms": 2400,
  "total_tokens": 5700
}
```

---

## Next Steps

- See `COLLABORATION_IMPLEMENTATION.md` for how to integrate with Syntra backend
- See `COLLABORATION_AGENTS.md` for detailed agent prompts and rules
