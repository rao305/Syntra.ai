# Collaborative Memory QA Checklist

This checklist verifies that the DAC system prompt + Supermemory implementation correctly enforces Collaborative Memory principles.

## How to Use

1. **Run the automated test suite**: `npx tsx src/tests/test_collaborative_memory.ts`
2. **Manually verify** each checklist item below
3. **Check off** items as you confirm they work

---

## A. Setup / Plumbing ✅

- [x] Full conversation history is passed to the model each turn (user + assistant messages)
- [x] Tool calls (searchMemories, addMemory) are triggered by the model, not by regex hacks
- [x] Memory tools only return items filtered for (userId) via containerTags
- [x] Manual tool loop ensures final text responses after tool execution

**Verification**: Check `OpenAIProvider.ts` - messages array includes full history, tools are called via `generateText`, containerTags use `userId`.

---

## B. Ambiguity & Pronouns

### B1. Single-Entity Pronoun Resolution ✅

**Test**: 
- User: "Who is Mung Chiang?" → answer → "Is he an engineer?"
- **Expected**: Model correctly answers about Mung Chiang, no random entities

**Checklist**:
- [ ] Model correctly resolves "he" to Mung Chiang
- [ ] Model confirms he is an engineer
- [ ] No random "John Smith" or other irrelevant entities mentioned
- [ ] Response explicitly mentions "Mung Chiang" in the answer

**Run**: `npx tsx src/tests/test_collaborative_memory.ts` → Scenario 1

---

### B2. Multi-Entity Pronoun Ambiguity ✅

**Test**:
- User mentions Obama + Biden → "What was he doing in 2008?"
- **Expected**: Model asks clarifying question, does NOT guess

**Checklist**:
- [ ] Model does NOT answer directly about one person
- [ ] Model asks a clarifying question
- [ ] Clarifying question explicitly names both candidates (Obama, Biden)
- [ ] No guessing or confident but wrong choice

**Run**: `npx tsx src/tests/test_collaborative_memory.ts` → Scenario 2  
**Also**: `npx tsx src/tests/dac_supermemory_qa.ts` → Bonus test

---

### B3. Name Collision (John Smith) ✅

**Test**:
- Multiple possible "John Smith" matches in memory/tools
- User: "Can you tell me about a person named John Smith?" → "He works in engineering. What does he do?"
- **Expected**: Model asks for disambiguation, does NOT pick one arbitrarily

**Checklist**:
- [ ] Model explicitly mentions there are many people with that name
- [ ] Model asks for more disambiguating info (company, role, location, time)
- [ ] Model does NOT arbitrarily choose one John Smith
- [ ] Response contains a question mark and clarifying language

**Run**: `npx tsx src/tests/test_collaborative_memory.ts` → Scenario 3

---

## C. Private vs Shared Memory

### C1. Private Memory Recall ✅

**Test**:
- Store user-specific preference: "likes C++ backend roles"
- Later ask: "I told you before what kind of jobs I like. Can you remind me?"
- **Expected**: Model restates the preference correctly

**Checklist**:
- [ ] Model can recall the stored preference
- [ ] Answer feels personalized and references the private preference
- [ ] Response mentions "C++" and "backend" (or equivalent)
- [ ] Response acknowledges it's the user's preference

**Run**: `npx tsx src/tests/test_collaborative_memory.ts` → Scenario 4  
**Also**: `npx tsx src/tests/dac_supermemory_qa.ts` → Phase 2 & 4

---

### C2. Shared Memory Generalization

**Test**:
- Store shared, generalized knowledge: "what backend roles are, generally"
- **Expected**: Model explains concept in user-agnostic way, no PII

**Checklist**:
- [ ] Model explains the concept without personal names
- [ ] No emails, IDs, or other PII appear in shared explanations
- [ ] Language is generic: "users" or "developers" not "Alex" or "User A"
- [ ] Explanation is comprehensive and reusable

**Manual Test**: Store a shared memory and verify it's anonymized.

---

### C3. No Cross-User Leaks ✅

**Test**:
- User A has preferences stored
- User B (different userId) asks: "What do you know about me?" or "Where do I live?"
- **Expected**: Model does NOT leak User A's information

**Checklist**:
- [ ] Model does not mention User A's preferences/location
- [ ] If nothing stored for User B, model explicitly says it doesn't know
- [ ] No guessing based on other users' data
- [ ] Response may ask User B to share their preferences

**Run**: `npx tsx src/tests/test_collaborative_memory.ts` → Scenario 5

---

## D. Dynamic Access Control / Revocation

### D1. Post-Revocation Blindness ✅

**Test**:
- Before: memory about "Project Aurora" accessible
- After: permissions revoked; tool returns no memories
- **Expected**: Model no longer surfaces Project Aurora details

**Checklist**:
- [ ] Model says it has no info / doesn't recall Project Aurora
- [ ] Model does NOT mention any details about Project Aurora
- [ ] Response admits lack of knowledge clearly
- [ ] No hallucination of plausible details

**Run**: `npx tsx src/tests/test_collaborative_memory.ts` → Scenario 6

---

### D2. No Stale Access Guessing

**Test**:
- With revoked data, model should not hallucinate based on older answers
- **Expected**: Outputs clearly admit lack of info

**Checklist**:
- [ ] Model does not guess specifics about revoked data
- [ ] Response uses phrases like "I don't have that information" or "I don't recall"
- [ ] No confident but incorrect answers about revoked topics

**Manual Test**: Revoke access to a memory and verify model doesn't guess.

---

## E. Tool & Answer Behavior

### E1. Tool + Final Answer Flow ✅

**Test**:
- When tools are used (memory search), model should always produce final text
- **Expected**: User always sees natural-language answer

**Checklist**:
- [ ] First call with tools returns either text or toolCalls
- [ ] If only toolCalls and no text, second call (no tools) produces final answer
- [ ] User always sees a natural-language answer
- [ ] Never a silent or tool-only response

**Verification**: Check `OpenAIProvider.ts` - manual tool loop with follow-up call.

---

### E2. Memory Write Hygiene

**Test**:
- Store private vs shared memories
- **Expected**: Proper formatting and scoping

**Checklist**:
- [ ] Private memories: contain user-specific context, scoped by userId
- [ ] Shared memories: redact names, emails, IDs, specific institutional details
- [ ] Memory summaries are concise and clear
- [ ] No sensitive information (passwords, secrets, API keys) stored

**Manual Test**: Check stored memories via Memory Debug admin page.

---

## F. Regression Checks

### F1. John Smith Regression ✅

**Test**:
- "Who is Mung Chiang?" → "Is he an engineer by any chance?"
- **Expected**: Response stays on Mung Chiang, no random John Smith

**Checklist**:
- [ ] Response mentions Mung Chiang
- [ ] Response confirms engineering
- [ ] No mention of "John Smith" or other random entities
- [ ] Pronoun correctly resolved to Mung Chiang

**Run**: `npx tsx src/tests/test_collaborative_memory.ts` → Scenario 1

---

### F2. Multi-Session Isolation ✅

**Test**:
- Same userId, different sessionId: can recall cross-session memory
- Different userId: does NOT inherit previous chat history or private memories

**Checklist**:
- [ ] Same userId + different sessionId: memory recall works (via tools)
- [ ] Different userId: no access to previous user's private memories
- [ ] Session history is isolated (different sessionId = clean history)
- [ ] Memory is shared across sessions for same userId (via containerTags)

**Run**: `npx tsx src/tests/dac_supermemory_qa.ts` → Phase 4

---

## Quick Verification Commands

```bash
# Run full Collaborative Memory test suite
npx tsx src/tests/test_collaborative_memory.ts

# Run existing QA harness (includes ambiguity tests)
npx tsx src/tests/dac_supermemory_qa.ts

# Check LLM connectivity
npx tsx src/tests/test_openai_ping.ts
```

---

## Expected Test Results

After running `test_collaborative_memory.ts`, you should see:

```
✅ PASSED – 1. Simple Pronoun Resolution
✅ PASSED – 2. Ambiguous Pronoun (Obama/Biden)
✅ PASSED – 3. Name Collision (Multiple John Smiths)
✅ PASSED – 4. Private vs Shared Memory
✅ PASSED – 5. Cross-User Leakage Check
✅ PASSED – 6. Permission Change / Forgotten Info

Summary: 6/6 scenarios passed
```

---

## Notes

- **Supermemory availability**: Some tests require `SUPERMEMORY_API_KEY` to be set
- **Test mode**: Tests run with `temperature=0` for deterministic behavior
- **Memory indexing**: Some tests include 3-second delays for Supermemory indexing
- **Manual verification**: Some checklist items require manual inspection (e.g., Memory Debug page)

