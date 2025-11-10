# Phase 1 Quickstart Guide

This guide will help you set up and test the Phase 1 deliverables of the Cross-LLM Thread Hub.

## Phase 1 Deliverables

✅ **Foundation:**
- Docker Compose for local Postgres + Qdrant + Redis
- Database schema with RLS policies
- NextAuth email magic link authentication
- BYOK vault with server-side encryption

✅ **API Endpoints:**
- `POST /api/orgs/{id}/providers` - Save encrypted provider keys
- `GET /api/orgs/{id}/providers/status` - Get provider status (masked keys)
- `POST /api/orgs/{id}/providers/test` - Test provider connections (**Exit Criteria**)

✅ **UI:**
- Settings/Providers page with Test Connection button
- Thread UI stub with send message and provider badge

✅ **Phase 1.5 - Observability:**
- Request counting per path/org/provider
- Latency tracking (p50, p95, p99)
- Error classification
- Metrics API at `GET /api/metrics`

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose

## Step 1: Start Local Services

```bash
# Start Postgres, Qdrant, and Redis
docker-compose up -d

# Verify services are running
docker-compose ps
```

You should see:
- `dac-postgres` on port 5432
- `dac-qdrant` on ports 6333, 6334
- `dac-redis` on port 6379

## Step 2: Set Up Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
```

Edit `.env` and set:

```bash
# Database (Docker Compose)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/dac

# Qdrant (Docker Compose)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Leave empty for local

# Redis (Docker Compose)
UPSTASH_REDIS_URL=http://localhost:6379
UPSTASH_REDIS_TOKEN=  # Leave empty for local

# Security - GENERATE THESE!
SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Email (for magic links) - Use Resend or SMTP
EMAIL_FROM=noreply@yourdomain.com
RESEND_API_KEY=re_xxx  # Or configure SMTP_* variables

# Stripe (optional for Phase 1)
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_ID=price_xxx

# Frontend
FRONTEND_URL=http://localhost:3000
```

Run migrations:

```bash
# Apply database schema and RLS policies
alembic upgrade head
```

Start the backend:

```bash
# Development mode with auto-reload
python main.py

# Or use uvicorn directly
uvicorn main:app --reload
```

Backend will be available at **http://localhost:8000**

## Step 3: Set Up Frontend

```bash
cd frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local
```

Edit `.env.local`:

```bash
# Auth
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=$(openssl rand -base64 32)

# Database (same as backend)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dac

# Email (same provider as backend)
RESEND_API_KEY=re_xxx
# Or SMTP configuration
EMAIL_FROM=noreply@yourdomain.com
```

Start the frontend:

```bash
npm run dev
```

Frontend will be available at **http://localhost:3000**

## Step 4: Test Phase 1 Exit Criteria

### Option A: Automated Test Script

```bash
# From project root
python test_phase1_exit.py
```

This tests:
1. ✅ Database connectivity and schema
2. ✅ Organization creation
3. ✅ Provider key management
4. ✅ Provider connection testing
5. ✅ Observability metrics

### Option B: Manual Testing

#### 1. Create Organization

Run the test script or manually insert:

```bash
cd backend
python -c "
import asyncio
from app.database import AsyncSessionLocal
from app.models.org import Org

async def create_org():
    async with AsyncSessionLocal() as session:
        org = Org(
            id='org_demo',
            name='Demo Organization',
            slug='demo',
            tier='trial'
        )
        session.add(org)
        await session.commit()
        print(f'Created org: {org.id}')

asyncio.run(create_org())
"
```

#### 2. Add Provider Keys via UI

1. Visit **http://localhost:3000/settings/providers**
2. For each provider (Perplexity, OpenAI, Gemini, OpenRouter):
   - Click "Configure"
   - Enter your API key
   - Click "Test Before Saving" (optional)
   - Click "Save Key"

#### 3. Test Connections

On the same page, click **"Test Connection"** for each configured provider.

**Expected results:**
- ✅ Perplexity: "Connection successful"
- ✅ OpenAI: "Connection successful" + model count
- ✅ Gemini: "Connection successful" + model count
- ✅ OpenRouter: "Connection successful" + model count

#### 4. Verify Encryption

Keys are encrypted in the database:

```bash
psql postgresql://postgres:postgres@localhost:5432/dac -c \
  "SELECT provider, encode(encrypted_key, 'base64') FROM provider_keys LIMIT 1;"
```

You should see base64-encoded ciphertext, not plaintext keys.

#### 5. Check Observability Metrics

```bash
# System-wide metrics
curl http://localhost:8000/api/metrics | jq

# Per-org metrics
curl http://localhost:8000/api/metrics/org/org_demo | jq
```

**Expected output:**
- Total request count
- Requests by path
- Requests by provider
- Latency statistics (min, max, avg, p50, p95, p99)
- Error counts by class

## Step 5: Test Thread UI Stub

1. Visit **http://localhost:3000/threads**
2. Select a provider (Perplexity, OpenAI, Gemini, or OpenRouter)
3. Type a message and click "Send"
4. See the provider badge on the simulated response

**Note:** This is a Phase 1 stub. Real LLM integration comes in Phase 2.

## Phase 1 Exit Criteria Checklist

- [ ] Docker services running (Postgres, Qdrant, Redis)
- [ ] Backend API running at http://localhost:8000
- [ ] Frontend running at http://localhost:3000
- [ ] Database schema created (all tables exist)
- [ ] RLS policies applied
- [ ] Organization created
- [ ] Provider API keys added (at least one)
- [ ] Test Connection succeeds for configured providers
- [ ] Metrics endpoint returns data
- [ ] Thread UI displays provider badges

## Common Issues

### Database Connection Errors

```bash
# Restart Docker services
docker-compose down
docker-compose up -d

# Check logs
docker-compose logs postgres
```

### Migration Errors

```bash
# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
cd backend
alembic upgrade head
```

### Frontend Build Errors

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Email Magic Links Not Working

For local testing, check your email provider's logs:
- **Resend:** https://resend.com/emails
- **SMTP:** Check your SMTP server logs

## Next Steps: Phase 2

Once Phase 1 exit criteria pass, you're ready for Phase 2:

1. **Thread/Message CRUD** - Real database-backed conversations
2. **Provider Adapters** - Actual LLM API integrations
3. **Router Logic** - Rule-based provider selection
4. **Context Rehydration** - Last-N messages + top-K memory
5. **Forward Dialog** - Move conversations between providers

## Support

- Check logs: `docker-compose logs -f`
- Backend logs: Terminal running `python main.py`
- Frontend logs: Terminal running `npm run dev`
- Database: `psql postgresql://postgres:postgres@localhost:5432/dac`

---

**Phase 1 Complete!** 🎉

You now have:
- ✅ Secure BYOK vault with encryption
- ✅ Provider health checks
- ✅ Basic observability
- ✅ Foundation for Phase 2 threading
