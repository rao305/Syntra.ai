---
title: Qdrant Cloud Setup Guide
summary: Documentation file
last_updated: '2025-11-12'
owner: DAC
tags:
- dac
- docs
---

# Qdrant Cloud Setup Guide

## Quick Setup (5 minutes)

### Step 1: Create Qdrant Cloud Account

1. Go to: https://cloud.qdrant.io/
2. Click **"Sign Up"** (or use GitHub/Google)
3. Choose **FREE tier** (1GB storage, perfect for getting started)

### Step 2: Create a Cluster

1. After login, click **"Create Cluster"**
2. Choose settings:
   - **Cloud Provider**: AWS, GCP, or Azure (any works, AWS recommended for speed)
   - **Region**: Choose closest to you:
     - **US East** (Virginia) - `us-east-1` - Best for East Coast
     - **US West** (Oregon) - `us-west-2` - Best for West Coast
     - **EU** (Frankfurt) - `eu-central-1` - Best for Europe
     - **Asia** (Singapore) - `ap-southeast-1` - Best for Asia
   - **Name**: `dac-memory` (or any name you like)
   - **Tier**: Free tier (1GB)

3. Click **"Create"**
4. Wait ~30-60 seconds for cluster to provision

### Step 3: Get Your Credentials

Once cluster is ready:

1. Click on your cluster name
2. You'll see:
   ```
   Cluster URL: https://xxxx-xxxx.aws.cloud.qdrant.io:6333
   API Key: [Click to reveal]
   ```
3. **Copy both values**

### Step 4: Update Your .env File

Update these lines in `/Users/rao305/Documents/DAC/backend/.env`:

```env
# Replace localhost with your cloud URL
QDRANT_URL=https://your-cluster-id.aws.cloud.qdrant.io:6333

# Add your API key
QDRANT_API_KEY=your-api-key-here
```

**Example:**
```env
QDRANT_URL=https://abc123-def456.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Step 5: Verify Connection

Test the connection:

```bash
cd /Users/rao305/Documents/DAC/backend
source venv/bin/activate
python -c "
import asyncio
from qdrant_client import AsyncQdrantClient

async def test():
    client = AsyncQdrantClient(
        url='YOUR_QDRANT_URL',
        api_key='YOUR_QDRANT_API_KEY'
    )
    info = await client.get_collections()
    print('✅ Connected to Qdrant Cloud!')
    print(f'Collections: {len(info.collections)}')

asyncio.run(test())
"
```

If you see "✅ Connected to Qdrant Cloud!" - you're ready!

---

## Region Recommendations

### US East (Virginia) - `us-east-1`
- ✅ Best for: East Coast US
- ✅ Lowest latency for: New York, Boston, DC, Atlanta
- ✅ AWS default region (most services)

### US West (Oregon) - `us-west-2`
- ✅ Best for: West Coast US
- ✅ Lowest latency for: San Francisco, LA, Seattle
- ✅ Good for Asia-Pacific too

### EU (Frankfurt) - `eu-central-1`
- ✅ Best for: Europe
- ✅ Lowest latency for: Germany, UK, France, Netherlands

### Asia (Singapore) - `ap-southeast-1`
- ✅ Best for: Asia-Pacific
- ✅ Lowest latency for: Singapore, Indonesia, Malaysia, Thailand

**My Recommendation:** If you're in the US, use **US East (Virginia)** - it's the most reliable.

---

## Free Tier Limits

- **Storage**: 1 GB (enough for ~100K-500K memory fragments)
- **Requests**: Unlimited
- **Clusters**: 1 free cluster
- **No credit card required**

---

## Alternative: Keep Using Local Qdrant

If you prefer to keep using Docker locally:

1. Make sure Qdrant is running:
   ```bash
   docker ps | grep qdrant
   ```

2. If not running, start it:
   ```bash
   cd /Users/rao305/Documents/DAC
   docker-compose up -d qdrant
   ```

3. Your .env is already configured:
   ```env
   QDRANT_URL=http://localhost:6333
   QDRANT_API_KEY=  # Empty for local Docker
   ```

**Note:** Local Docker is fine for development, but Qdrant Cloud is better for production:
- ✅ Automatic backups
- ✅ Better uptime
- ✅ Easier to scale
- ✅ No local resources used

---

## Troubleshooting

### Issue: "Connection refused"
**Solution:** Check your QDRANT_URL format:
- ✅ Correct: `https://xxx.aws.cloud.qdrant.io:6333`
- ❌ Wrong: `http://xxx` (missing https)
- ❌ Wrong: `xxx.cloud.qdrant.io` (missing port :6333)

### Issue: "Authentication failed"
**Solution:** Check your API key:
- Copy the full key from Qdrant Cloud dashboard
- Make sure no extra spaces
- Should start with something like `eyJhbGciOiJ...`

### Issue: "Cannot create collection"
**Solution:** Check free tier limits:
- Free tier: 1GB storage
- If full, delete old collections or upgrade

---

## Testing the Memory System

Once Qdrant is connected, test the memory system:

```bash
cd /Users/rao305/Documents/DAC
python test_intelligent_routing.py
```

This will:
1. Create memory fragments
2. Store them in Qdrant
3. Retrieve them across different models
4. Demonstrate cross-model context sharing

---

## Quick Start Checklist

- [ ] Create Qdrant Cloud account
- [ ] Create cluster (choose region)
- [ ] Copy URL and API key
- [ ] Update .env file
- [ ] Test connection
- [ ] Run test_intelligent_routing.py
- [ ] 🎉 Cross-model memory working!

---

## Need Help?

1. **Qdrant Cloud Issues**: https://qdrant.tech/documentation/cloud/
2. **DAC Issues**: Check `INTELLIGENT_ROUTING_GUIDE.md`
3. **Still stuck**: Run `python test_intelligent_routing.py` and share the error

The setup takes **less than 5 minutes**. Once done, you'll have production-ready cross-model memory sharing! 🚀
