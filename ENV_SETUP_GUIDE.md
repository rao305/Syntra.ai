# Environment Variables Setup Guide

This guide helps developers set up their environment after pulling code from GitHub.

## Quick Start

Run the automated setup script:

```bash
./setup-env.sh
```

This will:
- Create `backend/.env` from `backend/env.example`
- Create `frontend/.env.local` from `frontend/env.example`
- Optionally generate secure `SECRET_KEY` and `ENCRYPTION_KEY`

## Manual Setup

### Backend

1. Copy the example file:
   ```bash
   cp backend/env.example backend/.env
   ```

2. Edit `backend/.env` and configure:
   - **Required**: `DATABASE_URL`, `QDRANT_URL`, `UPSTASH_REDIS_URL`, `SECRET_KEY`, `ENCRYPTION_KEY`
   - **Optional**: Provider API keys (`OPENAI_API_KEY`, `GOOGLE_API_KEY`, etc.)

3. Generate secure keys:
   ```bash
   # SECRET_KEY
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   
   # ENCRYPTION_KEY
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

### Frontend

1. Copy the example file:
   ```bash
   cp frontend/env.example frontend/.env.local
   ```

2. Edit `frontend/.env.local` and configure:
   - **Required**: `NEXT_PUBLIC_API_URL` (backend API URL)
   - **Optional**: Firebase configuration (if using Firebase auth)

## Environment Variables Reference

### Backend Variables

See `backend/env.example` for complete documentation. Key variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes* | `postgresql+asyncpg://postgres:postgres@localhost:5432/syntra` | PostgreSQL connection string |
| `QDRANT_URL` | Yes* | `http://localhost:6333` | Qdrant vector database URL |
| `UPSTASH_REDIS_URL` | Yes* | `redis://localhost:6379` | Redis connection URL |
| `SECRET_KEY` | Yes* | `dev-secret-key-...` | JWT signing key (change in production!) |
| `ENCRYPTION_KEY` | Yes* | `dev-encryption-key-...` | Fernet key for API key encryption |
| `OPENAI_API_KEY` | No | - | OpenAI API key (optional fallback) |
| `GOOGLE_API_KEY` | No | - | Google/Gemini API key (optional fallback) |
| `PERPLEXITY_API_KEY` | No | - | Perplexity API key (optional fallback) |
| `KIMI_API_KEY` | No | - | Kimi/Moonshot API key (optional fallback) |

*Required fields have development defaults but should be configured properly for production.

### Frontend Variables

See `frontend/env.example` for complete documentation. Key variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | Yes | `http://localhost:8000/api` | Backend API base URL |
| `NEXT_PUBLIC_WS_URL` | No | `ws://localhost:8000` | WebSocket URL |
| `NEXT_PUBLIC_FIREBASE_*` | No | - | Firebase configuration (if using Firebase auth) |

## Development vs Production

### Development

- Backend config includes sensible defaults for local development
- Missing API keys will disable features but won't crash the app
- Placeholder security keys work but should be changed

### Production

- All required fields must be properly configured
- Security keys must be changed from defaults
- Database and service URLs must point to production instances
- The config will warn if production settings are invalid

## Troubleshooting

### "Missing environment variable" errors

1. Check that `.env` files exist in the correct locations
2. Verify variable names match exactly (case-sensitive in some contexts)
3. Restart the application after changing `.env` files

### API endpoints not working

1. Verify `NEXT_PUBLIC_API_URL` in `frontend/.env.local` matches your backend URL
2. Check that the backend is running and accessible
3. Ensure CORS is configured correctly in backend settings

### Provider API keys not working

1. Verify keys are set correctly in `backend/.env`
2. Check that keys are valid and have proper permissions
3. For frontend workflow features, ensure backend `.env` is accessible (or set keys in frontend env)

## Best Practices

1. **Never commit `.env` files** - They're gitignored for security
2. **Use `env.example` files** - These are templates that can be committed
3. **Generate secure keys** - Use the provided commands or `setup-env.sh`
4. **Document custom variables** - If you add new variables, update `env.example`
5. **Use environment-specific configs** - Different `.env` files for dev/staging/prod

## Team Development

For teams using AWS Parameter Store:

1. Configure AWS credentials: `aws configure`
2. Fetch secrets: `./scripts/fetch-secrets.sh`
3. This creates `backend/.env.local` with all secrets

See `README.md` for more details on team setup.











