# Collaborative Memory Integration - DAC System Prompt

## Overview

The DAC system prompt has been updated to incorporate principles from the **Collaborative Memory paper**, addressing the "John Smith" problem where models might use irrelevant or cross-user memory without proper access control and ambiguity handling.

## Key Principles Integrated

### 1. **Two-Tier Memory Model**

The system now explicitly distinguishes between:
- **PRIVATE memory**: User-specific, scoped by `userId` via Supermemory `containerTags`
- **SHARED memory**: Generalized, anonymized knowledge (conceptual - Supermemory currently implements single-tier with userId scoping)

### 2. **Read Policy (Access Control)**

- All retrieved memory fragments are treated as **already access-controlled**
- Model must NOT infer or reference hidden/redacted data
- Model must NOT mention internal metadata (IDs, containerTags)
- If multiple entities match (e.g., multiple "John Smith"), model must ask for disambiguation

### 3. **Write Policy (Memory Storage)**

**PRIVATE memories** (default):
- User-specific information (preferences, goals, personal context)
- Format: Concise, standalone summary
- Example: "User is Alex, studies computer science at Purdue, prefers TypeScript and dark mode."

**SHARED memories** (for general knowledge):
- Remove user-specific details (names, emails, IDs)
- Generalize personal examples into anonymized patterns
- Format: Comprehensive, user-agnostic explanation
- Example: "A student at a large public university prefers TypeScript for web development."

### 4. **Ambiguity & Pronouns (Critical)**

- **MUST NOT guess** when multiple entities match
- **MUST ask clarifying questions** for ambiguous references
- Only auto-resolve when exactly ONE entity matches
- Examples:
  - ❌ BAD: User mentions Obama & Biden, asks "What was he doing in 2008?" → model guesses
  - ✅ GOOD: "Just to clarify, are you asking about Barack Obama or Joe Biden?"

### 5. **User Boundary & Privacy**

- Never reveal information came from another user's private memory
- Never mention other users/tenants/accounts explicitly
- When using shared memory, speak generically: "In previous interactions, similar users have..."
- If information is outside allowed scope, say you don't have it (don't speculate)

### 6. **Tool Usage Priorities**

1. **Current conversation** (short-term history)
2. **Retrieved memory** (already access-controlled via searchMemories)
3. **Other tools** (web search, etc.) - still respecting ambiguity/privacy rules

## Implementation Details

### System Prompt Location
- **File**: `src/config.ts`
- **Variable**: `DAC_SYSTEM_PROMPT`
- **Used by**: All LLM providers via `OpenAIProvider`, `AnthropicProvider`, etc.

### Supermemory Integration
- **File**: `src/integrations/supermemory.ts`
- **Scoping**: Uses `userId` as `containerTag` for private memory isolation
- **Tools**: `addMemory` and `searchMemories` (provided by `@supermemory/tools/ai-sdk`)

### Test Coverage
- ✅ All 8/8 QA tests pass
- ✅ Ambiguity handling (Obama/Biden) works correctly
- ✅ Cross-session memory recall works
- ✅ User boundary enforcement in place

## Key Sections in Updated Prompt

1. **HIGH-LEVEL RULES**: Access control assumptions
2. **TWO-TIER MEMORY MODEL**: Private vs shared distinction
3. **AMBIGUITY & PRONOUNS**: No guessing policy
4. **USER-BOUNDARY & PRIVACY**: Cross-user isolation
5. **TOOL USAGE & ANSWER PRIORITIES**: Conversation → Memory → Other tools
6. **OUTPUT REQUIREMENTS**: What to expose/not expose
7. **QA-MODE**: Strict test requirements (preserved from original)

## Benefits

1. **Prevents "John Smith" problem**: Model won't use irrelevant cross-user memory
2. **Enforces ambiguity handling**: No silent guessing when multiple entities match
3. **Respects access control**: Treats retrieved memories as already filtered
4. **Maintains privacy**: Never reveals other users' information
5. **Structured memory storage**: Clear guidance on private vs shared formatting

## Future Enhancements

If Supermemory adds native support for two-tier memory (private vs shared containers), we can:
- Use separate `containerTags` for private vs shared memories
- Add dedicated system prompts for `addMemory` tool calls (as suggested in the paper)
- Implement explicit key-value formatting in tool descriptions

For now, the system prompt enforces the principles at the model level, which is sufficient for the current Supermemory implementation.

