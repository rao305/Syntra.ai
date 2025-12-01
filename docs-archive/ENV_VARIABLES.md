# Environment Variables Reference

## Frontend (Netlify) Environment Variables

All frontend environment variables must be prefixed with `NEXT_PUBLIC_` to be accessible in the browser.

### Required Variables

```bash
# Backend API URL - REQUIRED
NEXT_PUBLIC_API_URL=https://your-backend-url.railway.app/api
```

### Optional Variables (Firebase Auth)

If you're using Firebase for authentication:

```bash
NEXT_PUBLIC_FIREBASE_API_KEY=your-firebase-api-key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project-id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=your-sender-id
NEXT_PUBLIC_FIREBASE_APP_ID=your-app-id
```

## Backend Environment Variables

These are set in your backend deployment platform (Railway, Render, etc.):

### Database
```bash
DATABASE_URL=postgresql://user:password@host:port/dbname
```

### Qdrant (Vector Database)
```bash
QDRANT_URL=https://your-qdrant-instance.com
QDRANT_API_KEY=your-qdrant-api-key
```

### Redis (Upstash)
```bash
UPSTASH_REDIS_URL=https://your-redis-instance.upstash.io
UPSTASH_REDIS_TOKEN=your-redis-token
```

### Security
```bash
SECRET_KEY=your-secret-key-for-jwt
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENCRYPTION_KEY=your-fernet-encryption-key
```

### Email (Optional)
```bash
EMAIL_FROM=noreply@yourdomain.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
# OR use Resend
RESEND_API_KEY=your-resend-api-key
```

### Stripe (Billing)
```bash
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...
```

### Frontend URL
```bash
FRONTEND_URL=https://your-site.netlify.app
```

### LLM Provider API Keys (Optional - for fallback)
```bash
PERPLEXITY_API_KEY=pplx-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
OPENROUTER_API_KEY=sk-or-...
KIMI_API_KEY=sk-...
```

### Feature Flags
```bash
FEATURE_COREWRITE=false
MEMORY_ENABLED=0
```

### Firebase (Backend)
```bash
FIREBASE_CREDENTIALS_FILE=path/to/service-account.json
# OR
FIREBASE_CREDENTIALS_JSON={"type":"service_account",...}
FIREBASE_PROJECT_ID=your-project-id
```

### Default Organization
```bash
DEFAULT_ORG_ID=org_demo
```

## Setting Environment Variables

### In Netlify (Frontend)
1. Go to Site settings → Environment variables
2. Add each variable with `NEXT_PUBLIC_` prefix
3. Redeploy after adding variables

### In Railway (Backend)
1. Go to your project → Variables
2. Add each variable
3. Redeploy if needed

### In Render (Backend)
1. Go to your service → Environment
2. Add each variable
3. Save and redeploy

## Security Notes

- Never commit `.env` files to Git
- Use platform secrets management for sensitive keys
- Rotate keys regularly
- Use different keys for development and production
- Keep `SECRET_KEY` and `ENCRYPTION_KEY` secure and random




