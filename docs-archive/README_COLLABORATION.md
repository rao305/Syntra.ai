# 🤖 Multi-Agent Collaboration System

This implementation provides a complete 5-agent collaboration pipeline with conversation continuity and follow-up capabilities.

## 🏗️ Architecture

### Database Schema

The collaboration system uses a robust schema designed for multi-agent workflows:

```sql
conversations     -- Main conversation threads
├── collab_runs   -- Individual 5-agent collaboration runs  
│   ├── collab_steps -- Individual agent steps (analyst→researcher→creator→critic→synthesizer)
│   └── collab_messages -- All messages (user, assistant, agent outputs)
```

### Agent Pipeline

1. **Analyst** (Gemini) - Problem breakdown, user archetypes, structure
2. **Researcher** (Perplexity) - Web research with citations  
3. **Creator** (GPT) - Main solution draft
4. **Critic** (GPT) - Flaws, risks, improvements
5. **Synthesizer** (GPT) - Final integrated report

## 🚀 Setup

### 1. Run the Migration

```bash
cd backend
python run_migration.py
```

This creates all necessary tables, enums, views, and functions.

### 2. API Endpoints

The system adds these new endpoints:

```bash
# Full 5-agent collaboration
POST /api/collaboration/collaborate
{
  "message": "Help me build a todo app",
  "user_id": "user123",
  "thread_id": "optional"
}

# Ask follow-up questions
POST /api/collaboration/follow-up  
{
  "message": "Expand on the database design section",
  "thread_id": "thread_abc",
  "user_id": "user123"
}

# Meta-questions about the process
POST /api/collaboration/meta-question
{
  "question": "What did the Researcher find?",
  "thread_id": "thread_abc", 
  "user_id": "user123"
}

# Get collaboration run details
GET /api/collaboration/turns/{turn_id}

# Get agent outputs for a thread
GET /api/collaboration/threads/{thread_id}/agent-outputs?role=agent_researcher

# Regular messages with collaboration mode
POST /api/threads/{thread_id}/messages
{
  "content": "Build me an app",
  "collaboration_mode": true
}
```

### 3. Required API Keys

Set these environment variables for the providers:

```bash
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...  
PERPLEXITY_API_KEY=pplx-...
```

Or configure them in the database via the existing provider keys system.

## 📋 Usage Examples

### Basic Collaboration

```bash
curl -X POST "http://localhost:8000/api/collaboration/collaborate" \
  -H "X-Org-ID: org_demo" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want to build a habit tracking app called MindTrack",
    "user_id": "user123"
  }'
```

Response includes:
- `final_report` - Synthesizer's integrated response
- `agent_outputs` - All 5 agent outputs 
- `turn_id` - For follow-up references
- `total_time_ms` - Performance metrics

### Follow-up Questions

```bash
curl -X POST "http://localhost:8000/api/collaboration/follow-up" \
  -H "X-Org-ID: org_demo" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Can you expand on the tech stack recommendations?",
    "thread_id": "collab_abc123",
    "user_id": "user123"  
  }'
```

### Meta-Questions

```bash
curl -X POST "http://localhost:8000/api/collaboration/meta-question" \
  -H "X-Org-ID: org_demo" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What specific research did Perplexity find about habit tracking?",
    "thread_id": "collab_abc123",
    "user_id": "user123"
  }'
```

## 🔍 Key Features

### ✅ Conversation Continuity

Users can reference any part of previous collaborations:

- "What did the Researcher find?" 
- "Show me the Critic's concerns again"
- "Expand on the roadmap section"
- "Compare what the Analyst and Creator recommended"

### ✅ Structured Storage

All agent outputs are stored with:

- Role identification (analyst, researcher, creator, critic, synthesizer)
- Provider and model used
- Execution order and timing
- Full context and outputs
- Turn-based threading

### ✅ Smart Context Building

The system automatically:

- Builds progressive context through the pipeline
- Maintains conversation history
- Supports meta-questions about the process
- Enables follow-up questions on specific sections

### ✅ Performance Tracking

Tracks and reports:

- Total collaboration time
- Individual agent execution time  
- Token usage across providers
- Success/failure rates
- Provider performance metrics

## 🧪 Testing

Run the included test suite:

```bash
python test_collaboration.py
```

This tests:
- Basic collaboration pipeline
- Follow-up questions
- Meta-questions
- Regular message integration
- Database storage/retrieval

## 📊 Database Queries

### Get Recent Agent Outputs

```sql
SELECT * FROM get_recent_agent_outputs('conversation_id', 10);
```

### Get Collaboration History

```sql
SELECT * FROM collab_run_summary 
WHERE conversation_id = 'conversation_id'
ORDER BY started_at DESC;
```

### Find Specific Agent Responses

```sql
SELECT content_text, created_at 
FROM collab_messages 
WHERE conversation_id = 'conversation_id' 
  AND role = 'agent_researcher'
ORDER BY created_at DESC;
```

## 🛠️ Extending

### Adding New Agents

1. Add to `CollabRole` enum in migration
2. Update `agent_configs` in `CollaborationService`
3. Add corresponding `MessageRole` mapping
4. Implement agent logic in `CollaborationEngine`

### Custom Agent Workflows

The system supports:
- Parallel agent execution  
- Conditional agent triggering
- Custom agent prompts
- Mock agents for testing

### Integration Points

- Works with existing Syntra routing
- Integrates with provider key management
- Supports existing auth/org isolation
- Compatible with current message threading

## 🚨 Error Handling

The system includes comprehensive error handling:

- **Agent Failures**: Individual agents can fail without breaking the pipeline
- **Provider Outages**: Automatic fallback to alternative providers
- **Rate Limits**: Exponential backoff and retry logic
- **Validation**: Input sanitization and output validation
- **Rollback**: Database transactions ensure consistency

## 🔐 Security

- **Row Level Security**: All tables use RLS for org isolation
- **Input Sanitization**: User inputs are sanitized before processing
- **API Key Management**: Secure storage and rotation of provider keys
- **Audit Trail**: Complete audit trail of all collaboration activities