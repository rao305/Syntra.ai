#!/bin/bash

# AWS Systems Manager Parameter Store Setup Script
# This script uploads all secrets to AWS Parameter Store for team sharing
# Cost: FREE (Standard parameters)
#
# IMPORTANT: Before running this, ensure:
# 1. You have AWS CLI installed: brew install awscli (macOS)
# 2. You have AWS credentials configured: aws configure
# 3. You have .env file with your actual secrets in /backend/.env

set -e  # Exit on any error

echo "🔐 Setting up AWS Systems Manager Parameter Store..."
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Install with: brew install awscli"
    exit 1
fi

# Check if .env files exist
if [ ! -f "backend/.env" ]; then
    echo "❌ backend/.env not found. Please create it first."
    exit 1
fi

# Load secrets from backend .env first
set -a
source backend/.env
set +a

# Also load from frontend .env.local if it exists (frontend vars override backend)
if [ -f "frontend/.env.local" ]; then
    echo "📝 Also reading frontend/.env.local..."
    set -a
    source frontend/.env.local
    set +a
fi

# Set defaults for variables that have defaults in config.py but might not be in .env
CORS_ORIGINS=${CORS_ORIGINS:-"http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001"}
SUPERMEMORY_API_BASE_URL=${SUPERMEMORY_API_BASE_URL:-"https://api.supermemory.ai"}
ALGORITHM=${ALGORITHM:-"HS256"}
ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES:-"30"}
FEATURE_COREWRITE=${FEATURE_COREWRITE:-"false"}
ENVIRONMENT=${ENVIRONMENT:-"development"}
FRONTEND_URL=${FRONTEND_URL:-"http://localhost:3000"}

# AWS Region (change if needed)
AWS_REGION="us-east-1"

echo "📝 Reading secrets from backend/.env"
if [ -f "frontend/.env.local" ]; then
    echo "   and frontend/.env.local..."
fi
echo "🌍 Using region: $AWS_REGION"
echo ""

# Function to safely put parameter
# Usage: put_param KEY VALUE TYPE [required|optional]
put_param() {
    local key=$1
    local value=$2
    local key_type=$3
    local required=${4:-required}  # Default to required

    if [ -z "$value" ]; then
        if [ "$required" = "required" ]; then
            echo "❌ $key: REQUIRED but empty value!"
            echo "   Please set $key in backend/.env or frontend/.env.local"
            return 1
        else
            echo "⏭️  Skipping $key (optional, empty value)"
            return 0
        fi
    fi

    # Check for common placeholder patterns
    if [[ "$value" == *"your-"* ]] || [[ "$value" == *"change-this"* ]] || [[ "$value" == *"placeholder"* ]] || [[ "$value" == "sk_test_"* && ${#value} -lt 20 ]] || [[ "$value" == "pk_test_"* && ${#value} -lt 20 ]]; then
        echo "⚠️  WARNING: $key appears to have a placeholder value: ${value:0:30}..."
        echo "   Are you sure you want to upload this? (This might be intentional for some config)"
    fi

    echo "📤 Uploading $key to Parameter Store..."
    
    # Check if parameter exists
    if aws ssm get-parameter --name "/syntra/$key" --region "$AWS_REGION" &>/dev/null; then
        # Parameter exists, update without tags (tags can't be updated with overwrite)
        if aws ssm put-parameter \
            --name "/syntra/$key" \
            --value "$value" \
            --type "$key_type" \
            --overwrite \
            --region "$AWS_REGION" \
            2>&1; then
            echo "✅ $key updated successfully"
        else
            echo "❌ Failed to update $key"
            return 1
        fi
    else
        # Parameter doesn't exist, create with tags
        if aws ssm put-parameter \
            --name "/syntra/$key" \
            --value "$value" \
            --type "$key_type" \
            --region "$AWS_REGION" \
            --tags Key=app,Value=syntra Key=env,Value=development \
            2>&1; then
            echo "✅ $key uploaded successfully"
        else
            echo "❌ Failed to upload $key"
            return 1
        fi
    fi
}

ERRORS=0

# Upload all secrets (SecureString for sensitive values, String for non-sensitive)
echo "🔒 Uploading required secrets as SecureString (encrypted)..."
put_param "SECRET_KEY" "$SECRET_KEY" "SecureString" "required" || ERRORS=$((ERRORS + 1))
put_param "ENCRYPTION_KEY" "$ENCRYPTION_KEY" "SecureString" "required" || ERRORS=$((ERRORS + 1))
put_param "CLERK_SECRET_KEY" "$CLERK_SECRET_KEY" "SecureString" "required" || ERRORS=$((ERRORS + 1))
put_param "OPENAI_API_KEY" "$OPENAI_API_KEY" "SecureString" "required" || ERRORS=$((ERRORS + 1))
put_param "GOOGLE_API_KEY" "$GOOGLE_API_KEY" "SecureString" "required" || ERRORS=$((ERRORS + 1))
put_param "PERPLEXITY_API_KEY" "$PERPLEXITY_API_KEY" "SecureString" "required" || ERRORS=$((ERRORS + 1))
put_param "OPENROUTER_API_KEY" "$OPENROUTER_API_KEY" "SecureString" "required" || ERRORS=$((ERRORS + 1))
put_param "KIMI_API_KEY" "$KIMI_API_KEY" "SecureString" "required" || ERRORS=$((ERRORS + 1))
put_param "SUPERMEMORY_API_KEY" "$SUPERMEMORY_API_KEY" "SecureString" "required" || ERRORS=$((ERRORS + 1))

echo ""
echo "🔑 Uploading optional secrets..."
put_param "STRIPE_SECRET_KEY" "$STRIPE_SECRET_KEY" "SecureString" "optional"
put_param "STRIPE_WEBHOOK_SECRET" "$STRIPE_WEBHOOK_SECRET" "SecureString" "optional"
put_param "RESEND_API_KEY" "$RESEND_API_KEY" "SecureString" "optional"
put_param "SMTP_PASSWORD" "$SMTP_PASSWORD" "SecureString" "optional"

echo ""
echo "📝 Uploading required configuration as String..."
put_param "DATABASE_URL" "$DATABASE_URL" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "QDRANT_URL" "$QDRANT_URL" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "UPSTASH_REDIS_URL" "$UPSTASH_REDIS_URL" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "FRONTEND_URL" "$FRONTEND_URL" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "ENVIRONMENT" "$ENVIRONMENT" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "DEFAULT_ORG_ID" "$DEFAULT_ORG_ID" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "ALGORITHM" "$ALGORITHM" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "ACCESS_TOKEN_EXPIRE_MINUTES" "$ACCESS_TOKEN_EXPIRE_MINUTES" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "FEATURE_COREWRITE" "$FEATURE_COREWRITE" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "CORS_ORIGINS" "$CORS_ORIGINS" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "INTELLIGENT_ROUTING_ENABLED" "$INTELLIGENT_ROUTING_ENABLED" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "MEMORY_ENABLED" "$MEMORY_ENABLED" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "DEFAULT_REQUESTS_PER_DAY" "$DEFAULT_REQUESTS_PER_DAY" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "DEFAULT_TOKENS_PER_DAY" "$DEFAULT_TOKENS_PER_DAY" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "PERPLEXITY_RPS" "$PERPLEXITY_RPS" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "PERPLEXITY_BURST" "$PERPLEXITY_BURST" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "PERPLEXITY_CONCURRENCY" "$PERPLEXITY_CONCURRENCY" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "OPENAI_RPS" "$OPENAI_RPS" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "OPENAI_BURST" "$OPENAI_BURST" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "OPENAI_CONCURRENCY" "$OPENAI_CONCURRENCY" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "GEMINI_RPS" "$GEMINI_RPS" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "GEMINI_BURST" "$GEMINI_BURST" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "GEMINI_CONCURRENCY" "$GEMINI_CONCURRENCY" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "OPENROUTER_RPS" "$OPENROUTER_RPS" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "OPENROUTER_BURST" "$OPENROUTER_BURST" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "OPENROUTER_CONCURRENCY" "$OPENROUTER_CONCURRENCY" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "SUPERMEMORY_API_BASE_URL" "$SUPERMEMORY_API_BASE_URL" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "NEXT_PUBLIC_API_URL" "$NEXT_PUBLIC_API_URL" "String" "required" || ERRORS=$((ERRORS + 1))
put_param "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY" "$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY" "String" "required" || ERRORS=$((ERRORS + 1))

echo ""
echo "📧 Uploading optional configuration..."
put_param "QDRANT_API_KEY" "$QDRANT_API_KEY" "String" "optional"
put_param "UPSTASH_REDIS_TOKEN" "$UPSTASH_REDIS_TOKEN" "String" "optional"
put_param "EMAIL_FROM" "$EMAIL_FROM" "String" "optional"
put_param "SMTP_HOST" "$SMTP_HOST" "String" "optional"
put_param "SMTP_PORT" "$SMTP_PORT" "String" "optional"
put_param "SMTP_USER" "$SMTP_USER" "String" "optional"
put_param "STRIPE_PUBLISHABLE_KEY" "$STRIPE_PUBLISHABLE_KEY" "String" "optional"
put_param "STRIPE_PRICE_ID" "$STRIPE_PRICE_ID" "String" "optional"
put_param "FIREBASE_PROJECT_ID" "$FIREBASE_PROJECT_ID" "String" "optional"
put_param "FIREBASE_CREDENTIALS_FILE" "$FIREBASE_CREDENTIALS_FILE" "String" "optional"
put_param "NEXT_PUBLIC_FIREBASE_API_KEY" "$NEXT_PUBLIC_FIREBASE_API_KEY" "String" "optional"
put_param "NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN" "$NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN" "String" "optional"
put_param "NEXT_PUBLIC_FIREBASE_PROJECT_ID" "$NEXT_PUBLIC_FIREBASE_PROJECT_ID" "String" "optional"
put_param "NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET" "$NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET" "String" "optional"
put_param "NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID" "$NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID" "String" "optional"
put_param "NEXT_PUBLIC_FIREBASE_APP_ID" "$NEXT_PUBLIC_FIREBASE_APP_ID" "String" "optional"
put_param "NEXT_PUBLIC_APP_URL" "$NEXT_PUBLIC_APP_URL" "String" "optional"
put_param "NEXT_PUBLIC_CLERK_FRONTEND_API" "$NEXT_PUBLIC_CLERK_FRONTEND_API" "String" "optional"
put_param "NEXT_PUBLIC_WS_URL" "$NEXT_PUBLIC_WS_URL" "String" "optional"
put_param "DAC_FORCE_MOCK" "$DAC_FORCE_MOCK" "String" "optional"

echo ""
if [ $ERRORS -gt 0 ]; then
    echo "❌ Failed to upload $ERRORS required secret(s)!"
    echo ""
    echo "💡 Please set all required environment variables in backend/.env and frontend/.env.local"
    echo "   Then run this script again."
    exit 1
fi

echo "✅ All required secrets uploaded to AWS Parameter Store!"
echo ""
echo "📋 Your secrets are now at:"
echo "   /syntra/OPENAI_API_KEY"
echo "   /syntra/DATABASE_URL"
echo "   /syntra/... (and more)"
echo ""
echo "🔗 View in AWS Console:"
echo "   https://console.aws.amazon.com/systems-manager/parameters"
echo ""
echo "👥 Next steps for your team:"
echo "   1. Give developers IAM permissions (see setup-iam-policy.json)"
echo "   2. They run: ./scripts/fetch-secrets.sh"
echo "   3. Secrets load to .env.local (gitignored)"
