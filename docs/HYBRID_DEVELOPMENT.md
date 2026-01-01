# Hybrid Development Strategy

Syntra uses a **hybrid development approach** for optimal developer experience and production performance:

- **Local Development** → Local PostgreSQL (fast, reliable)
- **Production** → Supabase (managed, scalable, built-in AI features)

## 🚀 Quick Start (New Developer)

```bash
# 1. Clone repository
git clone <your-repo>
cd syntra

# 2. Run setup script
chmod +x scripts/dev-setup.sh
./scripts/dev-setup.sh

# 3. Configure environment
# Add your API keys to backend/.env and frontend/.env.local

# 4. Start development servers
chmod +x scripts/dev-start.sh
./scripts/dev-start.sh
```

Your app will be running at:
- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000

## 📋 Manual Setup (Alternative)

### Prerequisites
- **macOS** (Linux/Windows: adapt PostgreSQL installation)
- **Node.js** 18+ 
- **Python** 3.11+
- **Homebrew** (for PostgreSQL)

### Backend Setup
```bash
# 1. Install PostgreSQL
brew install postgresql@14
brew services start postgresql@14

# 2. Create database
createdb dac

# 3. Setup Python environment
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Configure environment
cp env.example .env
# Edit .env with your API keys

# 5. Create database tables
python -c "
import asyncio
from app.database import engine, Base
from app.models import *

async def create_tables():
    async with engine.begin() as conn:
        from app.models import Org, User, Thread, Message, AuditLog, ProviderKey, RouterRun
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=[
            Org.__table__, User.__table__, Thread.__table__, Message.__table__, 
            AuditLog.__table__, ProviderKey.__table__, RouterRun.__table__
        ]))
    print('Tables created')

asyncio.run(create_tables())
"

# 6. Create default organization
psql -d dac -c "INSERT INTO orgs (id, name, slug) VALUES ('org_demo', 'Demo Organization', 'demo') ON CONFLICT DO NOTHING;"

# 7. Start backend
python3 main.py
```

### Frontend Setup
```bash
# 1. Install dependencies
cd frontend
npm install

# 2. Configure environment
cp env.example .env.local
# Edit .env.local with your Clerk keys

# 3. Start frontend
npm run dev
```

## 🔑 Required API Keys

### Backend (.env)
```bash
# AI Providers (get your own)
OPENAI_API_KEY=sk-...
PERPLEXITY_API_KEY=pplx-...
GOOGLE_API_KEY=AIza...

# Clerk Authentication
CLERK_SECRET_KEY=sk_test_...

# Security (generate random)
SECRET_KEY=your-jwt-secret
ENCRYPTION_KEY=your-fernet-key
```

### Frontend (.env.local)
```bash
# Clerk Authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
```

## 🗃️ Database Architecture

### Local Development
- **PostgreSQL** on localhost:5432
- **Database**: `dac`
- **Tables**: Basic schema (no vector dependencies)
- **Memory**: Disabled (set `MEMORY_ENABLED=0`)

### Production 
- **Supabase** PostgreSQL with pgvector
- **Tables**: Full schema with vector support
- **Memory**: Enabled (`MEMORY_ENABLED=1`)
- **Features**: All AI features enabled

## 🔄 Migration Strategy

### Development → Production
1. **Database**: Automatic migration via Alembic during deployment
2. **Environment**: Switch `DATABASE_URL` to Supabase
3. **Features**: Enable memory and vector features
4. **Scaling**: Supabase handles connection pooling and scaling

## 🛠️ Development Workflow

### Daily Development
```bash
# Start both servers
./scripts/dev-start.sh

# Or manually:
# Terminal 1: Backend
cd backend && source venv/bin/activate && python3 main.py

# Terminal 2: Frontend  
cd frontend && npm run dev
```

### Adding Features
1. Develop locally with PostgreSQL
2. Test against local backend
3. Commit changes
4. Deploy triggers production migration

### Database Changes
1. Create Alembic migration: `alembic revision -m "description"`
2. Test locally: `alembic upgrade head`
3. Commit migration file
4. Production deployment runs migrations automatically

## 🚀 Production Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed production setup with Supabase.

## 🔧 Troubleshooting

### Common Issues

**PostgreSQL not starting**
```bash
brew services restart postgresql@14
```

**Database connection failed**
```bash
# Check if database exists
psql -l | grep dac

# Recreate if needed
dropdb dac && createdb dac
```

**Python dependencies**
```bash
cd backend
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Port conflicts**
```bash
# Check what's using ports
lsof -i :3000  # Frontend
lsof -i :8000  # Backend
lsof -i :5432  # PostgreSQL
```

### Getting Help

1. Check logs in `backend/backend.log`
2. Verify environment variables are set
3. Ensure PostgreSQL is running
4. Check network connectivity

## 📚 Related Documentation

- [API Documentation](./API.md)
- [Production Deployment](./DEPLOYMENT.md)  
- [Supabase Migration Guide](./SUPABASE_MIGRATION.md)
- [Contributing Guide](./CONTRIBUTING.md)