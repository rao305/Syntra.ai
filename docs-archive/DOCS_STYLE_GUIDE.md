---
title: Documentation Style Guide
summary: Standards and guidelines for writing and formatting DAC documentation
last_updated: 2025-01-12
owner: DAC
tags: [dac, docs, standards, style-guide]
---

# Documentation Style Guide

This guide defines the standards for writing and formatting documentation in the DAC repository.

## File Naming

- Use **UPPER_SNAKE_CASE.md** for top-level documentation files
- Examples: `API_REFERENCE.md`, `SYSTEM_DESIGN.md`, `CHANGELOG.md`
- Phase files: `PHASE{N}_IMPLEMENTATION.md` (e.g., `PHASE1_IMPLEMENTATION.md`)
- Validation checklists: `PHASE{N}_{M}_VALIDATION_CHECKLIST.md`

## Front-Matter

Every documentation file must include YAML front-matter at the top:

```yaml
---
title: Document Title
summary: One to two sentence summary of the document
last_updated: YYYY-MM-DD
owner: DAC
tags: [dac, docs, relevant-tags]
---
```

### Required Fields

- **title**: Document title (should match H1 heading)
- **summary**: Brief description (1-2 sentences)
- **last_updated**: Date in YYYY-MM-DD format
- **owner**: Usually "DAC" or specific team name
- **tags**: Array of relevant tags

## Headings

- Use a single `# H1` heading that matches the front-matter title
- Use `## H2` for major sections
- Use `### H3` for subsections
- Maintain a logical hierarchy (don't skip levels)

## Links

### Internal Links

- Use relative paths: `[Link Text](./path/to/file.md)`
- For files in the same directory: `[Link](./file.md)`
- For files in subdirectories: `[Link](./subdir/file.md)`
- For parent directories: `[Link](../file.md)`

### External Links

- Use absolute URLs: `[Link Text](https://example.com)`
- Consider adding `{:target="_blank"}` for external links if your renderer supports it

## Images

- Store all images in `/docs/assets/`
- Reference images with relative paths: `![Alt Text](./assets/image.png)`
- Use descriptive alt text
- Prefer SVG for diagrams, PNG/JPG for screenshots

## Code Blocks

Use fenced code blocks with language specification:

````markdown
```python
def example():
    return "code"
```
````

For shell commands, use `bash` or `shell`:

````markdown
```bash
docker compose up -d
```
````

## Lists

- Use `-` for unordered lists
- Use `1.` for ordered lists
- Indent nested lists with 2 spaces
- Add blank lines before and after lists

## Tables

Use GitHub-flavored markdown tables:

```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
```

## Emphasis

- **Bold** for important terms: `**term**`
- *Italic* for emphasis: `*text*`
- `Code` for inline code: `` `code` ``
- Use backticks for file names, commands, and technical terms

## Sections

Common sections to include:

- **Overview/Introduction**: What the document covers
- **Prerequisites**: What's needed before starting
- **Steps/Instructions**: Main content
- **Examples**: Code or configuration examples
- **Troubleshooting**: Common issues and solutions
- **References**: Links to related documentation

## Writing Style

- Write in clear, concise language
- Use active voice when possible
- Define acronyms on first use
- Include examples for complex concepts
- Add diagrams for architectural concepts
- Keep paragraphs short (3-4 sentences)

## Maintenance

- Update `last_updated` when making changes
- Keep links current (fix broken links immediately)
- Archive superseded documents rather than deleting
- Add new documents to the appropriate directory
- Update `/docs/README.md` when adding major new sections

## Examples

### Good Example

```markdown
---
title: API Authentication
summary: How to authenticate API requests using API keys
last_updated: 2025-01-12
owner: DAC
tags: [dac, api, authentication]
---

# API Authentication

DAC uses API keys for authentication. Include your API key in the `Authorization` header.

## Getting an API Key

1. Navigate to Settings → API Keys
2. Click "Generate New Key"
3. Copy the key (it's only shown once)

## Using the API Key

Include the key in your request headers:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://api.dac.example.com/v1/threads
```
```

### Bad Example

```markdown
# api auth

use api keys. get them from settings.
```

---

**Questions?** Open an issue or contact the DAC team.








