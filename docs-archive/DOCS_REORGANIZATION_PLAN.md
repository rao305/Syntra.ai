# Documentation Reorganization Plan

## Current State
- Found **250+ markdown files** across the project
- Many files in root directory
- Some files already in `/docs` with existing structure
- `CURSOR_PROMPTS/` directory with system prompts

## Proposed Structure

```
docs/
├── specs/                    # Specifications and invariants
│   ├── CONTEXT_INVARIANTS_SPEC.md
│   └── PROVIDER_ROUTING_SPEC.md (if exists)
│
├── onboarding/               # Contributor onboarding
│   └── CONTRIBUTOR_ONBOARDING.md
│
├── debugging/                # Debugging guides
│   └── CONTEXT_DEBUGGING_PLAYBOOK.md
│
├── architecture/             # Architecture documentation
│   ├── MEMORY_PIPELINE_ARCHITECTURE.md
│   └── LLM_CONTEXT_SYSTEM.md
│
├── tests/                    # Test documentation
│   ├── COMPLETE_TEST_SUITE.md
│   ├── REGRESSION_TESTS_COMPLETE.md
│   ├── E2E_API_TEST_COMPLETE.md
│   ├── BROWSER_TEST_RESULTS.md
│   ├── BROWSER_TEST_FINDINGS.md
│   ├── SANITY_TEST_FINDINGS.md
│   └── TEST_RESULTS_SUMMARY.md
│
├── implementation/           # Implementation guides and summaries
│   ├── THREAD_STORE_FIX_COMPLETE.md
│   ├── DEBUGGING_INSTRUMENTATION_COMPLETE.md
│   ├── ROBUST_CONTEXT_FIX.md
│   ├── ROBUST_CONTEXT_SOLUTION.md
│   ├── COMPLETE_SOLUTION_SUMMARY.md
│   ├── CENTRALIZED_CONTEXT_BUILDER.md
│   ├── CONVERSATION_CONTEXT_FIX.md
│   └── QUERY_REWRITER_IMPLEMENTATION.md
│
├── phases/                   # Phase-specific documentation
│   ├── PHASE1_*.md
│   ├── PHASE2_*.md
│   ├── PHASE3_*.md
│   ├── PHASE4_*.md
│   └── PHASE5_*.md
│
├── guides/                   # User and developer guides
│   ├── QUERY_REWRITER_INTEGRATION_GUIDE.md
│   ├── QUERY_REWRITER_DEMO_SCRIPTS.md
│   ├── CONTEXT_AWARENESS_GUIDE.md
│   ├── INTELLIGENT_ROUTING_GUIDE.md
│   └── PROVIDER_SWITCHING_GUIDE.md
│
├── reports/                  # Analysis and evaluation reports
│   ├── SUPERMEMORY_INTEGRATION_REPORT.md
│   ├── MODEL_OPTIMIZATION_REPORT.md
│   ├── MEMORY_MANAGEMENT_EVALUATION.md
│   └── PHASE2_QA_REPORT.md
│
└── cursor-prompts/          # Cursor system prompts
    ├── README.md
    ├── 1_MEMORY_PIPELINE_STRESS_TEST.md
    ├── 2_ASYNC_RACE_CONDITION_SIMULATOR.md
    ├── 3_PROVIDER_ROUTING_RELIABILITY_SPEC.md
    └── 4_LLM_EVALUATION_HARNESS.md
```

## Files to Move

### Root-level files to organize:
- Core specs → `docs/specs/`
- Onboarding → `docs/onboarding/`
- Debugging → `docs/debugging/`
- Architecture → `docs/architecture/`
- Tests → `docs/tests/`
- Implementation → `docs/implementation/`
- Phases → `docs/phases/`
- Guides → `docs/guides/`
- Reports → `docs/reports/`

### CURSOR_PROMPTS/ → `docs/cursor-prompts/`

## Files to Keep in Root
- `README.md` (main project readme)
- `CHANGELOG.md` (if it exists)
- `LICENSE` (not markdown, but important)

## Next Steps
1. Create directory structure
2. Move files to appropriate locations
3. Update any internal links
4. Create a docs index/README
5. Commit and push changes

