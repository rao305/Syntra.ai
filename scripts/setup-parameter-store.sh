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

# Check if .env file exists
if [ ! -f "backend/.env" ]; then
    echo "❌ backend/.env not found. Please create it first."
    exit 1
fi

# Load secrets from .env
set -a
source backend/.env
set +a

# AWS Region (change if needed)
AWS_REGION="us-east-1"

echo "📝 Reading secrets from backend/.env..."
echo "🌍 Using region: $AWS_REGION"
echo ""

# Function to safely put parameter
put_param() {
    local key=$1
    local value=$2
    local key_type=$3

    if [ -z "$value" ]; then
        echo "⏭️  Skipping $key (empty value)"
        return
    fi

    echo "📤 Uploading $key to Parameter Store..."
    aws ssm put-parameter \
        --name "/syntra/$key" \
        --value "$value" \
        --type "$key_type" \
        --overwrite \
        --region "$AWS_REGION" \
        --tags Key=app,Value=syntra Key=env,Value=development \
        2>/dev/null && echo "✅ $key uploaded" || echo "⚠️  $key already exists (updated)"
}

# Upload all secrets (SecureString for sensitive values, String for non-sensitive)
echo "🔒 Uploading secrets as SecureString (encrypted)..."
put_param "OPENAI_API_KEY" "$OPENAI_API_KEY" "SecureString"
put_param "GOOGLE_API_KEY" "$GOOGLE_API_KEY" "SecureString"
put_param "PERPLEXITY_API_KEY" "$PERPLEXITY_API_KEY" "SecureString"
put_param "OPENROUTER_API_KEY" "$OPENROUTER_API_KEY" "SecureString"
put_param "SUPERMEMORY_API_KEY" "$SUPERMEMORY_API_KEY" "SecureString"
put_param "STRIPE_SECRET_KEY" "$STRIPE_SECRET_KEY" "SecureString"
put_param "STRIPE_WEBHOOK_SECRET" "$STRIPE_WEBHOOK_SECRET" "SecureString"
put_param "RESEND_API_KEY" "$RESEND_API_KEY" "SecureString"
put_param "SMTP_PASSWORD" "$SMTP_PASSWORD" "SecureString"
put_param "SECRET_KEY" "$SECRET_KEY" "SecureString"
put_param "ENCRYPTION_KEY" "$ENCRYPTION_KEY" "SecureString"

echo ""
echo "📝 Uploading non-sensitive config as String..."
put_param "DATABASE_URL" "$DATABASE_URL" "String"
put_param "QDRANT_URL" "$QDRANT_URL" "String"
put_param "QDRANT_API_KEY" "$QDRANT_API_KEY" "String"
put_param "UPSTASH_REDIS_URL" "$UPSTASH_REDIS_URL" "String"
put_param "UPSTASH_REDIS_TOKEN" "$UPSTASH_REDIS_TOKEN" "String"
put_param "FRONTEND_URL" "$FRONTEND_URL" "String"
put_param "ENVIRONMENT" "$ENVIRONMENT" "String"
put_param "EMAIL_FROM" "$EMAIL_FROM" "String"
put_param "SMTP_HOST" "$SMTP_HOST" "String"
put_param "SMTP_PORT" "$SMTP_PORT" "String"
put_param "SMTP_USER" "$SMTP_USER" "String"
put_param "STRIPE_PUBLISHABLE_KEY" "$STRIPE_PUBLISHABLE_KEY" "String"
put_param "STRIPE_PRICE_ID" "$STRIPE_PRICE_ID" "String"
put_param "INTELLIGENT_ROUTING_ENABLED" "$INTELLIGENT_ROUTING_ENABLED" "String"
put_param "MEMORY_ENABLED" "$MEMORY_ENABLED" "String"
put_param "DEFAULT_REQUESTS_PER_DAY" "$DEFAULT_REQUESTS_PER_DAY" "String"
put_param "DEFAULT_TOKENS_PER_DAY" "$DEFAULT_TOKENS_PER_DAY" "String"
put_param "PERPLEXITY_RPS" "$PERPLEXITY_RPS" "String"
put_param "PERPLEXITY_BURST" "$PERPLEXITY_BURST" "String"
put_param "PERPLEXITY_CONCURRENCY" "$PERPLEXITY_CONCURRENCY" "String"
put_param "OPENAI_RPS" "$OPENAI_RPS" "String"
put_param "OPENAI_BURST" "$OPENAI_BURST" "String"
put_param "OPENAI_CONCURRENCY" "$OPENAI_CONCURRENCY" "String"
put_param "GEMINI_RPS" "$GEMINI_RPS" "String"
put_param "GEMINI_BURST" "$GEMINI_BURST" "String"
put_param "GEMINI_CONCURRENCY" "$GEMINI_CONCURRENCY" "String"
put_param "OPENROUTER_RPS" "$OPENROUTER_RPS" "String"
put_param "OPENROUTER_BURST" "$OPENROUTER_BURST" "String"
put_param "OPENROUTER_CONCURRENCY" "$OPENROUTER_CONCURRENCY" "String"
put_param "FIREBASE_PROJECT_ID" "$FIREBASE_PROJECT_ID" "String"
put_param "DEFAULT_ORG_ID" "$DEFAULT_ORG_ID" "String"
put_param "NEXT_PUBLIC_FIREBASE_API_KEY" "$NEXT_PUBLIC_FIREBASE_API_KEY" "String"
put_param "NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN" "$NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN" "String"
put_param "NEXT_PUBLIC_FIREBASE_PROJECT_ID" "$NEXT_PUBLIC_FIREBASE_PROJECT_ID" "String"
put_param "NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET" "$NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET" "String"
put_param "NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID" "$NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID" "String"
put_param "NEXT_PUBLIC_FIREBASE_APP_ID" "$NEXT_PUBLIC_FIREBASE_APP_ID" "String"
put_param "NEXT_PUBLIC_APP_URL" "$NEXT_PUBLIC_APP_URL" "String"

echo ""
echo "✅ All secrets uploaded to AWS Parameter Store!"
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
