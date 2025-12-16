# SyntraEval - Golden Prompt Nightly Evaluator Implementation

## Overview

SyntraEval is an automated evaluation system for the multi-LLM collaboration system. It runs a fixed suite of "golden prompts" and generates shareable reports to help engineers improve:
- Stage prompts
- Routing logic
- Quality gates (validators)
- Repair/fallback policy

## Architecture

### Core Components

1. **SyntraEval** (`syntra_eval.py`): Main evaluator class
   - Evaluates tests against 5 quality gates (A-E)
   - Calculates scores (0-100)
   - Generates Markdown reports

2. **Quality Gates**:
   - **Gate A (Contract)**: Output contract validation (0-30 points)
   - **Gate B (Lexicon)**: Lexicon lock enforcement (0-20 points)
   - **Gate C (Safety)**: Safety/policy checks (0-5 points)
   - **Gate D (Domain)**: Domain completeness (0-15 points)
   - **Gate E (Quality)**: Clarity & actionability (0-30 points)

3. **API Endpoint** (`/api/eval/evaluate`): REST endpoint for running evaluations

## Usage

### API Request Example

```json
{
  "tests": [
    {
      "test_id": "test_001",
      "title": "Incident Severity Framework",
      "user_prompt": "Design an incident severity framework with ONLY severities P1, P2, P3...",
      "expected_output_contract": {
        "required_headings": ["AGENT OUTPUTS", "SYNTHESIZED FINAL", "JUDGE CHECK"],
        "file_count": null
      },
      "lexicon_lock": {
        "forbidden_terms": ["P0", "SEV0", "Scribe"],
        "allowed_terms": ["P1", "P2", "P3", "IC", "Comms Lead"]
      },
      "domain_checklist": [
        "measurable severity criteria",
        "escalation triggers",
        "comms templates",
        "roles/RACI"
      ],
      "priority": "P0"
    }
  ],
  "transcripts": [
    {
      "run_id": "run_001",
      "timestamp": "2024-01-15T10:30:00Z",
      "thread_id": "thread_abc123",
      "routing": {
        "architect": "openai/gpt-4o",
        "synthesizer": "openai/gpt-4o",
        "judge": "openai/gpt-4o"
      },
      "repair_attempts": 0,
      "fallback_used": false,
      "final_output": "# Incident Severity Framework\n\n## AGENT OUTPUTS\n...",
      "user_rating": 4
    }
  ],
  "run_metadata": {
    "date": "2024-01-15",
    "build_commit": "abc123def456",
    "environment": "production",
    "providers_enabled": ["openai", "gemini", "perplexity"],
    "notes": "Nightly evaluation run"
  },
  "prior_run": {
    "average_score": 85.5,
    "date": "2024-01-14"
  }
}
```

### Python Usage

```python
from app.services.eval import SyntraEval, GoldenTest, TestRunTranscript

# Create evaluator
evaluator = SyntraEval()

# Define test
test = GoldenTest(
    test_id="test_001",
    title="Incident Severity Framework",
    user_prompt="Design an incident severity framework...",
    expected_output_contract={
        "required_headings": ["AGENT OUTPUTS", "SYNTHESIZED FINAL"]
    },
    lexicon_lock={
        "forbidden_terms": ["P0", "SEV0"]
    },
    domain_checklist=["severity criteria", "escalation triggers"],
    priority="P0"
)

# Define transcript
transcript = TestRunTranscript(
    run_id="run_001",
    timestamp="2024-01-15T10:30:00Z",
    final_output="# Incident Severity Framework\n\n## AGENT OUTPUTS\n...",
    repair_attempts=0,
    fallback_used=False
)

# Evaluate
evaluation = evaluator.evaluate_test(test, transcript)

print(f"Total Score: {evaluation.total_score}/100")
print(f"Contract: {evaluation.gate_a_contract.result.value}")
print(f"Lexicon: {evaluation.gate_b_lexicon.result.value}")
```

## Report Format

The generated report includes:

1. **Run Metadata**: Date, build, environment, providers
2. **Executive Summary**: Pass rates, average score, repair/fallback rates
3. **Results Table**: All tests with gate results and scores
4. **Failures & Evidence**: Detailed failure analysis with quoted excerpts
5. **Trend Notes**: Comparison with prior runs (if provided)
6. **Action Plan**: Top 5 engineering fixes ranked by impact

## Scoring System

### Gate Score (0-70)
- Contract: 0-30 points
- Lexicon: 0-20 points
- Safety: 0-5 points
- Domain: 0-15 points

### Quality Score (0-30)
- Clarity: 0-10 points
- Specificity/measurability: 0-10 points
- Internal consistency: 0-10 points

### Total Score (0-100)
- **Caps applied**:
  - If Contract gate fails: max 49
  - If Safety gate fails: max 39

## Quality Gates Details

### Gate A: Output Contract
- Validates required headings exist
- Checks file count matches exactly
- Validates JSON schema if specified
- **Highest priority** - failure caps total score at 49

### Gate B: Lexicon Lock
- Checks for forbidden terms (word boundary matching)
- Optionally enforces allowed terms
- Returns N/A if no lexicon lock provided

### Gate C: Safety/Policy
- Detects API keys (OpenAI, Google patterns)
- Detects secrets (password, secret, api_key patterns)
- Detects sensitive system paths
- **Critical** - failure caps total score at 39

### Gate D: Domain Completeness
- Checks for required elements from domain_checklist
- Flexible keyword matching
- Returns N/A if no checklist provided

### Gate E: Quality (Scored)
- Checks structure (headings)
- Checks actionability (concrete steps)
- Detects vagueness (vague terms)
- Detects contradictions
- Detects repeated content

## Integration with CI/CD

### Nightly Evaluation Workflow

1. **Collect Test Results**: Run golden prompts through collaboration system
2. **Call Evaluation API**: POST to `/api/eval/evaluate` with tests and transcripts
3. **Store Report**: Save Markdown report to artifacts
4. **Alert on Regressions**: If pass rate drops below threshold, alert team
5. **Track Trends**: Compare with prior runs to identify improvements/regressions

### Example CI Script

```bash
#!/bin/bash
# Run nightly evaluation

# Collect test results (from your test harness)
python collect_test_results.py > test_results.json

# Call evaluation API
curl -X POST http://localhost:8000/api/eval/evaluate \
  -H "Content-Type: application/json" \
  -H "x-org-id: org_demo" \
  -d @test_results.json \
  > evaluation_report.json

# Extract report
jq -r '.report' evaluation_report.json > nightly_report.md

# Check for regressions
AVG_SCORE=$(jq '.summary.average_score' evaluation_report.json)
if (( $(echo "$AVG_SCORE < 80" | bc -l) )); then
  echo "WARNING: Average score below threshold: $AVG_SCORE"
  exit 1
fi
```

## Files Created

1. **`backend/app/services/eval/syntra_eval.py`**: Core evaluator implementation
2. **`backend/app/services/eval/__init__.py`**: Module exports
3. **`backend/app/api/eval.py`**: REST API endpoints
4. **`docs/implementation/SYNTRA_EVAL_IMPLEMENTATION.md`**: This documentation

## API Endpoints

### POST `/api/eval/evaluate`
Evaluate golden tests and generate report.

**Request Body**: `EvaluationRequest`
- `tests`: List of golden test cases
- `transcripts`: List of run transcripts (one per test)
- `run_metadata`: Run metadata (date, build, environment, etc.)
- `prior_run`: Optional prior run data for trends

**Response**: `EvaluationResponse`
- `report`: Markdown evaluation report
- `evaluations`: Detailed evaluation results
- `summary`: Summary statistics

### GET `/api/eval/health`
Health check endpoint.

## Future Enhancements

1. **Database Storage**: Store evaluation results in database for historical analysis
2. **Dashboard**: Web UI to view evaluation trends over time
3. **Automatic Repair Suggestions**: Generate code patches for common failures
4. **Provider Comparison**: Compare performance across different providers
5. **A/B Testing**: Compare different prompt versions side-by-side

## Notes

- SyntraEval does NOT generate production answers - it only evaluates existing outputs
- All gates are evidence-based - failures include quoted excerpts
- Missing data is marked as NOT_EVALUABLE rather than failing
- Reports are deterministic and reproducible

