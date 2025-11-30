---
title: Contributing to DAC
summary: Guidelines for contributing code, documentation, and improvements to DAC
last_updated: 2025-01-12
owner: DAC
tags: [dac, contributing, standards]
---

# Contributing to DAC

Thank you for your interest in contributing to DAC! This guide will help you get started.

## Getting Started

1. **Fork the repository**
2. **Clone your fork**: `git clone https://github.com/your-username/DAC.git`
3. **Create a branch**: `git checkout -b feature/your-feature-name`
4. **Make your changes**
5. **Test your changes**
6. **Commit with clear messages**
7. **Push and open a Pull Request**

## Code Style

- Follow the existing code style in each language
- Python: Follow PEP 8, use Black for formatting
- TypeScript/JavaScript: Follow ESLint rules
- Run linters before committing

## Commit Messages

Use clear, descriptive commit messages:

```
feat: add support for Kimi provider
fix: resolve memory leak in conversation history
docs: update API reference with new endpoints
```

Prefixes:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Test additions/changes
- `chore:` - Maintenance tasks

## Pull Requests

- Keep PRs focused on a single feature or fix
- Include tests for new features
- Update documentation as needed
- Reference related issues
- Request review from maintainers

## Testing

- Write tests for new features
- Ensure all existing tests pass
- Add integration tests for API changes

## Documentation

- Update relevant documentation when adding features
- Follow the [Documentation Style Guide](./DOCS_STYLE_GUIDE.md)
- Add examples for new APIs or features

## Questions?

Open an issue or contact the maintainers.








