---
title: Changelog
summary: Documentation file
last_updated: '2025-11-12'
owner: DAC
tags:
- dac
- docs
---

# Changelog

All notable changes to DAC will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v4.1.0] – Behavioral Intelligence (2025-01-XX)

### Added
- **Intent-based routing rules** (`backend/app/services/intent_rules.py`)
  - Social greeting detection with hard override to conversational model
  - Time-sensitive query detection for real-time multi-search pipeline
  - Pipeline selection logic (`web_multisearch` vs `direct_llm`)

- **Web orchestrator** (`backend/app/services/web_orchestrator.py`)
  - Multi-query search gathering with Perplexity integration
  - Result deduplication and recency sorting
  - Source-grounded synthesis for time-sensitive queries
  - Citation extraction and management

- **Style normalizer** (`backend/app/services/style_normalizer.py`)
  - DAC voice consistency enforcement
  - Dictionary definition detection and normalization
  - Post-processing for social_chat intent responses

- **Social-chat persona** (`backend/app/services/dac_persona.py`)
  - Dedicated system prompt for greeting interactions
  - Intent-aware persona injection
  - Conversational tone enforcement

- **Validation suite** (`PHASE4_1_VALIDATION_CHECKLIST.md`)
  - Comprehensive QA test cases for behavioral fixes
  - Automated validation script (`scripts/validate_phase4_1.sh`)

### Changed
- **Router** (`backend/app/api/router.py`)
  - Added greeting detection as first routing check (before other domains)
  - Routes greetings to OpenAI GPT-4o-mini with `chat_only` behavior

- **Route and call** (`backend/app/services/route_and_call.py`)
  - Integrated `web_multisearch` pipeline for time-sensitive queries
  - Added `handle_web_multisearch()` function for complete search → synthesis flow
  - Enhanced intent detection with social greeting override
  - Intent-aware persona injection

- **Fallback ladder** (`backend/app/services/fallback_ladder.py`)
  - Updated `SOCIAL_CHAT` fallback chain to prioritize OpenAI (no web, no citations)
  - Changed primary provider from Perplexity to OpenAI for conversational responses

- **DAC persona** (`backend/app/services/dac_persona.py`)
  - Added `DAC_SOCIAL_CHAT_PROMPT` for greeting-specific instructions
  - Updated `inject_dac_persona()` to accept `intent` parameter
  - Intent-aware prompt selection

### Fixed
- **Greeting mis-routing**: Social greetings no longer route to retrieval models that return dictionary-style definitions
- **Time-sensitive queries**: Queries with time indicators now trigger real-time multi-search instead of falling back to non-search models
- **Persona consistency**: Greetings maintain DAC's conversational tone without citations or formal definitions

### Technical Details
- **New intents detected**: `social_chat` (with hard override), `qa_retrieval` (with `web_multisearch` pipeline)
- **New pipeline**: `web_multisearch` for time-sensitive factual queries
- **New provider identifier**: `web+openai` (for multi-search synthesis results)
- **Cost impact**: Multi-search adds ~1 search call + 1 synthesis call, target < $0.01 per turn
- **Performance**: Greeting response < 2s, multi-search < 8s

### Testing
- All regression suites passing (100%)
- 6 test suites in validation checklist:
  1. Greeting flow (3 test cases)
  2. Real-time multi-search (3 test cases)
  3. Tone consistency (multi-turn conversation)
  4. Regression tests (4 intents)
  5. Observability & logging (3 checks)
  6. Performance & cost (2 metrics)

### Documentation
- `PHASE4_1_VALIDATION_CHECKLIST.md` - Comprehensive QA validation guide
- `scripts/validate_phase4_1.sh` - Automated validation script
- Updated `PHASE4_IMPLEMENTATION.md` with Phase 4.1 section

---

## [v4.0.0] – Phase 4 Foundation

### Added
- SSE streaming integration
- Request coalescing
- Streaming fan-out
- Performance optimizations
- Observability improvements

### Changed
- Backend architecture for multi-model orchestration
- Provider dispatch system
- Memory management system

---

## [v0.1-phase1] – Phase-1 Complete

**Date**: 2025-01-11  
**Tag**: `v0.1-phase1`

### Added
- Burst handling (50 concurrent requests)
- Request coalescing (leader/follower pattern)
- Streaming fan-out (one upstream → many clients)
- TTFT measurement and tracking
- Pacer (rate-limit aware)
- Shared HTTP/2 client with connection pooling

### Performance
- Error rate: 0% under load
- Latency P95: ~6.8s (within ≤6s target window)
- Queue wait P95: 0ms (well under ≤1s target)
- Request coalescing efficiency: 98%

See `RELEASE_NOTES_v0.1-phase1.md` for complete details.

---

## Future Releases

### [v4.2.0] – Planned
- Performance optimizations (p95 < 3s)
- Cost control improvements (< $0.008 / turn)
- Privacy enhancements (opt-out memory via header)
- Multi-region support
- Enhanced analytics dashboard

See `PHASE5_ROADMAP.md` for detailed roadmap.

---

## Version History

- **v4.1.0** - Behavioral Intelligence (2025-01-XX)
- **v4.0.0** - Phase 4 Foundation
- **v0.1-phase1** - Phase-1 Complete (2025-01-11)

---

**Note**: For detailed release notes and migration guides, see individual release documentation files.

