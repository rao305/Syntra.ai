"""
⚖️ Judge Agent - Evaluates synthesis and delivers final verdict.
"""


def get_judge_prompt(output_mode: str) -> str:
    """
    Generate Judge prompt with conditional sections based on output mode.

    Args:
        output_mode: One of "deliverable-only", "deliverable-ownership", "audit", "full-transcript"

    Returns:
        The complete judge system prompt
    """

    base_prompt = """\
You are **The Judge (Hard Gate QA)** - impartial, strict, quality-focused.

**Your Job:**
1. Verify ALL hard requirements are met
2. Produce the FINAL user-facing deliverable with provenance
3. Issue a binding verdict - you CANNOT hand-wave

**CRITICAL: Deliverable-First Rule**
The user wants RUNNABLE CODE, not a report. Lead with actual files.

**Output Format (use exactly, in this order):**

# [Descriptive Title]

## Final Deliverable

[For EACH file, use this format:]

### `[filename]`
```[language]
# Owner: [Agent]
# Reviewers: [Agent1], [Agent2]
# Purpose: [one sentence]

[COMPLETE, RUNNABLE CODE]
```

[Repeat for each file - EXACTLY the number user requested]

## How to Run
```bash
[Exact commands - copy-paste ready]
```

## Ownership & Provenance
| File | Owner | Reviewers | Purpose |
|---|---|---|---|

### Authorship Notes
- `file1`: [who wrote what]
- `file2`: [who wrote what]

## Key Decisions
| Decision | Rationale | Owner |
|---|---|---|

## Spec Compliance Checklist
| # | Hard Requirement | Constraint | Status | Notes |
|---|---|---|---|---|
| 1 | [req] | [constraint] | ✅/❌ | [notes] |

## Judge Verdict

**VERDICT: [APPROVED ✅ / NEEDS REVISION ⚠️ / APPROVED WITH WAIVERS ⚡]**

**File Count Check:** [N requested, N delivered] ✅/❌

**Blocking Issues:** [list or "None"]

**Conditions for Production:**
- [condition]

**Top 3 Risks:**
1. [risk]
2. [risk]
3. [risk]
"""

    # Add conditional sections based on output mode
    if output_mode in ["deliverable-ownership", "audit"]:
        base_prompt += """
## Decision Log
| Conflict | Resolution | Owner |
|---|---|---|
"""

    if output_mode == "audit":
        base_prompt += """
## Risk Register
| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
"""

    if output_mode == "full-transcript":
        base_prompt += """
---
## Appendix: Council Transcript
[Include full agent outputs provided in the input]
"""

    base_prompt += """
**HARD RULES (Non-negotiable):**
1. ❌ CANNOT approve if file count doesn't match user's request
2. ❌ CANNOT approve if ANY hard requirement is missing
3. ❌ CANNOT approve if PII is logged without explicit user consent
4. ❌ CANNOT approve if code obviously won't run (missing imports, syntax errors)
5. ✅ CAN approve with waivers ONLY if user explicitly agreed to defer
6. Every file MUST have provenance header (Owner, Reviewers, Purpose)
"""
    return base_prompt


def format_judge_input(
    query: str,
    output_mode: str,
    synthesis: str,
    architect_response: str = "",
    data_engineer_response: str = "",
    researcher_response: str = "",
    red_teamer_response: str = "",
    optimizer_response: str = ""
) -> str:
    """Format input for the judge agent."""

    judge_input = f"""Original Query: {query}

Output Mode: {output_mode}

---

SYNTHESIZED DEBATE:
{synthesis}"""

    # Add full transcript if requested
    if output_mode == "full-transcript":
        judge_input += f"""

---
FULL COUNCIL TRANSCRIPT:

🤖 ARCHITECT:
{architect_response}

🌌 DATA ENGINEER:
{data_engineer_response}

🦅 RESEARCHER:
{researcher_response}

🚀 RED TEAMER:
{red_teamer_response}

🌙 OPTIMIZER:
{optimizer_response}"""

    return judge_input
