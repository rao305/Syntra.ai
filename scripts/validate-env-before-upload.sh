#!/bin/bash

# Validate .env file before uploading to AWS Parameter Store
# This script checks for placeholder values and warns you before uploading

set -e

ENV_FILE="backend/.env"

echo "🔍 Validating $ENV_FILE before upload..."
echo ""

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ $ENV_FILE not found!"
    echo "   Create it by copying: cp backend/env.example backend/.env"
    exit 1
fi

# Load the .env file
set -a
source "$ENV_FILE"
set +a

echo "Checking for placeholder values..."
echo ""

# Function to check for placeholders
check_placeholder() {
    local key=$1
    local value="${!key}"
    
    if [ -z "$value" ]; then
        echo "⏭️  $key: empty (will be skipped)"
        return
    fi
    
    # Check for common placeholder patterns
    if [[ "$value" == *"your-"* ]] || \
       [[ "$value" == *"change-this"* ]] || \
       [[ "$value" == *"placeholder"* ]] || \
       [[ "$value" == "sk_test_"* && ${#value} -lt 25 ]] || \
       [[ "$value" == "pk_test_"* && ${#value} -lt 25 ]] || \
       [[ "$value" == "sk_live_"* && ${#value} -lt 25 ]] || \
       [[ "$value" == "pk_live_"* && ${#value} -lt 25 ]]; then
        echo "⚠️  $key: PLACEHOLDER DETECTED!"
        echo "      Value: ${value:0:50}..."
        return 1
    else
        echo "✅ $key: looks good"
        return 0
    fi
}

ERRORS=0

echo "🔒 Checking secrets..."
check_placeholder "OPENAI_API_KEY" || ERRORS=$((ERRORS + 1))
check_placeholder "GOOGLE_API_KEY" || ERRORS=$((ERRORS + 1))
check_placeholder "PERPLEXITY_API_KEY" || ERRORS=$((ERRORS + 1))
check_placeholder "OPENROUTER_API_KEY" || ERRORS=$((ERRORS + 1))
check_placeholder "CLERK_SECRET_KEY" || ERRORS=$((ERRORS + 1))
check_placeholder "SECRET_KEY" || ERRORS=$((ERRORS + 1))
check_placeholder "ENCRYPTION_KEY" || ERRORS=$((ERRORS + 1))
check_placeholder "DATABASE_URL" || ERRORS=$((ERRORS + 1))
check_placeholder "QDRANT_URL" || ERRORS=$((ERRORS + 1))

echo ""
echo "📝 Checking frontend config..."
check_placeholder "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY" || ERRORS=$((ERRORS + 1))
check_placeholder "NEXT_PUBLIC_API_URL" || ERRORS=$((ERRORS + 1))

echo ""
if [ $ERRORS -gt 0 ]; then
    echo "❌ Found $ERRORS placeholder value(s)!"
    echo ""
    echo "⚠️  DO NOT upload these placeholder values to AWS Parameter Store!"
    echo ""
    echo "📝 To fix:"
    echo "   1. Edit backend/.env and replace placeholder values with real ones"
    echo "   2. Run this script again to verify: ./scripts/validate-env-before-upload.sh"
    echo "   3. Once all values are real, run: ./scripts/setup-parameter-store.sh"
    exit 1
else
    echo "✅ All values look good! Ready to upload."
    echo ""
    echo "🚀 Run this to upload to AWS Parameter Store:"
    echo "   ./scripts/setup-parameter-store.sh"
fi



