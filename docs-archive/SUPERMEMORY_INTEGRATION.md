# Supermemory Integration Guide

This document describes how Supermemory is integrated into the DAC system for long-term memory capabilities.

## Overview

Supermemory provides a long-term memory layer that allows the DAC assistant to:
- Automatically save important information to memory
- Search previous memories to answer follow-up questions
- Work across different LLM providers

## Setup

### 1. Environment Variables

Add the following to your `.env.local` file:

```bash
SUPERMEMORY_API_KEY=your_supermemory_api_key_here
```

**Important**: Do NOT hardcode the API key in source code.

### 2. Install Dependencies

The required packages are already in `package.json`:
- `ai` - Vercel AI SDK
- `@ai-sdk/openai` - OpenAI provider for Vercel AI SDK
- `@supermemory/tools` - Supermemory tools integration

Install with:
```bash
npm install
```

## Architecture

### Integration Points

1. **Configuration** (`src/config.ts`)
   - Exports `SUPERMEMORY_API_KEY` from environment variables
   - Warns if the key is missing (graceful degradation)

2. **Supermemory Helper** (`src/integrations/supermemory.ts`)
   - `getSupermemoryTools()` - Returns Supermemory tools instance
   - `isSupermemoryAvailable()` - Checks if Supermemory is configured

3. **OpenAI Provider** (`src/router/providers/OpenAIProvider.ts`)
   - Uses Vercel AI SDK's `generateText` with Supermemory tools
   - Automatically includes tools when Supermemory is available
   - Logs tool calls for debugging

4. **System Prompt** (`src/config.ts`)
   - Updated `DAC_SYSTEM_PROMPT` includes guidance on using Supermemory tools
   - Instructs the model to use `addMemory` and `searchMemories` appropriately

5. **Chat Route** (`src/api/chat.ts`)
   - Passes `sessionId` and `userId` to the LLM router
   - These are used by Supermemory to aggregate memories per user/session

## How It Works

### Memory Heuristics

The DAC system prompt includes detailed heuristics for when to use Supermemory tools:

#### When to CALL searchMemories

**MUST call when:**
- User asks about their identity or preferences ("What is my name?", "What language do I like?")
- User asks about ongoing projects or decisions ("What did we decide about [project]?")
- User asks about past information ("Remind me of [something]")

**SHOULD call when:**
- User refers to something from a previous session
- Question references past decisions, plans, or summaries
- User mentions ongoing projects, preferences, or goals

#### When to CALL addMemory

**MUST call when:**
- User explicitly requests storage ("Remember that...", "Please remember...")
- User provides stable, long-term information:
  - Identity: name, pronouns, role, school, company
  - Preferences: languages, tools, frameworks, UI themes
  - Long-term projects: architecture decisions, tech stack choices

**SHOULD call when:**
- Information is clearly meant to persist
- Information is stable and unlikely to change soon
- Storing it will improve future conversation quality

**Do NOT store:**
- Temporary or trivial facts ("I'm eating a sandwich")
- Highly sensitive data (passwords, API keys, exact addresses)
- Noisy or log-like content

### Memory Storage Example

When a user says:
- "My name is Alice and I love TypeScript. Please remember that."

The model will:
1. Detect explicit storage request ("Please remember")
2. Identify stable information (name, language preference)
3. Call the `addMemory` tool via Supermemory
4. Store structured summary: "User: Alice, Preferences: TypeScript"
5. Acknowledge storage to user

### Memory Retrieval Example

When a user asks:
- "What is my name and what language do I like?"

The model will:
1. Detect question about stored user information
2. Call `searchMemories` with query: "user name and preferences"
3. Retrieve relevant memories
4. Use memories to answer: "Your name is Alice and you love TypeScript."
5. Answer naturally without exposing tool usage

### Session/User Context

The system uses:
- `sessionId` - Stable across requests for the same conversation
- `userId` - Optional, for cross-session memory aggregation

These are passed from the chat route through the LLM router to the provider, ensuring Supermemory can properly scope memories.

## Testing

### Manual Test Script

1. **Start a chat and store information:**
   ```bash
   curl -X POST http://localhost:3000/api/chat \
     -H "Content-Type: application/json" \
     -d '{
       "sessionId": "test-session-1",
       "userId": "test-user-1",
       "message": "My name is Alice and I love TypeScript. Please remember that.",
       "provider": "openai"
     }'
   ```

   **Expected behavior:**
   - The model should acknowledge the request
   - Check server logs for: `[OpenAIProvider] Tool calls made: 1`
   - The tool call should be `addMemory`

2. **Ask a follow-up question:**
   ```bash
   curl -X POST http://localhost:3000/api/chat \
     -H "Content-Type: application/json" \
     -d '{
       "sessionId": "test-session-1",
       "userId": "test-user-1",
       "message": "What is my name and what language do I like?",
       "provider": "openai"
     }'
   ```

   **Expected behavior:**
   - The model should answer: "Your name is Alice and you love TypeScript."
   - Check server logs for: `[OpenAIProvider] Tool calls made: 1`
   - The tool call should be `searchMemories`

### Verification

To verify Supermemory is working:

1. **Check server logs** for tool call messages:
   ```
   [OpenAIProvider] Tool calls made: 1
     Tool 1: addMemory
   ```

2. **Check the response** - The assistant should correctly recall stored information

3. **Test across sessions** - Use the same `userId` but different `sessionId` to test cross-session memory

## Troubleshooting

### Supermemory Not Working

1. **Check API Key:**
   - Verify `SUPERMEMORY_API_KEY` is set in `.env.local`
   - Restart the server after adding the key

2. **Check Logs:**
   - Look for: `⚠️  SUPERMEMORY_API_KEY is not set`
   - Look for: `Supermemory tools not available:`

3. **Verify Package Installation:**
   ```bash
   npm list @supermemory/tools ai @ai-sdk/openai
   ```

### Tool Calls Not Happening

1. **Check System Prompt:**
   - The system prompt includes guidance on using Supermemory tools
   - The model should automatically use tools when appropriate

2. **Check Model Capabilities:**
   - Ensure the model supports tool calling (GPT-4, GPT-4o, etc.)
   - Some models may not support tools

3. **Enable Debug Logging:**
   - Tool calls are logged automatically
   - Check server console for `[OpenAIProvider] Tool calls made:`

## Future Enhancements

- [ ] Support for streaming responses with `streamText`
- [ ] Integration with other providers (Anthropic, Gemini)
- [ ] Memory management UI
- [ ] Memory search and retrieval analytics

## Notes

- Supermemory is an **additive** feature - it doesn't replace ContextManager or EntityResolver
- The system gracefully degrades if Supermemory is not configured
- Tool calls are logged for debugging but not exposed to the user
- Session and user IDs should be stable across requests for best results

