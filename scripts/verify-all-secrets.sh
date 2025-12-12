#!/bin/bash

# Comprehensive verification of all secrets in AWS Parameter Store
# This script checks that all required variables are present and not placeholders

set -e

echo "🔍 Comprehensive Secret Verification"
echo "======================================"
echo ""

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not installed"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &>/dev/null; then
    echo "❌ AWS credentials not configured"
    exit 1
fi

AWS_REGION="us-east-1"

# Function to verify parameter
verify_param() {
    local key=$1
    local required=$2  # "required" or "optional"
    local aws_param_name="/syntra/$key"

    local value=$(aws ssm get-parameter \
        --name "$aws_param_name" \
        --with-decryption \
        --query 'Parameter.Value' \
        --output text \
        --region "$AWS_REGION" \
        2>/dev/null || echo "")

    if [ -z "$value" ]; then
        if [ "$required" = "required" ]; then
            echo "❌ $key: MISSING (REQUIRED)"
            return 1
        else
            echo "⏭️  $key: not set (optional)"
            return 0
        fi
    fi

    # Check for placeholder patterns
    if [[ "$value" == *"your-"* ]] || \
       [[ "$value" == *"change-this"* ]] || \
       [[ "$value" == *"placeholder"* ]] || \
       [[ "$value" == "sk_test_"* && ${#value} -lt 25 ]] || \
       [[ "$value" == "pk_test_"* && ${#value} -lt 25 ]] || \
       [[ "$value" == "sk_live_"* && ${#value} -lt 25 ]] || \
       [[ "$value" == "pk_live_"* && ${#value} -lt 25 ]]; then
        echo "⚠️  $key: PLACEHOLDER VALUE (${value:0:40}...)"
        return 1
    else
        local preview="${value:0:15}..."
        echo "✅ $key: $preview"
        return 0
    fi
}

ERRORS=0

echo "🔒 Backend Secrets (Required):"
echo "-------------------------------"
verify_param "DATABASE_URL" "required" || ERRORS=$((ERRORS + 1))
verify_param "QDRANT_URL" "required" || ERRORS=$((ERRORS + 1))
verify_param "UPSTASH_REDIS_URL" "required" || ERRORS=$((ERRORS + 1))
verify_param "SECRET_KEY" "required" || ERRORS=$((ERRORS + 1))
verify_param "ENCRYPTION_KEY" "required" || ERRORS=$((ERRORS + 1))
verify_param "CLERK_SECRET_KEY" "required" || ERRORS=$((ERRORS + 1))

echo ""
echo "🔑 API Keys (Optional but recommended):"
echo "----------------------------------------"
verify_param "OPENAI_API_KEY" "optional" || ERRORS=$((ERRORS + 1))
verify_param "GOOGLE_API_KEY" "optional" || ERRORS=$((ERRORS + 1))
verify_param "PERPLEXITY_API_KEY" "optional" || ERRORS=$((ERRORS + 1))
verify_param "OPENROUTER_API_KEY" "optional" || ERRORS=$((ERRORS + 1))
verify_param "KIMI_API_KEY" "optional" || ERRORS=$((ERRORS + 1))

echo ""
echo "🌐 Frontend Configuration (Required):"
echo "--------------------------------------"
verify_param "NEXT_PUBLIC_API_URL" "required" || ERRORS=$((ERRORS + 1))
verify_param "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY" "required" || ERRORS=$((ERRORS + 1))

echo ""
echo "⚙️  Configuration:"
echo "-------------------"
verify_param "FRONTEND_URL" "optional" || ERRORS=$((ERRORS + 1))
verify_param "ENVIRONMENT" "optional" || ERRORS=$((ERRORS + 1))
verify_param "DEFAULT_ORG_ID" "optional" || ERRORS=$((ERRORS + 1))
verify_param "FEATURE_COREWRITE" "optional" || ERRORS=$((ERRORS + 1))

echo ""
echo "======================================"
if [ $ERRORS -eq 0 ]; then
    echo "✅ All verified secrets look good!"
    echo ""
    echo "📊 Summary:"
    echo "   - All required variables are present"
    echo "   - No placeholder values detected"
    echo "   - Ready for team use"
else
    echo "⚠️  Found $ERRORS issue(s)!"
    echo ""
    echo "💡 To fix:"
    echo "   1. Update backend/.env and frontend/.env.local with real values"
    echo "   2. Run: ./scripts/setup-parameter-store.sh"
fi







