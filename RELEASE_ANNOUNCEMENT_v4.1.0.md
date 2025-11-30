# DAC v4.1.0 Release Announcement

**Date**: 2025-01-XX  
**Version**: v4.1.0 "Behavioral Intelligence"  
**Status**: 🚀 Live

---

## 🎉 What's New

DAC v4.1.0 is now live with two major behavioral improvements:

### 1. Natural Greetings
Greetings now feel natural and conversational. No more dictionary-style definitions when you say "hi" or "hello"!

**What changed**:
- Greetings route to conversational model (OpenAI GPT-4o-mini)
- No citations or formal definitions
- Warm, friendly responses with optional follow-up questions

### 2. Real-Time Multi-Search
Time-sensitive queries now get real-time, multi-source summaries.

**What changed**:
- Queries with time indicators (e.g., "two days ago", "this week") trigger web multi-search
- Aggregated summaries from multiple sources
- Bulleted format with dates and citations

**Example**: "what happened in delhi two days ago" → Multi-source summary with recent events

---

## 📊 Monitoring

**Dashboard**: [Grafana Link]  
**Alert Flag**: `DAC_SSE_V2`  
**Roll-back**: See `PHASE4_INCIDENT_RUNBOOK.md`

**Key Metrics to Watch**:
- p95 latency < 5s ✅
- Fallback rate < 5% ✅
- Cache hit rate > 30% ✅
- Cost per turn < $0.01 ✅

---

## 🔍 Observability

New intents and pipelines are now tracked:
- `social_chat` - Conversational greetings
- `qa_retrieval:web_multisearch` - Time-sensitive queries with multi-search
- Provider: `web+openai` - Multi-search synthesis results

Check Grafana for:
- Intent distribution
- Pipeline usage (`direct_llm` vs `web_multisearch`)
- Provider breakdown

---

## 📚 Documentation

- **Release Notes**: `CHANGELOG.md`
- **Validation**: `PHASE4_1_VALIDATION_CHECKLIST.md`
- **Release Summary**: `PHASE4_1_RELEASE_SUMMARY.md`
- **Implementation**: `PHASE4_IMPLEMENTATION.md` (Phase 4.1 section)

---

## 🐛 Issues?

If you notice any issues:
1. Check Grafana dashboard for error rates
2. Review logs for intent/pipeline mismatches
3. Set roll-back flag if needed: `DAC_SSE_V2=false`
4. See `PHASE4_INCIDENT_RUNBOOK.md` for detailed procedures

---

## 🎯 What's Next

After 24 hours of stable operation, Phase 5 optimization cycle begins:
- Performance: p95 < 3s
- Cost: < $0.008 / turn
- Privacy: opt-out memory
- Scale: multi-region support

See `PHASE5_ROADMAP.md` for details.

---

**Release Manager**: [Your Name]  
**Git Tag**: `v4.1.0`  
**Commit**: `[commit hash]`

---

**End of Announcement**









