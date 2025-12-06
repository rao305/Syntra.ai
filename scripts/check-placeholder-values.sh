#!/bin/bash

# Check for placeholder values in AWS Parameter Store
# Identifies values that look like placeholders vs real values

set -e

AWS_REGION="us-east-1"

echo "🔍 Checking for Placeholder Values in AWS Parameter Store"
echo "=========================================================="
echo ""

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not installed"
    exit 1
fi

if ! aws sts get-caller-identity &>/dev/null; then
    echo "❌ AWS credentials not configured"
    exit 1
fi

# Function to check parameter
check_param() {
    local key=$1
    local aws_param_name="/syntra/$key"

    local value=$(aws ssm get-parameter \
        --name "$aws_param_name" \
        --with-decryption \
        --query 'Parameter.Value' \
        --output text \
        --region "$AWS_REGION" \
        2>/dev/null || echo "")

    if [ -z "$value" ]; then
        echo "⏭️  $key: NOT SET (optional)"
        return
    fi

    local status="✅"
    local note=""
    
    # Check for definite placeholders
    if [[ "$value" == *"your-"* ]] || \
       [[ "$value" == *"change-this"* ]] || \
       [[ "$value" == *"placeholder"* ]] || \
       [[ "$value" == *"yourdomain.com"* ]] || \
       [[ "$value" == *"your-email"* ]]; then
        status="⚠️ "
        note="PLACEHOLDER - Should be replaced"
    # Check for short API keys (likely placeholders)
    elif [[ "$value" == "sk_test_"* ]] && [ ${#value} -lt 25 ]; then
        status="⚠️ "
        note="PLACEHOLDER - Too short to be real"
    elif [[ "$value" == "pk_test_"* ]] && [ ${#value} -lt 25 ]; then
        status="⚠️ "
        note="PLACEHOLDER - Too short to be real"
    # Check for dev/test values (OK for development)
    elif [[ "$value" == *"@example.com"* ]] || \
         [[ "$value" == *"@localhost"* ]] || \
         [[ "$value" == "org_demo"* ]] || \
         [[ "$value" == *"localhost"* ]]; then
        status="ℹ️ "
        note="DEV/TEST VALUE (OK for development, change for production)"
    else
        status="✅"
        note="Real value"
    fi
    
    echo "$status $key: $note"
    if [ "$status" != "✅" ]; then
        echo "      Value: ${value:0:60}..."
    else
        local preview="${value:0:30}..."
        echo "      Preview: $preview"
    fi
}

echo "🔒 Checking Critical Secrets:"
echo "-----------------------------"
check_param "SECRET_KEY"
check_param "ENCRYPTION_KEY"
check_param "CLERK_SECRET_KEY"
check_param "OPENAI_API_KEY"
check_param "GOOGLE_API_KEY"
check_param "PERPLEXITY_API_KEY"

echo ""
echo "📧 Checking Email Configuration:"
echo "---------------------------------"
check_param "EMAIL_FROM"
check_param "SMTP_USER"
check_param "SMTP_HOST"

echo ""
echo "🗄️  Checking Database Configuration:"
echo "------------------------------------"
check_param "DATABASE_URL"
check_param "QDRANT_URL"
check_param "UPSTASH_REDIS_URL"

echo ""
echo "🌐 Checking Frontend Configuration:"
echo "-----------------------------------"
check_param "NEXT_PUBLIC_API_URL"
check_param "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY"
check_param "FRONTEND_URL"

echo ""
echo "⚙️  Checking Other Configuration:"
echo "----------------------------------"
check_param "DEFAULT_ORG_ID"
check_param "ENVIRONMENT"

echo ""
echo "=========================================================="
echo "💡 Legend:"
echo "   ✅ = Real value (production-ready)"
echo "   ℹ️  = Dev/test value (OK for development, change for production)"
echo "   ⚠️  = Placeholder (should be replaced)"
echo "   ⏭️  = Not set (optional, can be empty)"
echo ""
echo "📝 To update values:"
echo "   1. Edit backend/.env and frontend/.env.local with real values"
echo "   2. Run: ./scripts/setup-parameter-store.sh"
echo ""
echo "🔗 View all parameters:"
echo "   ./scripts/list-all-parameters.sh"
