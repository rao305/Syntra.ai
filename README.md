# Cross-LLM Thread Hub (MVP)

Multi-tenant B2B hub for cross-provider conversation threading (Perplexity, OpenAI Responses, Gemini), governed memory, and audit logs.

## Getting Started

1) `cp .env.example .env.local` and fill values

2) `docker compose up -d`  (Postgres + Qdrant)

3) Apply migrations in `apps/api/migrations`

4) `uvicorn apps.api.main:app --reload` (API)

5) `pnpm --filter @web dev` (Web)

## Packages

- `apps/api`: FastAPI, adapters, router, memory policies

- `apps/web`: Next.js App Router, settings/providers, threads UI

## Docs

- /docs/ARCHITECTURE.md (coming)
