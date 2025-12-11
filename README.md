# Syntra - Unified AI Platform

**Enterprise-grade intelligent LLM routing platform that operates across multiple providers with unified context, intelligent routing, and enterprise security.**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org/)

---

## 🎯 Overview

Syntra is a unified AI assistant platform that intelligently routes queries across multiple LLM providers (OpenAI, Anthropic, Google Gemini, Perplexity, Kimi) while maintaining a single, consistent conversation context. Users interact with one assistant—Syntra—while the system automatically selects the optimal provider based on query intent, cost, and performance.

### Key Features

- **🤖 Unified AI Assistant** - Single persona across all providers
- **🧠 Intelligent Routing** - Intent-based provider selection
- **💬 Context Continuity** - Seamless context across provider switches
- **🔒 Enterprise Security** - Encrypted API keys, multi-tenant isolation
- **📊 Observability** - Real-time metrics, cost tracking, performance analytics
- **⚡ High Performance** - Sub-200ms p95 TTFT, 99.9% uptime
- **🎨 Modern UI** - Enterprise-grade B2B interface with motion and polish

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Conversations│  │   Settings   │  │   Analytics  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend API (FastAPI)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Router     │  │   Memory     │  │  Adapters    │     │
│  │  (Intent)    │  │  (Qdrant)    │  │ (Providers)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
    ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐
    │ OpenAI │    │Anthropic│   │ Gemini │    │Perplexity│
    └────────┘    └────────┘    └────────┘    └────────┘
```

### Core System Techniques

#### 1. **Intelligent Routing**
- **Intent Detection**: Analyzes query content to determine intent (social_chat, qa_retrieval, coding_help, editing/writing, reasoning/math)
- **Cost Optimization**: Routes to cheapest capable model (Gemini Flash for simple, GPT-4o-mini for reasoning, Perplexity for web search)
- **Performance-Based**: Monitors latency and automatically falls back to faster providers
- **Context-Aware**: Considers conversation length and complexity

#### 2. **Unified Persona System**
- **Syntra Identity**: All responses presented as "Syntra" regardless of underlying provider
- **Consistent Tone**: Single voice across all models (friendly, concise, helpful)
- **Response Sanitization**: Automatically removes provider self-references
- **Thinking Preamble**: Structured thinking/searching display for UI animation

#### 3. **Memory & Context Management**
- **Vector Memory**: Qdrant-based semantic memory for cross-conversation context
- **Coalescing**: Deduplicates concurrent requests to same query
- **Context Window Management**: Smart truncation for long conversations
- **Memory Retrieval**: Retrieves relevant past context based on query similarity

#### 4. **Multi-Tenant Architecture**
- **Organization Isolation**: Row-Level Security (RLS) at database level
- **Encrypted API Keys**: Fernet encryption for provider API keys
- **Per-Org Rate Limits**: Configurable limits per organization
- **Audit Logging**: Complete audit trail of all operations

#### 5. **Performance Optimization**
- **Streaming Responses**: Server-Sent Events (SSE) for real-time streaming
- **Request Coalescing**: Prevents duplicate API calls
- **Caching**: Redis-based caching for frequent queries
- **Connection Pooling**: Efficient database and HTTP connection management

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+**
- **Node.js 18+**
- **Docker & Docker Compose**
- **PostgreSQL 15+** (via Docker)
- **Qdrant** (via Docker)
- **Redis** (via Docker)

### Quick Reference - Complete Setup Guide

Follow these steps to set up your development environment (for both new setup and fresh pulls):

#### Step 1: Clone & Pull Latest Changes
```bash
# First time only
git clone https://github.com/rao305/Syntra.ai.git
cd Syntra

# Or if already cloned, pull latest changes
git pull origin main
```

#### Step 2: Remove Old Python Environment (Fresh Setup)
```bash
# Remove any old/broken virtual environment
rm -rf backend/venv
```

#### Step 3: Create Fresh Python Environment
```bash
cd backend
python3.9 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Step 4: Install Pinned Dependencies
```bash
pip install -r requirements.txt
```

#### Step 5: Setup Environment Variables

**Option A: Using AWS Credentials (Recommended for Team)**

```bash
# Configure AWS credentials
aws configure
# Enter credentials from developer-credentials.txt:
# - AWS Access Key ID: [your access key]
# - AWS Secret Access Key: [your secret key]
# - Default region: us-east-1
# - Default output format: json

# Go back to root directory
cd ..

# Fetch all secrets from AWS Parameter Store
./scripts/fetch-secrets.sh
# This creates:
# - backend/.env.local (with all backend variables)
# - frontend/.env.local (with all frontend variables)

# Verify everything loaded correctly
./scripts/verify-all-secrets.sh
```

**Option B: Manual Setup (Local Development)**

```bash
cd ..
./setup-env.sh
# Interactively configure environment variables
# Then edit backend/.env and frontend/.env.local manually
```

#### Step 6: Start Infrastructure Services
```bash
# Start Docker services (PostgreSQL, Qdrant, Redis)
docker compose up -d

# Verify services are running
docker compose ps
```

#### Step 7: Run Database Migrations
```bash
cd backend
alembic upgrade head
```

#### Step 8: Start Backend Server
```bash
python main.py
# OR use uvicorn for development
uvicorn main:app --reload --port 8000
```

#### Step 9: Start Frontend (in new terminal)
```bash
cd frontend
npm install
npm run dev
```

#### Step 10: Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Qdrant Dashboard**: http://localhost:6333/dashboard

---

**📝 Important Notes:**
- Always use `python3.9` or higher for virtual environment
- Each developer should have their own fresh venv (don't share venv directory)
- Environment files (.env, .env.local) are gitignored - never commit them
- AWS credentials should come from `developer-credentials.txt`

### 1. Clone Repository

```bash
git clone https://github.com/your-org/syntra.git
cd syntra
```

### 2. Environment Setup ⚙️

**🚀 Quick Setup (Recommended):**

Run the automated setup script to configure environment variables:

```bash
# Make script executable (if needed)
chmod +x setup-env.sh

# Run the setup script
./setup-env.sh
```

This script will:
- ✅ Create `backend/.env` from `backend/env.example`
- ✅ Create `frontend/.env.local` from `frontend/env.example`
- ✅ Optionally generate secure `SECRET_KEY` and `ENCRYPTION_KEY`
- ✅ Check for existing files before overwriting

**📝 Manual Setup (Alternative):**

If you prefer to set up manually:

```bash
# Backend
cp backend/env.example backend/.env
# Edit backend/.env with your configuration

# Frontend
cp frontend/env.example frontend/.env.local
# Edit frontend/.env.local with your backend API URL
```

**⚠️ Important:** After setting up environment files, you'll need to:
1. Edit `backend/.env` with your database, Qdrant, and Redis URLs
2. Generate secure keys for `SECRET_KEY` and `ENCRYPTION_KEY` (or let the script do it)
3. Edit `frontend/.env.local` with your backend API URL (`NEXT_PUBLIC_API_URL`)

See the [Environment Variables](#environment-variables) section below for detailed configuration.

### 3. Start Infrastructure Services

```bash
# Start PostgreSQL, Qdrant, and Redis
docker compose up -d

# Verify services are running
docker compose ps
```

### 4. Backend Setup

#### Option A: AWS Parameter Store (Recommended for Team Development)

**Step 1: Configure AWS Credentials**

Get your AWS credentials from the team (see `developer-credentials.txt`):

```bash
aws configure

# When prompted, enter:
# AWS Access Key ID: [from developer-credentials.txt]
# AWS Secret Access Key: [from developer-credentials.txt]
# Default region: us-east-1
# Default output format: json
```

**Step 2: Fetch Secrets from Parameter Store**

```bash
# Fetch all secrets from AWS Parameter Store
./scripts/fetch-secrets.sh

# This creates:
# - backend/.env.local (backend variables, gitignored, never commit)
# - frontend/.env.local (frontend variables, gitignored, never commit)
```

**✅ All 47 parameters are uploaded with correct names and real values (no placeholders)**

**Verify everything is correct:**
```bash
# Check that all secrets are properly uploaded
./scripts/verify-all-secrets.sh

# List all uploaded parameters
./scripts/list-all-parameters.sh
```

**Step 3: Install Dependencies and Start**

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Secrets are now available in .env.local
# Backend automatically loads from .env.local

# Run migrations
alembic upgrade head

# Start backend
python main.py
# OR
uvicorn main:app --reload --port 8000
```

#### Option B: Local Development (Manual Setup)

If you want to set up locally without AWS:

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
# If you haven't run setup-env.sh, copy the example:
cp env.example .env

# Generate security keys (or let setup-env.sh do it)
# Generate SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate ENCRYPTION_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Edit .env with your configuration
# Required: DATABASE_URL, QDRANT_URL, UPSTASH_REDIS_URL, SECRET_KEY, ENCRYPTION_KEY
# Optional: Provider API keys (OPENAI_API_KEY, GOOGLE_API_KEY, etc.)

# Run migrations
alembic upgrade head

# Start backend
python main.py
# OR
uvicorn main:app --reload --port 8000
```

**💡 Note:** The backend config includes sensible defaults for development. Required fields have placeholder values that work locally, but you should configure them properly for production.

### 5. Frontend Setup

#### Option A: AWS Parameter Store (Recommended for Team Development)

If you're using AWS Parameter Store (see Backend Setup - Option A), the frontend variables are automatically fetched:

```bash
cd frontend

# Install dependencies
npm install

# Frontend variables are already in frontend/.env.local from fetch-secrets.sh
# No manual configuration needed!

# Start development server
npm run dev
```

#### Option B: Manual Setup

If setting up locally without AWS:

```bash
cd frontend

# Install dependencies
npm install

# Configure environment variables
# If you haven't run setup-env.sh, copy the example:
cp env.example .env.local

# Edit .env.local
# Required: NEXT_PUBLIC_API_URL=http://localhost:8000/api
# Optional: Firebase configuration (if using Firebase auth)

# Start development server
npm run dev
```

### 6. Access Application

Once both backend and frontend are running:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Qdrant Dashboard**: http://localhost:6333/dashboard

---

## 📋 Detailed Setup

### First-Time Setup Checklist

After cloning the repository, follow these steps:

1. ✅ **Run setup script**: `./setup-env.sh` (or manually copy env.example files)
2. ✅ **Configure backend/.env**: Set database, Qdrant, Redis URLs and generate secure keys
3. ✅ **Configure frontend/.env.local**: Set `NEXT_PUBLIC_API_URL` to your backend URL
4. ✅ **Start infrastructure**: `docker compose up -d`
5. ✅ **Install backend dependencies**: `cd backend && python3 -m venv venv && pip install -r requirements.txt`
6. ✅ **Run migrations**: `cd backend && alembic upgrade head`
7. ✅ **Install frontend dependencies**: `cd frontend && npm install`
8. ✅ **Start backend**: `cd backend && python main.py` or `uvicorn main:app --reload`
9. ✅ **Start frontend**: `cd frontend && npm run dev`

### Secrets Management

**AWS Systems Manager Parameter Store** (Recommended):
- Secrets are stored securely in AWS Parameter Store
- Use `./scripts/fetch-secrets.sh` to fetch them locally into `.env.local`
- `.env.local` is gitignored and never committed
- Team members: Get AWS credentials from `developer-credentials.txt`

**Setup for Team:**
```bash
# 1. One-time setup: Upload secrets to Parameter Store
#    (Reads from both backend/.env and frontend/.env.local)
./scripts/setup-parameter-store.sh

# 2. Give IAM permissions to team members
# Share: scripts/setup-iam-policy.json with your AWS admin

# 3. Team members setup:
#    a. Configure AWS: aws configure (use credentials from developer-credentials.txt)
#    b. Fetch secrets: ./scripts/fetch-secrets.sh
#       This creates:
#       - backend/.env.local (backend variables)
#       - frontend/.env.local (frontend variables)
#    c. Verify: ./scripts/verify-all-secrets.sh
```

**📊 Current Status:**
- ✅ **47 parameters** uploaded to AWS Parameter Store
- ✅ All parameter names are correct (no placeholders)
- ✅ All values are real (no placeholder values)
- ✅ Both backend and frontend variables included

**For Single Developer:**
- Run `./setup-env.sh` to create environment files from templates
- Or manually copy `backend/env.example` to `backend/.env` and `frontend/env.example` to `frontend/.env.local`
- Configure the files with your local settings

### Environment Variables

**🚀 Quick Setup**: Run `./setup-env.sh` to automatically create environment files from templates.

**📖 Full Guide**: See [ENV_SETUP_GUIDE.md](./ENV_SETUP_GUIDE.md) for detailed environment variable documentation and troubleshooting.

#### Backend (`backend/.env`)

See `backend/env.example` for a complete template with all available options. Complete configuration example:

```env
# LLM Provider API Keys [REQUIRED for full functionality]
OPENAI_API_KEY=sk-proj-...
GOOGLE_API_KEY=AIzaSy...
PERPLEXITY_API_KEY=pplx-...
KIMI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-v1-...

# Database [REQUIRED]
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/dac

# Vector Database [REQUIRED]
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Empty for local development

# Redis [REQUIRED]
UPSTASH_REDIS_URL=redis://localhost:6379
UPSTASH_REDIS_TOKEN=  # Empty for local Redis

# Security [REQUIRED - Generate secure values!]
SECRET_KEY=your-secret-key-here  # Generate: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENCRYPTION_KEY=your-encryption-key-here  # Generate: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:3000

# Environment
ENVIRONMENT=development

# Memory & Intelligent Routing Features
INTELLIGENT_ROUTING_ENABLED=1
MEMORY_ENABLED=1  # Requires Qdrant to be healthy

# SuperMemory API (long-term episodic memory)
SUPERMEMORY_API_KEY=sm_...
SUPERMEMORY_API_BASE_URL=https://api.supermemory.ai

# Rate Limits (defaults)
DEFAULT_REQUESTS_PER_DAY=1000
DEFAULT_TOKENS_PER_DAY=100000

# Provider Rate Limiting (Pacer Configuration)
# Shape traffic to avoid 429s while maintaining responsive UX
PERPLEXITY_RPS=1
PERPLEXITY_BURST=2
PERPLEXITY_CONCURRENCY=3

OPENAI_RPS=2
OPENAI_BURST=5
OPENAI_CONCURRENCY=5

GEMINI_RPS=2
GEMINI_BURST=5
GEMINI_CONCURRENCY=5

OPENROUTER_RPS=2
OPENROUTER_BURST=5
OPENROUTER_CONCURRENCY=5

# Feature Flags
FEATURE_COREWRITE=1
feature_corewrite=true

# Email (for magic links - optional)
EMAIL_FROM=noreply@example.com
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=

# Resend API (optional)
RESEND_API_KEY=

# Stripe (optional)
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_ID=

# Firebase / Auth Integration
FIREBASE_CREDENTIALS_FILE=/path/to/firebase-adminsdk.json
FIREBASE_PROJECT_ID=your-project-id
DEFAULT_ORG_ID=org_demo

# Clerk (optional - alternative auth provider)
CLERK_SECRET_KEY=sk_test_...
```

**💡 Important Notes:**
- The backend config includes sensible defaults for development
- Required fields: `DATABASE_URL`, `QDRANT_URL`, `UPSTASH_REDIS_URL`, `SECRET_KEY`, `ENCRYPTION_KEY`
- **You must configure them properly for production**
- Generate secure keys: The setup script can do this, or use the commands shown above
- Provider API keys can be set per-organization via API, or globally in `.env`
- Rate limiting configuration helps prevent 429 errors from providers
- Memory features require Qdrant to be running and healthy

#### Frontend (`frontend/.env.local`)

See `frontend/env.example` for a complete template. Complete configuration example:

```env
# Backend API URL [REQUIRED]
NEXT_PUBLIC_API_URL=http://localhost:8000/api

# WebSocket URL (optional)
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Firebase Auth Configuration [REQUIRED if using Firebase]
NEXT_PUBLIC_FIREBASE_API_KEY=AIzaSy...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project-id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=123456789012
NEXT_PUBLIC_FIREBASE_APP_ID=1:123456789012:web:abc123def456
```

**💡 Important Notes:**
- `NEXT_PUBLIC_API_URL` must match your backend server URL
- Firebase configuration is required if using Firebase authentication
- All `NEXT_PUBLIC_*` variables are exposed to the browser
- Never put sensitive secrets in frontend environment variables

### Database Setup

```bash
cd backend

# Create database (if not using Docker)
createdb syntra

# Run migrations
alembic upgrade head

# Verify tables
psql -d syntra -c "\dt"
```

### Provider API Keys

API keys can be configured in two ways:

1. **Per-Organization** (Recommended): Via API or UI settings
2. **Global Default**: Set in `backend/.env` (fallback)

```bash
# Add API key for an organization
curl -X POST http://localhost:8000/api/orgs/{org_id}/provider-keys \
  -H "Content-Type: application/json" \
  -H "x-org-id: {org_id}" \
  -d '{
    "provider": "openai",
    "api_key": "sk-...",
    "is_active": true
  }'
```

### Feature Flags & Configuration

**Intelligent Routing:**
- `INTELLIGENT_ROUTING_ENABLED=1` - Enables intent-based provider selection (always recommended)

**Memory System:**
- `MEMORY_ENABLED=1` - Enables Qdrant-based semantic memory (requires Qdrant to be healthy)
- `SUPERMEMORY_API_KEY` - Long-term episodic memory via SuperMemory API

**Query Rewriting:**
- `FEATURE_COREWRITE=1` - Enables LLM-based context-aware query rewriting
- Improves handling of ambiguous queries and coreference resolution

**Rate Limiting:**
Configure per-provider rate limits to prevent 429 errors:
- `{PROVIDER}_RPS` - Requests per second
- `{PROVIDER}_BURST` - Burst capacity
- `{PROVIDER}_CONCURRENCY` - Concurrent request limit

Example for Perplexity:
```env
PERPLEXITY_RPS=1
PERPLEXITY_BURST=2
PERPLEXITY_CONCURRENCY=3
```

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern async Python web framework
- **PostgreSQL** - Primary database with RLS
- **SQLAlchemy** - Async ORM
- **Alembic** - Database migrations
- **Qdrant** - Vector database for semantic memory
- **Redis/Upstash** - Caching and rate limiting
- **Pydantic** - Data validation
- **Cryptography** - API key encryption

### Frontend
- **Next.js 16** - React framework with App Router
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS 4** - Utility-first CSS
- **Framer Motion** - Animation library
- **Radix UI** - Accessible component primitives
- **Recharts** - Data visualization
- **shadcn/ui** - Component library

### Infrastructure
- **Docker Compose** - Local development environment
- **PostgreSQL 15** - Relational database
- **Qdrant** - Vector search engine
- **Redis 7** - In-memory data store

---

## 🎨 System Techniques

### Intelligent Routing Algorithm

```python
# Routing logic prioritizes:
1. Intent detection (web search, coding, reasoning, etc.)
2. Cost optimization (cheapest capable model)
3. Performance (latency monitoring)
4. Context length (long conversations → Gemini)
5. Fallback chain (primary → backup → default)
```

### Memory Coalescing

- **Deduplication**: Concurrent identical requests share single API call
- **Key Generation**: Based on provider, model, messages, thread
- **TTL**: 5-second window for coalescing
- **Leader-Follower**: One request executes, others wait and share result

### Context Management

- **Rolling Memory**: Last N turns + summary + profile facts
- **Smart Truncation**: Preserves system messages and recent context
- **Cross-Provider Context**: Memory persists across provider switches
- **Semantic Retrieval**: Vector search for relevant past context

### Response Streaming

- **Server-Sent Events**: Real-time streaming via SSE
- **Thinking Preamble**: Structured thinking/searching display
- **Chunk Processing**: Character-by-character or token-by-token
- **Error Handling**: Graceful fallback on stream errors

---

## 📚 API Endpoints

### Core Endpoints

```
POST   /api/threads                    # Create thread
GET    /api/threads/{id}               # Get thread
POST   /api/threads/{id}/messages      # Send message (non-streaming)
POST   /api/threads/{id}/messages/stream  # Send message (streaming)
GET    /api/threads/{id}/messages      # Get message history
```

### Provider Management

```
POST   /api/orgs/{org_id}/provider-keys    # Add API key
GET    /api/orgs/{org_id}/provider-keys     # List keys
PUT    /api/orgs/{org_id}/provider-keys/{id}  # Update key
DELETE /api/orgs/{org_id}/provider-keys/{id}  # Delete key
```

### Full API Documentation

Visit http://localhost:8000/docs for interactive API documentation.

---

## 🔧 Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Code Quality

```bash
# Backend linting
cd backend
black .
ruff check .

# Frontend linting
cd frontend
npm run lint
```

### Database Migrations

```bash
cd backend

# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## 📖 Documentation

Comprehensive documentation is available:

- **[Environment Setup Guide](./ENV_SETUP_GUIDE.md)** - Complete guide to setting up environment variables
- **[System Design](./docs/SYSTEM_DESIGN.md)** - Architecture overview
- **[Intelligent Routing Guide](./docs/INTELLIGENT_ROUTING_GUIDE.md)** - How routing works
- **[Provider Switching Guide](./docs/PROVIDER_SWITCHING_GUIDE.md)** - Switching providers
- **[Quick Start Guide](./QUICK_START_GUIDE.md)** - Get started quickly
- **[API Reference](./docs/API_REFERENCE.md)** - API documentation

---

## 👥 AWS Credentials & Secrets Management

### For Team Members: Getting Started with AWS

#### Prerequisites
- You need AWS credentials from your team lead
- You should have `developer-credentials.txt` with your access keys
- AWS CLI installed: `brew install awscli` (macOS) or see [AWS CLI docs](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

#### Step-by-Step Setup

**Step 1: Configure AWS Credentials**

```bash
aws configure
```

When prompted, enter:
```
AWS Access Key ID: [from developer-credentials.txt]
AWS Secret Access Key: [from developer-credentials.txt]
Default region: us-east-1
Default output format: json
```

This creates `~/.aws/credentials` and `~/.aws/config` on your machine.

**Step 2: Verify AWS Configuration**

```bash
# Check that AWS is configured correctly
aws sts get-caller-identity
# Output should show your AWS account info
```

**Step 3: Fetch Secrets from Parameter Store**

```bash
# From project root directory
./scripts/fetch-secrets.sh

# This fetches all 47+ parameters from AWS Parameter Store and creates:
# - backend/.env.local (backend environment variables)
# - frontend/.env.local (frontend environment variables)
```

**Step 4: Verify All Secrets Loaded**

```bash
# Verify that all required secrets are present
./scripts/verify-all-secrets.sh

# List all parameters in Parameter Store
./scripts/list-all-parameters.sh
```

**Step 5: Continue with Setup**

Your environment files are now ready! Continue with the rest of the setup:
- Step 6 onwards from the **Quick Reference** section above

#### Common AWS Issues

| Issue | Solution |
|-------|----------|
| "Unable to locate credentials" | Run `aws configure` and ensure credentials are in `~/.aws/credentials` |
| "UnauthorizedOperation" | Check that your IAM user has `ssm:GetParameter` permissions |
| "Parameter not found" | Ensure your region is `us-east-1` where parameters are stored |
| "Access Denied" | Verify credentials with `aws sts get-caller-identity` |

---

### For Team Leads: Setting Up AWS for the Team

#### Prerequisites
- AWS Account with administrator access
- AWS CLI installed and configured
- At least one IAM user created for secrets management

#### Step-by-Step Setup

**Step 1: Create IAM Policy for Developers**

```bash
# Create IAM policy from template (see scripts/setup-iam-policy.json)
# This policy allows developers to read parameters from Parameter Store
aws iam create-policy \
  --policy-name SyntraParameterStoreAccess \
  --policy-document file://scripts/setup-iam-policy.json
```

**Step 2: Create IAM Users for Each Developer**

```bash
# Create IAM user
aws iam create-user --user-name developer-1

# Attach policy to user
aws iam attach-user-policy \
  --user-name developer-1 \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/SyntraParameterStoreAccess

# Create access keys
aws iam create-access-key --user-name developer-1
```

**Step 3: Share Credentials with Developers**

Create a secure `developer-credentials.txt` file with the format:
```
DEVELOPER CREDENTIALS FOR SYNTRA

Access Key ID: AKIA...
Secret Access Key: wJ+...

AWS Region: us-east-1

DO NOT SHARE OR COMMIT THIS FILE!
Each developer needs their own credentials.
```

Send to developers through secure channel (not email/Slack).

**Step 4: Upload Secrets to Parameter Store**

```bash
# First, ensure your backend/.env and frontend/.env.local have the latest values
# Then run:
./scripts/setup-parameter-store.sh

# This uploads all parameters with names:
# - /syntra/backend/DATABASE_URL
# - /syntra/backend/QDRANT_URL
# - /syntra/frontend/NEXT_PUBLIC_API_URL
# ... (and 44+ more parameters)

# Verify upload
./scripts/verify-all-secrets.sh
```

**Step 5: Update All Parameters**

If you need to update a parameter later:

```bash
# Update single parameter
aws ssm put-parameter \
  --name /syntra/backend/DATABASE_URL \
  --value "postgresql+asyncpg://..." \
  --overwrite

# Or update multiple from script
./scripts/setup-parameter-store.sh  # Re-run to update all
```

#### Managing Credentials Securely

**Best Practices:**
1. ✅ Rotate developer credentials every 90 days
2. ✅ Never commit credentials to git
3. ✅ Use AWS Secrets Manager for production secrets
4. ✅ Use individual IAM users per developer (not shared credentials)
5. ✅ Enable CloudTrail to audit Parameter Store access
6. ✅ Use separate AWS accounts for prod/staging/dev

**Security Checklist:**
- [ ] All parameters use `/syntra/` prefix for organization
- [ ] Parameters are stored in `us-east-1` region
- [ ] IAM policies follow least-privilege principle
- [ ] Developer credentials are rotated regularly
- [ ] Access logs are monitored
- [ ] Sensitive values are not logged anywhere

---

## 🚢 Deployment

### Production Checklist

- [ ] Use AWS Secrets Manager or Parameter Store for production secrets
- [ ] Configure production database (PostgreSQL)
- [ ] Set up Qdrant cluster
- [ ] Configure Redis/Upstash
- [ ] Set CORS origins
- [ ] Enable HTTPS
- [ ] Configure rate limits
- [ ] Set up monitoring (Grafana, Prometheus)
- [ ] Configure logging
- [ ] Set up backup strategy
- [ ] Enable IAM-based secret access for application
- [ ] Rotate developer credentials regularly

### Docker Production

```bash
# Build images
docker build -t syntra-backend ./backend
docker build -t syntra-frontend ./frontend

# Run with docker-compose.prod.yml
docker compose -f docker-compose.prod.yml up -d
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🆘 Support & Troubleshooting

### Common Issues

**"Missing environment variable" errors:**
- ✅ Check that `.env` files exist: `backend/.env` and `frontend/.env.local`
- ✅ Verify variable names match exactly (case-sensitive)
- ✅ Restart the application after changing `.env` files
- ✅ Run `./setup-env.sh` to create environment files from templates

**Backend won't start:**
- ✅ Check that database, Qdrant, and Redis are running: `docker compose ps`
- ✅ Verify `DATABASE_URL`, `QDRANT_URL`, and `UPSTASH_REDIS_URL` in `backend/.env`
- ✅ Ensure migrations are run: `cd backend && alembic upgrade head`
- ✅ Check backend logs for specific error messages

**Frontend can't connect to backend:**
- ✅ Verify `NEXT_PUBLIC_API_URL` in `frontend/.env.local` matches your backend URL
- ✅ Ensure backend is running on the port specified in `NEXT_PUBLIC_API_URL`
- ✅ Check CORS settings in backend config
- ✅ Verify backend is accessible: `curl http://localhost:8000/health`

**API keys not working:**
- ✅ Verify keys are set correctly in `backend/.env`
- ✅ Check that keys are valid and have proper permissions
- ✅ For frontend workflow features, ensure backend `.env` is accessible
- ✅ Some features work without API keys (using mock mode in development)

**Need more help?**
- 📖 **Environment Setup**: See [ENV_SETUP_GUIDE.md](./ENV_SETUP_GUIDE.md) for detailed troubleshooting
- 📚 **Documentation**: See [`/docs`](./docs/) directory
- 🐛 **Issues**: [GitHub Issues](https://github.com/your-org/syntra/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/your-org/syntra/discussions)

---

## 🎯 Roadmap

- [x] Phase 1: Multi-provider routing
- [x] Phase 2: Memory & context management
- [x] Phase 3: Unified persona
- [x] Phase 4: Enterprise features
- [ ] Phase 5: Advanced analytics & optimization

---

**Built with ❤️ by the Syntra Team**
