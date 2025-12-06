#!/bin/bash

# Fetch Secrets from AWS Parameter Store
# FOR DEVELOPERS: Run this once to fetch all secrets into .env.local
#
# Usage: ./scripts/fetch-secrets.sh
#
# This script:
# 1. Fetches all secrets from AWS Parameter Store
# 2. Creates .env.local (gitignored)
# 3. Loads them automatically with 'source .env.local'

set -e  # Exit on error

echo "🔐 Fetching secrets from AWS Parameter Store..."
echo ""

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not installed"
    echo "   macOS: brew install awscli"
    echo "   Linux: apt-get install awscli"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &>/dev/null; then
    echo "❌ AWS credentials not configured"
    echo "   Run: aws configure"
    echo "   Ask your team lead for AWS access keys"
    exit 1
fi

AWS_REGION="us-east-1"
BACKEND_ENV_FILE="backend/.env.local"
FRONTEND_ENV_FILE="frontend/.env.local"

echo "📍 Region: $AWS_REGION"
echo "📝 Creating: $BACKEND_ENV_FILE"
if [ -f "frontend/.env.local" ] || [ -n "$(aws ssm get-parameter --name '/syntra/NEXT_PUBLIC_API_URL' --region $AWS_REGION 2>/dev/null)" ]; then
    echo "📝 Creating: $FRONTEND_ENV_FILE"
fi
echo ""

# Function to fetch parameter
# Usage: fetch_param KEY [required|optional]
fetch_param() {
    local key=$1
    local required=${2:-required}  # Default to required
    local aws_param_name="/syntra/$key"

    # Try to fetch the parameter
    local value=$(aws ssm get-parameter \
        --name "$aws_param_name" \
        --with-decryption \
        --query 'Parameter.Value' \
        --output text \
        --region "$AWS_REGION" \
        2>/dev/null || echo "")

    if [ -z "$value" ]; then
        if [ "$required" = "required" ]; then
            echo "❌ $key: REQUIRED but not found in Parameter Store"
            return 1
        else
            echo "⏭️  Skipping $key (optional, not found)"
            return 0
        fi
    fi

    # Determine which file to write to based on variable name
    if [[ "$key" == NEXT_PUBLIC_* ]]; then
        echo "$key=$value" >> "$FRONTEND_ENV_FILE"
        echo "✅ $key → frontend"
    else
        echo "$key=$value" >> "$BACKEND_ENV_FILE"
        echo "✅ $key → backend"
    fi
    return 0
}

# Clear existing .env.local files
> "$BACKEND_ENV_FILE"
> "$FRONTEND_ENV_FILE"

ERRORS=0

echo "🔒 Fetching required secrets..."
fetch_param "SECRET_KEY" "required" || ERRORS=$((ERRORS + 1))
fetch_param "ENCRYPTION_KEY" "required" || ERRORS=$((ERRORS + 1))
fetch_param "CLERK_SECRET_KEY" "required" || ERRORS=$((ERRORS + 1))
fetch_param "DATABASE_URL" "required" || ERRORS=$((ERRORS + 1))
fetch_param "QDRANT_URL" "required" || ERRORS=$((ERRORS + 1))
fetch_param "UPSTASH_REDIS_URL" "required" || ERRORS=$((ERRORS + 1))
fetch_param "NEXT_PUBLIC_API_URL" "required" || ERRORS=$((ERRORS + 1))
fetch_param "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY" "required" || ERRORS=$((ERRORS + 1))

echo ""
echo "🔑 Fetching API keys (required)..."
fetch_param "OPENAI_API_KEY" "required" || ERRORS=$((ERRORS + 1))
fetch_param "GOOGLE_API_KEY" "required" || ERRORS=$((ERRORS + 1))
fetch_param "PERPLEXITY_API_KEY" "required" || ERRORS=$((ERRORS + 1))
fetch_param "OPENROUTER_API_KEY" "required" || ERRORS=$((ERRORS + 1))
fetch_param "KIMI_API_KEY" "required" || ERRORS=$((ERRORS + 1))
fetch_param "SUPERMEMORY_API_KEY" "required" || ERRORS=$((ERRORS + 1))

echo ""
echo "📝 Fetching required configuration..."
fetch_param "FRONTEND_URL" "required" || ERRORS=$((ERRORS + 1))
fetch_param "ENVIRONMENT" "required" || ERRORS=$((ERRORS + 1))
fetch_param "DEFAULT_ORG_ID" "required" || ERRORS=$((ERRORS + 1))
fetch_param "ALGORITHM" "required" || ERRORS=$((ERRORS + 1))
fetch_param "ACCESS_TOKEN_EXPIRE_MINUTES" "required" || ERRORS=$((ERRORS + 1))
fetch_param "FEATURE_COREWRITE" "required" || ERRORS=$((ERRORS + 1))
fetch_param "CORS_ORIGINS" "required" || ERRORS=$((ERRORS + 1))
fetch_param "INTELLIGENT_ROUTING_ENABLED" "required" || ERRORS=$((ERRORS + 1))
fetch_param "MEMORY_ENABLED" "required" || ERRORS=$((ERRORS + 1))
fetch_param "DEFAULT_REQUESTS_PER_DAY" "required" || ERRORS=$((ERRORS + 1))
fetch_param "DEFAULT_TOKENS_PER_DAY" "required" || ERRORS=$((ERRORS + 1))
fetch_param "PERPLEXITY_RPS" "required" || ERRORS=$((ERRORS + 1))
fetch_param "PERPLEXITY_BURST" "required" || ERRORS=$((ERRORS + 1))
fetch_param "PERPLEXITY_CONCURRENCY" "required" || ERRORS=$((ERRORS + 1))
fetch_param "OPENAI_RPS" "required" || ERRORS=$((ERRORS + 1))
fetch_param "OPENAI_BURST" "required" || ERRORS=$((ERRORS + 1))
fetch_param "OPENAI_CONCURRENCY" "required" || ERRORS=$((ERRORS + 1))
fetch_param "GEMINI_RPS" "required" || ERRORS=$((ERRORS + 1))
fetch_param "GEMINI_BURST" "required" || ERRORS=$((ERRORS + 1))
fetch_param "GEMINI_CONCURRENCY" "required" || ERRORS=$((ERRORS + 1))
fetch_param "OPENROUTER_RPS" "required" || ERRORS=$((ERRORS + 1))
fetch_param "OPENROUTER_BURST" "required" || ERRORS=$((ERRORS + 1))
fetch_param "OPENROUTER_CONCURRENCY" "required" || ERRORS=$((ERRORS + 1))
fetch_param "SUPERMEMORY_API_BASE_URL" "required" || ERRORS=$((ERRORS + 1))

echo ""
echo "📧 Fetching optional configuration..."
fetch_param "QDRANT_API_KEY" "optional"
fetch_param "UPSTASH_REDIS_TOKEN" "optional"
fetch_param "EMAIL_FROM" "optional"
fetch_param "SMTP_HOST" "optional"
fetch_param "SMTP_PORT" "optional"
fetch_param "SMTP_USER" "optional"
fetch_param "SMTP_PASSWORD" "optional"
fetch_param "RESEND_API_KEY" "optional"
fetch_param "STRIPE_SECRET_KEY" "optional"
fetch_param "STRIPE_PUBLISHABLE_KEY" "optional"
fetch_param "STRIPE_WEBHOOK_SECRET" "optional"
fetch_param "STRIPE_PRICE_ID" "optional"
fetch_param "FIREBASE_PROJECT_ID" "optional"
fetch_param "FIREBASE_CREDENTIALS_FILE" "optional"
fetch_param "NEXT_PUBLIC_FIREBASE_API_KEY" "optional"
fetch_param "NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN" "optional"
fetch_param "NEXT_PUBLIC_FIREBASE_PROJECT_ID" "optional"
fetch_param "NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET" "optional"
fetch_param "NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID" "optional"
fetch_param "NEXT_PUBLIC_FIREBASE_APP_ID" "optional"
fetch_param "NEXT_PUBLIC_APP_URL" "optional"
fetch_param "NEXT_PUBLIC_CLERK_FRONTEND_API" "optional"
fetch_param "NEXT_PUBLIC_WS_URL" "optional"
fetch_param "DAC_FORCE_MOCK" "optional"

echo ""
if [ $ERRORS -gt 0 ]; then
    echo "❌ Failed to fetch $ERRORS required secret(s)!"
    echo ""
    echo "💡 Make sure all required secrets are uploaded to AWS Parameter Store:"
    echo "   ./scripts/setup-parameter-store.sh"
    exit 1
fi

echo ""
echo "✅ Secrets fetched successfully!"
echo ""
echo "📝 Files created:"
echo "   Backend:  $BACKEND_ENV_FILE"
if [ -f "$FRONTEND_ENV_FILE" ] && [ -s "$FRONTEND_ENV_FILE" ]; then
    echo "   Frontend: $FRONTEND_ENV_FILE"
fi
echo ""
echo "   (These files are gitignored - never commit them)"
echo ""
echo "🚀 Ready to develop:"
echo "   Backend:  cd backend && source .env.local && python main.py"
echo "   Frontend: cd frontend && npm run dev (uses .env.local automatically)"
echo ""
echo "💡 TIP: Add this to your shell profile (~/.zshrc or ~/.bashrc):"
echo '   if [ -f backend/.env.local ]; then source backend/.env.local; fi'
echo "   Then reload: source ~/.zshrc"
