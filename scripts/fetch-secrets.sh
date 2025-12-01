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
ENV_FILE="backend/.env.local"

echo "📍 Region: $AWS_REGION"
echo "📝 Creating: $ENV_FILE"
echo ""

# Function to fetch parameter
fetch_param() {
    local key=$1
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
        echo "⏭️  Skipping $key (not found in Parameter Store)"
        return
    fi

    echo "$key=$value" >> "$ENV_FILE"
    echo "✅ $key"
}

# Clear existing .env.local
> "$ENV_FILE"

echo "🔒 Fetching secrets..."
fetch_param "OPENAI_API_KEY"
fetch_param "GOOGLE_API_KEY"
fetch_param "PERPLEXITY_API_KEY"
fetch_param "OPENROUTER_API_KEY"
fetch_param "SUPERMEMORY_API_KEY"
fetch_param "STRIPE_SECRET_KEY"
fetch_param "STRIPE_WEBHOOK_SECRET"
fetch_param "RESEND_API_KEY"
fetch_param "SMTP_PASSWORD"
fetch_param "SECRET_KEY"
fetch_param "ENCRYPTION_KEY"

echo ""
echo "📝 Fetching config..."
fetch_param "DATABASE_URL"
fetch_param "QDRANT_URL"
fetch_param "QDRANT_API_KEY"
fetch_param "UPSTASH_REDIS_URL"
fetch_param "UPSTASH_REDIS_TOKEN"
fetch_param "FRONTEND_URL"
fetch_param "ENVIRONMENT"
fetch_param "EMAIL_FROM"
fetch_param "SMTP_HOST"
fetch_param "SMTP_PORT"
fetch_param "SMTP_USER"
fetch_param "STRIPE_PUBLISHABLE_KEY"
fetch_param "STRIPE_PRICE_ID"
fetch_param "INTELLIGENT_ROUTING_ENABLED"
fetch_param "MEMORY_ENABLED"
fetch_param "DEFAULT_REQUESTS_PER_DAY"
fetch_param "DEFAULT_TOKENS_PER_DAY"
fetch_param "PERPLEXITY_RPS"
fetch_param "PERPLEXITY_BURST"
fetch_param "PERPLEXITY_CONCURRENCY"
fetch_param "OPENAI_RPS"
fetch_param "OPENAI_BURST"
fetch_param "OPENAI_CONCURRENCY"
fetch_param "GEMINI_RPS"
fetch_param "GEMINI_BURST"
fetch_param "GEMINI_CONCURRENCY"
fetch_param "OPENROUTER_RPS"
fetch_param "OPENROUTER_BURST"
fetch_param "OPENROUTER_CONCURRENCY"
fetch_param "FIREBASE_PROJECT_ID"
fetch_param "DEFAULT_ORG_ID"
fetch_param "NEXT_PUBLIC_FIREBASE_API_KEY"
fetch_param "NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN"
fetch_param "NEXT_PUBLIC_FIREBASE_PROJECT_ID"
fetch_param "NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET"
fetch_param "NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID"
fetch_param "NEXT_PUBLIC_FIREBASE_APP_ID"
fetch_param "NEXT_PUBLIC_APP_URL"

echo ""
echo "✅ Secrets fetched successfully!"
echo ""
echo "📝 File: $ENV_FILE"
echo "   (This file is gitignored - never commit it)"
echo ""
echo "🚀 Ready to develop:"
echo "   cd backend"
echo "   source .env.local"
echo "   python main.py"
echo ""
echo "💡 TIP: Add this to your shell profile (~/.zshrc or ~/.bashrc):"
echo '   if [ -f backend/.env.local ]; then source backend/.env.local; fi'
echo "   Then reload: source ~/.zshrc"
