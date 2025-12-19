#!/bin/bash

# List all parameters in AWS Parameter Store
# Useful for verifying what's been uploaded

set -e

AWS_REGION="us-east-1"

echo "📋 All Parameters in AWS Parameter Store (/syntra/)"
echo "===================================================="
echo ""

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not installed"
    exit 1
fi

if ! aws sts get-caller-identity &>/dev/null; then
    echo "❌ AWS credentials not configured"
    exit 1
fi

# Get all parameters
params=$(aws ssm describe-parameters \
    --region "$AWS_REGION" \
    --filters "Key=Name,Values=/syntra/" \
    --query 'Parameters[*].Name' \
    --output text 2>/dev/null || echo "")

if [ -z "$params" ]; then
    echo "❌ No parameters found"
    exit 1
fi

# Count and list
count=$(echo "$params" | tr '\t' '\n' | wc -l | tr -d ' ')
echo "Total parameters: $count"
echo ""

# List all parameter names
echo "$params" | tr '\t' '\n' | sort | while read -r param; do
    if [ -n "$param" ]; then
        # Extract just the key name (remove /syntra/ prefix)
        key="${param#/syntra/}"
        echo "  ✓ $key"
    fi
done

echo ""
echo "💡 To view a parameter value:"
echo "   aws ssm get-parameter --name \"/syntra/PARAM_NAME\" --with-decryption --region $AWS_REGION --query 'Parameter.Value' --output text"











