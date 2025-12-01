#!/bin/bash

# Create IAM Users for Developers
# This script creates IAM users, attaches permissions, and generates access keys
#
# Developers: pranav, kanav, yuvraaj, saksham

set -e

echo "🔐 Creating IAM users for developers..."
echo ""

AWS_REGION="us-east-1"
DEVELOPERS=("pranav" "kanav" "yuvraaj" "saksham")

# Create output file for credentials
CREDS_FILE="developer-credentials.txt"
> "$CREDS_FILE"

echo "================================================" >> "$CREDS_FILE"
echo "Syntra Developer AWS Credentials" >> "$CREDS_FILE"
echo "Generated: $(date)" >> "$CREDS_FILE"
echo "================================================" >> "$CREDS_FILE"
echo "" >> "$CREDS_FILE"

# Process each developer
for dev in "${DEVELOPERS[@]}"; do
    echo "👤 Processing: $dev"

    username="${dev}-dev"

    # Create user
    echo "   Creating user: $username"
    aws iam create-user --user-name "$username" 2>/dev/null || echo "   ⚠️  User $username already exists"

    # Wait a moment for user to be created
    sleep 1

    # Create inline policy for this user
    echo "   Attaching secrets policy..."

    # Create temporary policy file
    cat > /tmp/policy-$dev.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadSyntraSecrets",
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath"
      ],
      "Resource": "arn:aws:ssm:*:*:parameter/syntra/*"
    },
    {
      "Sid": "DecryptSecureStrings",
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:DescribeKey"
      ],
      "Resource": "arn:aws:kms:*:*:key/*"
    }
  ]
}
EOF

    aws iam put-user-policy \
        --user-name "$username" \
        --policy-name "syntra-secrets-access" \
        --policy-document file:///tmp/policy-$dev.json \
        2>/dev/null && echo "   ✅ Policy attached" || echo "   ⚠️  Policy already attached"

    rm /tmp/policy-$dev.json

    # Create access key
    echo "   Creating access key..."

    # Check if user already has access keys
    existing_keys=$(aws iam list-access-keys --user-name "$username" --query 'AccessKeyMetadata[*].AccessKeyId' --output text)

    if [ -z "$existing_keys" ]; then
        # No keys exist, create new one
        key_response=$(aws iam create-access-key --user-name "$username" --output json)
        access_key=$(echo "$key_response" | jq -r '.AccessKey.AccessKeyId')
        secret_key=$(echo "$key_response" | jq -r '.AccessKey.SecretAccessKey')
        echo "   ✅ Access key created"
    else
        # Keys already exist
        echo "   ⚠️  User already has access keys"
        access_key="[EXISTING_KEY_1]"
        secret_key="[EXISTING_KEY_1]"
    fi

    # Save to credentials file
    echo "" >> "$CREDS_FILE"
    echo "Developer: $dev" >> "$CREDS_FILE"
    echo "Username: $username" >> "$CREDS_FILE"
    echo "Access Key ID: $access_key" >> "$CREDS_FILE"
    echo "Secret Access Key: $secret_key" >> "$CREDS_FILE"
    echo "" >> "$CREDS_FILE"

    echo "✅ $dev setup complete"
    echo ""
done

echo "================================================" >> "$CREDS_FILE"
echo "INSTRUCTIONS FOR DEVELOPERS:" >> "$CREDS_FILE"
echo "================================================" >> "$CREDS_FILE"
echo "" >> "$CREDS_FILE"
echo "1. Run: aws configure" >> "$CREDS_FILE"
echo "" >> "$CREDS_FILE"
echo "2. When prompted, enter:" >> "$CREDS_FILE"
echo "   AWS Access Key ID: [from above]" >> "$CREDS_FILE"
echo "   AWS Secret Access Key: [from above]" >> "$CREDS_FILE"
echo "   Default region: us-east-1" >> "$CREDS_FILE"
echo "   Default output format: json" >> "$CREDS_FILE"
echo "" >> "$CREDS_FILE"
echo "3. Run: ./scripts/fetch-secrets.sh" >> "$CREDS_FILE"
echo "" >> "$CREDS_FILE"
echo "4. Verify:" >> "$CREDS_FILE"
echo "   source backend/.env.local" >> "$CREDS_FILE"
echo "   echo \$OPENAI_API_KEY" >> "$CREDS_FILE"
echo "" >> "$CREDS_FILE"

echo "✅ All developers created!"
echo ""
echo "📝 Credentials saved to: $CREDS_FILE"
echo ""
echo "📋 Next steps:"
echo "   1. Review: cat $CREDS_FILE"
echo "   2. Send each developer their credentials"
echo "   3. Delete this file after sending: rm $CREDS_FILE"
