# AWS Account Information

## Account Details

### AWS Account Number
**894222084046**

### AWS Region
**us-east-1** (Primary region for Parameter Store and services)

### IAM User Information
- **Username**: `kanav-dev`
- **User ARN**: `arn:aws:iam::894222084046:user/kanav-dev`
- **User ID**: `AIDA5AM6KE7HHBWCU7ZGT`

### Access Credentials
- **Access Key ID**: `[REDACTED - Stored in ~/.aws/credentials]`
- **Secret Access Key**: `[REDACTED - Stored in ~/.aws/credentials]`
- **Status**: ✅ Configured and verified

## AWS Services Used

### AWS Systems Manager Parameter Store
- **Path Prefix**: `/syntra/`
- **Purpose**: Store encrypted secrets and configuration
- **Region**: `us-east-1`
- **Resource ARN Pattern**: `arn:aws:ssm:*:*:parameter/syntra/*`

### AWS KMS (Key Management Service)
- **Purpose**: Decrypt SecureString parameters
- **Resource ARN Pattern**: `arn:aws:kms:*:*:key/*`
- **Via Service**: 
  - `ssm.us-east-1.amazonaws.com`
  - `ssm.us-west-2.amazonaws.com`

## IAM Policy

The IAM user has the following permissions:

### Policy: `syntra-secrets-access`

```json
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
      "Resource": "arn:aws:kms:*:*:key/*",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": [
            "ssm.us-east-1.amazonaws.com",
            "ssm.us-west-2.amazonaws.com"
          ]
        }
      }
    }
  ]
}
```

## Developer Team

The following developers are configured in the system:
- **pranav** → IAM user: `pranav-dev`
- **kanav** → IAM user: `kanav-dev` ✅ (Current user)
- **yuvraaj** → IAM user: `yuvraaj-dev`
- **saksham** → IAM user: `saksham-dev`

## Parameter Store Structure

Secrets are stored under the path `/syntra/` with the following keys:

### Secrets (SecureString)
- `OPENAI_API_KEY`
- `GOOGLE_API_KEY`
- `PERPLEXITY_API_KEY`
- `OPENROUTER_API_KEY`
- `SUPERMEMORY_API_KEY`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `RESEND_API_KEY`
- `SMTP_PASSWORD`
- `SECRET_KEY`
- `ENCRYPTION_KEY`

### Configuration (String)
- `DATABASE_URL`
- `QDRANT_URL`
- `QDRANT_API_KEY`
- `UPSTASH_REDIS_URL`
- `UPSTASH_REDIS_TOKEN`
- `FRONTEND_URL`
- `ENVIRONMENT`
- `EMAIL_FROM`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `STRIPE_PUBLISHABLE_KEY`
- `STRIPE_PRICE_ID`
- `FIREBASE_PROJECT_ID`
- `DEFAULT_ORG_ID`
- `NEXT_PUBLIC_FIREBASE_API_KEY`
- `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN`
- `NEXT_PUBLIC_FIREBASE_PROJECT_ID`
- `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET`
- `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID`
- `NEXT_PUBLIC_FIREBASE_APP_ID`
- `NEXT_PUBLIC_APP_URL`

## Verification

To verify AWS access:

```bash
# Check current identity
aws sts get-caller-identity

# Expected output:
# {
#   "UserId": "AIDA5AM6KE7HHBWCU7ZGT",
#   "Account": "894222084046",
#   "Arn": "arn:aws:iam::894222084046:user/kanav-dev"
# }

# List available parameters
aws ssm get-parameters-by-path --path "/syntra/" --region us-east-1
```

## Files Containing AWS Information

1. **SETUP_COMPLETE.md** - Setup documentation with account details
2. **scripts/setup-iam-policy.json** - IAM policy template
3. **scripts/create-developer-users.sh** - Script to create developer IAM users
4. **scripts/fetch-secrets.sh** - Script to fetch secrets from Parameter Store
5. **scripts/setup-parameter-store.sh** - Script to upload secrets to Parameter Store
6. **~/.aws/credentials** - Local AWS credentials (not in repo)
7. **~/.aws/config** - Local AWS configuration (not in repo)

## Security Notes

⚠️ **IMPORTANT**: 
- Access keys are stored locally in `~/.aws/credentials` (not in git)
- Secret access keys should NEVER be committed to version control
- The `.gitignore` file excludes `developer-credentials.txt` and `.env` files
- IAM users have minimal permissions (read-only access to Parameter Store)

## AWS Console Links

- **IAM Users**: https://console.aws.amazon.com/iam/home#/users
- **Parameter Store**: https://console.aws.amazon.com/systems-manager/parameters
- **Account Settings**: https://console.aws.amazon.com/billing/home#/account

---

**Last Updated**: $(date)
**Account**: 894222084046
**Region**: us-east-1
**Current User**: kanav-dev

