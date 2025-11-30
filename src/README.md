# DAC Conversational Backend

Production-ready TypeScript backend for cross-LLM conversations with robust context handling and pronoun/entity resolution.

## Architecture

```
src/
├── types.ts                    # Core type definitions
├── config.ts                   # Configuration and system prompts
├── context/
│   ├── HistoryStore.ts        # Conversation history storage
│   ├── ContextManager.ts      # Context window management
│   └── EntityResolver.ts      # Pronoun/entity resolution micro-agent
├── router/
│   ├── LlmRouter.ts           # Provider routing
│   └── providers/
│       ├── OpenAIProvider.ts  # ✅ Full implementation
│       ├── AnthropicProvider.ts  # ⚠️ Stub
│       ├── GeminiProvider.ts     # ⚠️ Stub
│       └── PerplexityProvider.ts # ⚠️ Stub
└── api/
    ├── chat.ts                # Next.js route handler
    └── chat-express.ts        # Express.js route handler
```

## Features

- ✅ **Conversation History**: Rolling window per session
- ✅ **Entity Resolution**: Automatic pronoun/vague reference resolution
- ✅ **Context Management**: Single source of truth for LLM context
- ✅ **Cross-LLM Routing**: Extensible provider system
- ✅ **Production Ready**: Error handling, type safety, clean architecture

## Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure environment variables:**
   ```bash
   export OPENAI_API_KEY="sk-..."
   # Optional:
   export ANTHROPIC_API_KEY="..."
   export GEMINI_API_KEY="..."
   export PERPLEXITY_API_KEY="..."
   ```

3. **Build:**
   ```bash
   npm run build
   ```

## Usage

### Next.js App Router

```typescript
// app/api/chat/route.ts
export { POST } from '../../../src/api/chat';
```

### Express.js

```typescript
import express from 'express';
import { chatHandler } from './src/api/chat-express';

const app = express();
app.use(express.json());
app.post('/api/chat', chatHandler);
app.listen(3000);
```

### API Request

```json
POST /api/chat
{
  "sessionId": "user-123",
  "userId": "user-123",
  "message": "When was he born?",
  "provider": "openai"
}
```

### API Response

```json
{
  "answer": "Donald Trump was born on June 14, 1946.",
  "resolvedQuery": "When was Donald Trump born?",
  "entities": ["Donald Trump"],
  "providerUsed": "openai"
}
```

## Example Flow

1. **User:** "Who is Donald Trump?"
   - Stored in history
   - No resolution needed (explicit entity)

2. **User:** "When was he born?"
   - EntityResolver rewrites: "When was Donald Trump born?"
   - Entities extracted: ["Donald Trump"]
   - Context window includes previous turn
   - LLM receives resolved query

3. **Assistant:** "Donald Trump was born on June 14, 1946."
   - Stored in history
   - Response includes resolvedQuery and entities

## System Prompts

### Entity Resolver (Context Guard)
- Rewrites ambiguous queries using conversation history
- Outputs JSON: `{ resolvedQuery, entities }`
- Falls back to original message on error

### Main DAC Assistant
- Context-aware, prioritizes conversation history
- Resolves pronouns using recent entities
- Never switches to unrelated entities from search results

## Extending Providers

To add a new provider:

1. Create `src/router/providers/NewProvider.ts`:
   ```typescript
   export class NewProvider implements LlmProvider {
     async chat(args) {
       // Implementation
     }
   }
   ```

2. Register in `LlmRouter.ts`:
   ```typescript
   this.providers.set("newprovider", new NewProvider());
   ```

## Testing

Run the example conversation:
```bash
npm run test
```

Or use the example file directly:
```typescript
import { exampleConversation } from './src/examples/conversation-example';
exampleConversation();
```

## Future Enhancements

- [ ] Redis/DB backend for HistoryStore
- [ ] History summarization for long conversations
- [ ] Full Anthropic/Gemini/Perplexity implementations
- [ ] Streaming responses
- [ ] Rate limiting and caching
- [ ] Metrics and observability








