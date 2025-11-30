---
title: Coding Guidelines
summary: Code style, best practices, and conventions for DAC development
last_updated: 2025-01-12
owner: DAC
tags: [dac, coding, standards, guidelines]
---

# Coding Guidelines

This document outlines coding standards and best practices for the DAC project.

## Python (Backend)

### Style

- Follow **PEP 8** style guide
- Use **Black** for code formatting (line length: 100)
- Use **type hints** for function signatures
- Use **async/await** for I/O operations

### Example

```python
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession

async def get_thread(
    db: AsyncSession,
    thread_id: str
) -> Optional[Dict[str, Any]]:
    """Get a thread by ID.
    
    Args:
        db: Database session
        thread_id: Thread identifier
        
    Returns:
        Thread data or None if not found
    """
    # Implementation
    pass
```

### Best Practices

- Use descriptive variable names
- Write docstrings for all public functions
- Handle errors explicitly (don't swallow exceptions)
- Use context managers for resources
- Keep functions focused and small

## TypeScript/JavaScript (Frontend)

### Style

- Use **TypeScript** for new code
- Follow **ESLint** rules
- Use **Prettier** for formatting
- Prefer functional components with hooks

### Example

```typescript
interface MessageProps {
  content: string
  timestamp: Date
  role: 'user' | 'assistant'
}

export function Message({ content, timestamp, role }: MessageProps) {
  return (
    <div className={cn('message', role)}>
      <p>{content}</p>
      <time>{timestamp.toISOString()}</time>
    </div>
  )
}
```

### Best Practices

- Use TypeScript interfaces for props
- Extract reusable logic into custom hooks
- Use meaningful component and variable names
- Keep components small and focused
- Handle loading and error states

## General Principles

### Code Organization

- Group related functionality together
- Separate concerns (business logic vs. UI)
- Use dependency injection where appropriate
- Keep files focused (one main responsibility)

### Error Handling

- Handle errors explicitly
- Provide meaningful error messages
- Log errors appropriately
- Don't expose sensitive information in errors

### Testing

- Write unit tests for business logic
- Write integration tests for APIs
- Aim for good test coverage
- Keep tests fast and independent

### Performance

- Profile before optimizing
- Use async/await for I/O
- Cache expensive operations
- Optimize database queries

### Security

- Never commit secrets or API keys
- Validate and sanitize user input
- Use parameterized queries
- Follow principle of least privilege

## Tools

- **Linters**: Run before committing
- **Formatters**: Use automated formatting
- **Type Checkers**: TypeScript, mypy
- **Testing**: pytest, Jest, Playwright

---

**Questions?** See [Contributing Guide](./CONTRIBUTING.md) or open an issue.








