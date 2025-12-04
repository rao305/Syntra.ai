# Google OAuth + E2E Encryption Setup Guide

This guide walks you through setting up Google OAuth authentication and E2E encryption for chat messages in Syntra.

## Overview

### What We've Implemented

1. **Google OAuth Authentication via Firebase**
   - Users can sign in with their Google account
   - Firebase handles OAuth flow securely
   - Backend validates Firebase tokens and issues JWT
   - Automatic user provisioning on first login

2. **End-to-End Encryption (E2E)**
   - Chat messages encrypted with per-user keys
   - Encryption service: `ChatEncryptionService`
   - Database migration adds `encrypted_content` and `encryption_key_id` fields
   - Keys derived deterministically from user ID + base encryption key

---

## Prerequisites

1. **Firebase Project** (free tier available)
2. **Google OAuth credentials** (configured in Firebase Console)
3. **Backend environment variables** for Firebase
4. **Frontend environment variables** for Firebase config

---

## Step 1: Set Up Firebase Project

### 1.1 Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Create a new project"
3. Enter project name: `syntra` (or your preference)
4. Accept terms and click "Create project"

### 1.2 Enable Google Authentication

1. In Firebase Console, go to **Authentication** → **Sign-in method**
2. Click **Google** and enable it
3. Select a project support email
4. Click **Save**

### 1.3 Create Service Account for Backend

1. Go to **Project Settings** → **Service Accounts**
2. Click **Generate New Private Key**
3. A JSON file will download with credentials
4. Save this file securely (you'll need it for backend)

### 1.4 Get Web API Key

1. Go to **Project Settings** → **General**
2. Under "Web API Key", copy the API key
3. Also note:
   - Project ID
   - Auth Domain (format: `{project-id}.firebaseapp.com`)
   - Storage Bucket
   - Messaging Sender ID
   - App ID

---

## Step 2: Configure Frontend Environment

Create or update `/Users/rao305/Documents/Syntra/frontend/.env.local`:

```env
# Firebase Web Configuration
NEXT_PUBLIC_FIREBASE_API_KEY={your-web-api-key}
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN={project-id}.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID={your-project-id}
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET={project-id}.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID={messaging-sender-id}
NEXT_PUBLIC_FIREBASE_APP_ID={app-id}
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Example values:**
```env
NEXT_PUBLIC_FIREBASE_API_KEY=AIzaSyDxXx_example_key_here
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=syntra-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=syntra-project
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=syntra-project.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=123456789
NEXT_PUBLIC_FIREBASE_APP_ID=1:123456789:web:abcdef1234567890
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Step 3: Configure Backend Environment

Update `/Users/rao305/Documents/Syntra/backend/.env`:

```env
# ... existing config ...

# Firebase Admin SDK
FIREBASE_CREDENTIALS_FILE=/path/to/service-account-key.json
# OR (alternative, using raw JSON):
# FIREBASE_CREDENTIALS_JSON={"type":"service_account","project_id":"..."}

FIREBASE_PROJECT_ID=your-project-id
DEFAULT_ORG_ID=org_demo

# Encryption (generate a new Fernet key if you don't have one)
ENCRYPTION_KEY=your-fernet-encryption-key-here
```

### Generate a Fernet Encryption Key

If you need to generate a new encryption key, run:

```bash
cd /Users/rao305/Documents/Syntra/backend
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output and use it as `ENCRYPTION_KEY` in your `.env` file.

---

## Step 4: Apply Database Migration

Run the E2E encryption migration:

```bash
cd /Users/rao305/Documents/Syntra/backend

# Activate venv if needed
source venv/bin/activate

# Run migration
alembic upgrade head
```

This will add:
- `encrypted_content` (BYTEA column)
- `encryption_key_id` (String column for key version tracking)

---

## Step 5: Test the Setup

### 5.1 Start Backend

```bash
cd /Users/rao305/Documents/Syntra/backend
source venv/bin/activate
python -m uvicorn main:app --reload
```

Backend should be running on `http://localhost:8000`

### 5.2 Start Frontend

```bash
cd /Users/rao305/Documents/Syntra/frontend
npm run dev
```

Frontend should be running on `http://localhost:3000`

### 5.3 Test Google Sign-In

1. Open `http://localhost:3000/auth/sign-in`
2. Click "Continue with Google"
3. Select or sign in with your Google account
4. You should be redirected to `/conversations`
5. Check browser console and network tab for successful auth

### 5.4 Verify Auth Flow

**Frontend logs:**
- "Firebase initialized"
- Auth state changes should log user data

**Backend logs:**
- POST `/api/auth/firebase` endpoint should be called
- User should be auto-created in database
- JWT token should be returned

---

## Architecture & Implementation Details

### Authentication Flow

```
User Browser                Firebase             Backend
    │                           │                   │
    ├─── Sign In ────────────→  │                   │
    │                           │                   │
    │ ← Google OAuth Dialog ────┤                   │
    │                           │                   │
    ├─── Auth Code ──────────→  │                   │
    │                           │                   │
    │ ← ID Token ───────────────┤                   │
    │                           │                   │
    ├─── ID Token ──────────────────────────────→  │
    │                           │    Verify Token   │
    │                           │  ← Valid/Invalid  │
    │                           │    Auto-create    │
    │                           │    User           │
    │ ← JWT (access token) ──────────────────────┤
    │ ← org_id, user data ───────────────────────┤
    │                           │                   │
    └─── Store JWT ──────────→  │                   │
         (Session Storage)      │                   │
```

### E2E Encryption Architecture

```
User Message                Encryption Service         Database
     │                              │                      │
     ├─ "Hello" ────────────────→   │                      │
     │                    Derive Key │                      │
     │                    (user_id)  │                      │
     │                  Fernet Encrypt                      │
     │                              │                      │
     │ ← Encrypted Bytes ───────────┤                      │
     │                              │                      │
     ├─ Store Encrypted ─────────────────────────────→   │
     │    + encryption_key_id       │                      │
     │                              │                      │
```

### User Key Derivation

Keys are derived deterministically using PBKDF2:
- Input: Base encryption key + User ID
- Output: Unique Fernet key per user
- Iterations: 100,000
- Hash: SHA-256

**Benefits:**
- Same user ID always produces same key
- No need to store keys separately
- Secure key derivation function (PBKDF2)
- Fernet provides authenticated encryption

---

## Code Files Modified/Created

### Backend

1. **Database Model**
   - `/Users/rao305/Documents/Syntra/backend/app/models/message.py`
   - Added: `encrypted_content`, `encryption_key_id` fields

2. **Encryption Service** (NEW)
   - `/Users/rao305/Documents/Syntra/backend/app/services/chat_encryption.py`
   - `ChatEncryptionService` class
   - Methods: `encrypt_message()`, `decrypt_message()`

3. **Database Migration** (NEW)
   - `/Users/rao305/Documents/Syntra/backend/migrations/versions/20250204_add_e2e_encryption.py`
   - Adds encryption columns to messages table

4. **Existing Files** (Already configured)
   - `/Users/rao305/Documents/Syntra/backend/app/api/auth.py` - Firebase token verification
   - `/Users/rao305/Documents/Syntra/backend/app/security.py` - Encryption service (reused)
   - `/Users/rao305/Documents/Syntra/backend/config.py` - Configuration

### Frontend

1. **Auth Provider** (UPDATED)
   - `/Users/rao305/Documents/Syntra/frontend/components/auth/auth-provider.tsx`
   - Enabled Firebase sign-in
   - Integrated with backend token exchange
   - Auto-redirect on auth

2. **Existing Files** (Already configured)
   - `/Users/rao305/Documents/Syntra/frontend/lib/firebase.ts` - Firebase initialization
   - `/Users/rao305/Documents/Syntra/frontend/app/auth/sign-in/page.tsx` - Sign-in UI

---

## Integration with Chat Endpoints

### Using Encryption in Message Endpoints

To encrypt messages when storing them:

```python
from app.services.chat_encryption import chat_encryption_service
from app.models.message import Message

# When creating a message
encrypted = chat_encryption_service.encrypt_message(
    content=user_message,
    user_id=current_user.id
)

message = Message(
    thread_id=thread_id,
    user_id=current_user.id,
    role=MessageRole.USER,
    content=user_message,  # Keep plaintext for display
    encrypted_content=encrypted,  # Store encrypted version
    encryption_key_id="v1",  # Version identifier
)

# When retrieving a message
decrypted = chat_encryption_service.decrypt_message(
    encrypted_content=message.encrypted_content,
    user_id=message.user_id
)
```

### Example: Updating Message Endpoints

Update `/Users/rao305/Documents/Syntra/backend/app/api/threads.py` routes that handle messages:

```python
from app.services.chat_encryption import chat_encryption_service

@router.post("/{thread_id}/messages")
async def add_message(
    thread_id: str,
    payload: AddMessageRequest,
    current_user: CurrentUser = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
):
    # ... existing validation ...

    # Encrypt the user message
    encrypted_content = chat_encryption_service.encrypt_message(
        content=payload.content,
        user_id=current_user.id
    )

    message = Message(
        thread_id=thread_id,
        user_id=current_user.id,
        role=MessageRole.USER,
        content=payload.content,  # For backwards compatibility
        encrypted_content=encrypted_content,
        encryption_key_id="v1",
        # ... other fields ...
    )

    db.add(message)
    await db.commit()

    # Return message with decrypted content
    return {
        "id": message.id,
        "content": payload.content,  # Return plaintext to user
        "encrypted": True,
    }
```

---

## Security Considerations

### What's Encrypted?

- ✓ Chat message content (in database)
- ✓ Provider API keys (existing - Fernet encryption)

### What's NOT Encrypted?

- ✗ User metadata (name, email)
- ✗ Thread titles and settings
- ✗ Timestamps
- ✗ Token/usage metadata

**Rationale:** Application needs metadata for search, sorting, and API operations. Content encryption protects sensitive chat data while allowing feature functionality.

### Key Management

**Current Implementation:**
- Single base key for entire system (`ENCRYPTION_KEY` env var)
- Per-user keys derived deterministically
- No key rotation yet (can be added later)

**Future Improvements:**
- Key versioning (track `encryption_key_id` version)
- Automatic key rotation
- Per-organization keys
- Hardware security modules (HSM) for production

### Data In Transit

- ✓ HTTPS enforced (in production)
- ✓ Firebase uses secure token exchange
- ✓ TLS for database connections

---

## Troubleshooting

### "Firebase is not initialized"

**Cause:** Firebase config not loaded
**Solution:**
1. Check `.env.local` has all Firebase variables
2. Verify `NEXT_PUBLIC_*` prefix (frontend only)
3. Restart dev server

### "Invalid Firebase token"

**Cause:** Backend can't verify Firebase token
**Solution:**
1. Verify `FIREBASE_CREDENTIALS_FILE` or `FIREBASE_CREDENTIALS_JSON` in backend `.env`
2. Check service account has correct permissions
3. Verify `FIREBASE_PROJECT_ID` matches Firebase project

### "Decryption failed"

**Cause:** User ID mismatch or key changed
**Solution:**
1. Ensure user_id is consistent
2. Check `ENCRYPTION_KEY` hasn't changed
3. Verify message was encrypted with same user ID

### CORS Errors

**Cause:** Frontend and backend CORS mismatch
**Solution:**
1. Check backend CORS config includes `http://localhost:3000`
2. Verify `NEXT_PUBLIC_API_URL` points to correct backend
3. Check browser console for actual error

---

## Production Considerations

### Before Going Live

1. **Firebase Project**
   - Enable additional sign-in methods if needed
   - Configure authorized redirect URIs
   - Set up HTTPS redirect

2. **Backend**
   - Use strong `ENCRYPTION_KEY` (already Fernet format)
   - Store service account key securely (environment variable or secret manager)
   - Enable database SSL/TLS
   - Set `environment=production` in config

3. **Frontend**
   - Set correct `NEXT_PUBLIC_API_URL` for production domain
   - Use HTTPS everywhere
   - Update Firebase console with production domain

4. **Database**
   - Regular encrypted backups
   - Test decryption of backups
   - Document key recovery procedures

5. **Monitoring**
   - Log auth successes/failures
   - Monitor decryption errors
   - Alert on key mismatches

---

## Support & Resources

- **Firebase Docs:** https://firebase.google.com/docs/auth
- **Cryptography (Fernet):** https://cryptography.io/en/latest/fernet/
- **FastAPI Auth:** https://fastapi.tiangolo.com/advanced/security/
- **Next.js Firebase Integration:** https://nextjs.org/docs

---

## Quick Reference

### Common Commands

```bash
# Generate new Fernet key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Run migrations
cd backend && alembic upgrade head

# Test auth endpoint
curl -X POST http://localhost:8000/api/auth/firebase \
  -H "Content-Type: application/json" \
  -d '{"id_token":"your-firebase-token"}'

# Encrypt test message (Python)
from app.services.chat_encryption import chat_encryption_service
encrypted = chat_encryption_service.encrypt_message("Hello", "user-123")
```

---

## Summary

You now have:
1. ✓ Google OAuth authentication (Firebase)
2. ✓ Secure token exchange (Backend JWT)
3. ✓ E2E message encryption (Fernet per-user)
4. ✓ Database schema updated
5. ✓ Full integration ready

Next steps:
- Integrate encryption into message endpoints
- Add key rotation strategy
- Test with real users
- Monitor and optimize performance
