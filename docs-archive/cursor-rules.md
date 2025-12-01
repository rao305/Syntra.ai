# Cursor IDE Rules

This file configures Cursor's AI assistant behavior for the Syntra project.

## System Prompt Integration

The primary system prompt is located at `.ide/system-prompt.md`. This prompt ensures:

- Consistent Markdown + LaTeX + code block formatting
- Proper code generation practices
- Mathematical notation using LaTeX syntax
- Dark theme code blocks for easy copying

## Project-Specific Context

### Tech Stack
- **Frontend**: Next.js 14, React, TypeScript, Tailwind CSS
- **Backend**: Python FastAPI, PostgreSQL, SQLAlchemy
- **AI/ML**: Multiple LLM providers (OpenAI, Anthropic, Google Gemini, etc.)
- **Infrastructure**: Docker, Railway, Vercel

### Key Directories
- `/frontend/` - Next.js application
- `/backend/` - Python FastAPI service
- `/docs/` - Documentation and guides
- `/.ide/` - IDE configuration files

### Code Style Preferences
- TypeScript for all frontend code
- Use existing component patterns in `/frontend/components/`
- Follow the established API patterns in `/backend/app/api/`
- Maintain consistent error handling patterns

### Development Workflow
1. Always check existing patterns before creating new ones
2. Use the project's established naming conventions
3. Follow the existing import/export structure
4. Test changes against the running development server

## AI Assistant Behavior

When helping with this project:
1. Reference the system prompt in `.ide/system-prompt.md`
2. Use fenced code blocks with proper language tags
3. Include LaTeX for any mathematical expressions
4. Respect the existing architecture and patterns
5. Provide complete, runnable code examples