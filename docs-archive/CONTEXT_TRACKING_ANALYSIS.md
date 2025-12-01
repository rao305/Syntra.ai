# Context Tracking System Analysis & Recommendations

## Problem Identified

User conversation shows context loss:
```
User: "tell me about umich"
AI: [Detailed response about University of Michigan]
User: "what is that colleges rank for computer science"
AI: "Which college? I need to know the specific college..."
```

**Expected behavior:** AI should understand "that college" = "University of Michigan" from previous message.

## Root Cause

Your query rewriter system is **DISABLED** by default:
- `FEATURE_COREWRITE = bool(int(os.getenv("FEATURE_COREWRITE", "0")))`
- File: `backend/app/api/threads.py:704`

## Existing System (Already Built!)

You have a comprehensive context tracking system in place:

### 1. **Query Rewriter** (`app/services/query_rewriter.py`)
- ✅ Detects pronouns: "it", "that", "this", "they", "that university", "that college"
- ✅ Resolves pronouns to entities using conversation history
- ✅ Handles multi-word patterns: "that college" → "University of Michigan"
- ✅ Generates disambiguation questions when ambiguous

### 2. **Topic Extractor** (`app/services/topic_extractor.py`)
- ✅ Extracts named entities: Universities, Companies, Products
- ✅ Tracks when entities were last mentioned
- ✅ Regex patterns for common entities

### 3. **Disambiguation Assistant** (`app/services/disambiguation_assistant.py`)
- ✅ Generates clarification questions with options
- ✅ Handles ambiguous references

## Why It Failed in Your Example

1. **Feature disabled** → Query rewriter never ran
2. **Topic extraction needs improvement** for:
   - Abbreviations: "UMich", "U-M", "UM"
   - Informal names: "that college", "the university"
   - Typos: "colleges" instead of "college"

## Recommended Solution

### Phase 1: Enable Existing System ✨
```bash
# Add to backend/.env
FEATURE_COREWRITE=1
```

### Phase 2: Enhance Topic Extraction
Add university abbreviation patterns:
- "UMich" → "University of Michigan"
- "MIT" → "Massachusetts Institute of Technology"
- Handle informal references

### Phase 3: Add Cross-Provider Context Persistence
Your system already has:
- In-memory thread storage (`memory_manager.py`)
- Turn-by-turn context tracking
- Topic extraction per turn

**Missing:** Explicit entity tracking across provider switches:
```python
thread_context = {
    "last_university": "University of Michigan",
    "last_company": None,
    "last_product": None,
    "conversation_topics": ["University of Michigan", "computer science", "rankings"]
}
```

### Phase 4: Smart Context Injection
When query rewriter detects a pronoun:
1. Check recent topics (last 5 messages)
2. Find matching entity type (university, company, etc.)
3. Rewrite query before routing to provider
4. Provider sees: "what is University of Michigan's rank for computer science"
   Instead of: "what is that colleges rank for computer science"

## Implementation Priority

### 🚀 **Immediate** (5 minutes)
1. Enable FEATURE_COREWRITE
2. Test with your example

### 📈 **Short-term** (30 minutes)
1. Add university abbreviation patterns
2. Improve typo tolerance ("colleges" → "college")
3. Add common university nicknames

### 🎯 **Medium-term** (2 hours)
1. Add explicit entity tracking per thread
2. Improve disambiguation UI
3. Add "Did you mean X?" suggestions

### 🔮 **Long-term** (Future)
1. Use LLM for entity extraction (more accurate)
2. Cross-session context persistence
3. User preference learning

## Quick Test

After enabling FEATURE_COREWRITE, test with:
```bash
# Message 1
curl -X POST http://localhost:8000/api/threads/{thread_id}/messages/stream \
  -H "x-org-id: org_demo" \
  -d '{"content":"tell me about Stanford University","user_id":"test"}'

# Message 2 (should resolve "that school")
curl -X POST http://localhost:8000/api/threads/{thread_id}/messages/stream \
  -H "x-org-id: org_demo" \
  -d '{"content":"what is that schools computer science ranking","user_id":"test"}'
```

Expected: Query rewriter should detect "that school" and rewrite to "what is Stanford University's computer science ranking"

## Architecture Overview

```
User Message: "what is that colleges rank"
       ↓
[Query Rewriter] → Detects "that college"
       ↓
[Topic Extractor] → Finds "University of Michigan" in recent context
       ↓
[Pronoun Resolver] → Replaces "that college" with "University of Michigan"
       ↓
Rewritten: "what is University of Michigan's rank for computer science"
       ↓
[Router] → Sends to Perplexity (factual question)
       ↓
Response with full context!
```

## Key Files

- Query Rewriter: `backend/app/services/query_rewriter.py`
- Topic Extractor: `backend/app/services/topic_extractor.py`
- Disambiguation: `backend/app/services/disambiguation_assistant.py`
- Integration: `backend/app/api/threads.py:704-776`

## Notes

- System is well-designed but needs to be enabled
- Consider adding "UMich" pattern for common abbreviations
- Your disambiguation UI integration is already built (lines 743-762)
