# Production Setup with Supabase

This guide covers deploying Syntra to production using Supabase as the database and hosting platform.

## 🏗️ Architecture Overview

**Local Development**: PostgreSQL + Local servers
**Production**: Supabase (DB + Edge Functions) + Frontend hosting

## 🔧 Supabase Setup

### 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Create new project
3. Choose a region close to your users
4. Set a strong database password
5. Wait for project to initialize (~2 minutes)

### 2. Enable Extensions

In Supabase SQL Editor, run:

```sql
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";  -- For AI embeddings
```

### 3. Get Connection Details

From Supabase Dashboard > Settings > Database:

```bash
# Direct connection (for migrations)
Host: db.PROJECT_ID.supabase.co
Port: 5432
Database: postgres
User: postgres
Password: [your-password]

# Connection pooler (for production app)
Host: db.PROJECT_ID.supabase.co  
Port: 6543 (transaction mode)
```

From API Settings:
```bash
SUPABASE_URL=https://PROJECT_ID.supabase.co
SUPABASE_ANON_KEY=eyJ... (public key)
SUPABASE_SERVICE_KEY=eyJ... (secret key - keep secure!)
```

## 🗃️ Database Migration

### Option A: Direct Migration (Recommended)

```bash
# 1. Set production environment
export DATABASE_URL="postgresql+asyncpg://postgres:PASSWORD@db.PROJECT_ID.supabase.co:5432/postgres"

# 2. Run migrations
cd backend
source venv/bin/activate
alembic upgrade head

# 3. Create default organization
psql $DATABASE_URL -c "INSERT INTO orgs (id, name, slug) VALUES ('org_demo', 'Demo Organization', 'demo') ON CONFLICT DO NOTHING;"
```

### Option B: Schema Export/Import

```bash
# 1. Export local schema
pg_dump -s dac > schema.sql

# 2. Import to Supabase
psql "postgresql://postgres:PASSWORD@db.PROJECT_ID.supabase.co:5432/postgres" < schema.sql
```

## 🚀 Backend Deployment

### Railway (Recommended)
1. Connect GitHub repository to Railway
2. Set environment variables:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@db.PROJECT_ID.supabase.co:6543/postgres

# Supabase
SUPABASE_URL=https://PROJECT_ID.supabase.co
SUPABASE_SERVICE_KEY=eyJ...

# Production settings
ENVIRONMENT=production
MEMORY_ENABLED=1
INTELLIGENT_ROUTING_ENABLED=1

# Security (generate new keys for production!)
SECRET_KEY=your-production-jwt-secret
ENCRYPTION_KEY=your-production-fernet-key

# Add all your AI provider API keys
OPENAI_API_KEY=sk-...
PERPLEXITY_API_KEY=pplx-...
GOOGLE_API_KEY=AIza...
```

### Other Platforms
- **Render**: Similar to Railway
- **Heroku**: Add Procfile (already included)
- **Vercel**: Deploy as serverless functions
- **Docker**: Use included Dockerfile

## 🌐 Frontend Deployment

### Vercel (Recommended)
1. Connect GitHub repository to Vercel
2. Set build command: `npm run build`
3. Set environment variables:

```bash
# API
NEXT_PUBLIC_API_URL=https://your-backend.railway.app

# Clerk (use production keys)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
CLERK_SECRET_KEY=sk_live_...

# Environment
NODE_ENV=production
```

### Other Platforms
- **Netlify**: Deploy via GitHub integration
- **Cloudflare Pages**: Connect repository
- **AWS Amplify**: Use GitHub deployment

## 🔐 Security Configuration

### Environment Variables

**Never commit these to git:**
- Database passwords
- API keys
- JWT secrets
- Service keys

**Use platform environment variable systems:**
- Railway: Environment tab
- Vercel: Environment Variables section  
- Render: Environment tab

### Generate Secure Keys

```bash
# JWT Secret (32+ chars)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Fernet Encryption Key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## 🔧 Production Configuration

### Backend Performance
```bash
# Connection pooling (via Supabase)
DATABASE_URL=...db.PROJECT_ID.supabase.co:6543/postgres  # Note port 6543

# Higher rate limits
DEFAULT_REQUESTS_PER_DAY=10000
DEFAULT_TOKENS_PER_DAY=1000000

# Enable all features
MEMORY_ENABLED=1
INTELLIGENT_ROUTING_ENABLED=1
```

### Frontend Optimization
```bash
# Production API URL
NEXT_PUBLIC_API_URL=https://your-backend.railway.app

# Production Clerk keys
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
```

## 📊 Monitoring & Analytics

### Supabase Dashboard
- Database metrics
- Query performance
- Connection pooling stats
- Storage usage

### Application Monitoring
- Add Sentry for error tracking
- Use Vercel Analytics for frontend metrics
- Railway provides backend metrics

### Health Checks
```bash
# Backend health endpoint
curl https://your-backend.railway.app/health

# Database connectivity  
psql $DATABASE_URL -c "SELECT version();"
```

## 🔄 CI/CD Pipeline

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Run Database Migrations
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          cd backend
          pip install -r requirements.txt
          alembic upgrade head
          
      # Deployment triggers automatically via platform integration
```

## 🚨 Backup & Recovery

### Automated Backups
Supabase provides automatic daily backups for 7 days (Pro plan for longer retention).

### Manual Backup
```bash
# Full database backup
pg_dump "postgresql://postgres:PASSWORD@db.PROJECT_ID.supabase.co:5432/postgres" > backup.sql

# Data-only backup  
pg_dump --data-only "postgresql://..." > data_backup.sql
```

### Recovery
```bash
# Restore from backup
psql "postgresql://..." < backup.sql
```

## 📚 Next Steps

1. **Set up monitoring**: Add Sentry, analytics
2. **Configure CDN**: Use Cloudflare for global performance  
3. **Set up staging**: Create staging Supabase project
4. **SSL/Security**: Ensure HTTPS everywhere
5. **Performance**: Monitor and optimize queries

## 🔧 Troubleshooting

### Database Connection Issues
- Check Supabase project status
- Verify connection string format
- Test direct vs pooler connection
- Check IP restrictions

### Migration Failures
- Run migrations locally first
- Check for schema conflicts
- Verify extension availability

### Performance Issues
- Monitor Supabase dashboard
- Check connection pooling metrics
- Optimize queries
- Consider read replicas

Need help? Check the [troubleshooting guide](./TROUBLESHOOTING.md) or create an issue.