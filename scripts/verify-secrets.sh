#!/bin/bash

# Verify Secrets in AWS Parameter Store
# This script checks what values are currently stored in AWS Parameter Store
# and warns about placeholder values

set -e

echo "🔍 Verifying secrets in AWS Parameter Store..."
echo ""

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not installed"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &>/dev/null; then
    echo "❌ AWS credentials not configured"
    echo "   Run: aws configure"
    exit 1
fi

AWS_REGION="us-east-1"

echo "📍 Region: $AWS_REGION"
echo ""

# Function to check parameter
check_param() {
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
        echo "❌ $key: NOT FOUND"
        return
    fi

    # Check for placeholder patterns
    if [[ "$value" == *"your-"* ]] || [[ "$value" == *"change-this"* ]] || [[ "$value" == *"placeholder"* ]] || [[ "$value" == "sk_test_"* && ${#value} -lt 20 ]] || [[ "$value" == "pk_test_"* && ${#value} -lt 20 ]]; then
        echo "⚠️  $key: PLACEHOLDER VALUE (${value:0:40}...)"
    else
        # Show first few chars for security
        local preview="${value:0:10}..."
        echo "✅ $key: $preview"
    fi
}

echo "Checking secrets..."
check_param "OPENAI_API_KEY"
check_param "GOOGLE_API_KEY"
check_param "PERPLEXITY_API_KEY"
check_param "OPENROUTER_API_KEY"
check_param "CLERK_SECRET_KEY"
check_param "SECRET_KEY"
check_param "ENCRYPTION_KEY"
check_param "DATABASE_URL"
check_param "QDRANT_URL"
check_param "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY"

echo ""
echo "💡 If you see placeholder values, update backend/.env with real values"
echo "   Then run: ./scripts/setup-parameter-store.sh"




