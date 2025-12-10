#!/bin/bash
# Quick start script for Google OAuth + E2E Encryption setup

set -e

echo "=========================================="
echo "Syntra: Google OAuth + E2E Encryption"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_ROOT="/Users/rao305/Documents/Syntra"

echo -e "${BLUE}Step 1: Verify Project Structure${NC}"
echo "Checking for required files..."

files_to_check=(
    "backend/app/services/chat_encryption.py"
    "backend/app/services/message_encryption_helper.py"
    "backend/migrations/versions/20250204_add_e2e_encryption.py"
    "backend/app/models/message.py"
    "frontend/components/auth/auth-provider.tsx"
)

for file in "${files_to_check[@]}"; do
    if [ -f "$PROJECT_ROOT/$file" ]; then
        echo -e "${GREEN}✓${NC} $file"
    else
        echo -e "${YELLOW}✗${NC} $file (MISSING)"
    fi
done

echo ""
echo -e "${BLUE}Step 2: Generate Fernet Encryption Key${NC}"
echo "Run this command to generate a new encryption key:"
echo ""
echo -e "${YELLOW}python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"${NC}"
echo ""
echo "Copy the output and add to backend/.env as ENCRYPTION_KEY="
echo ""

read -p "Press Enter after generating and setting ENCRYPTION_KEY..."

echo ""
echo -e "${BLUE}Step 3: Run Database Migration${NC}"
echo ""
cd "$PROJECT_ROOT/backend"

if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate

    echo "Running migration..."
    if command -v alembic &> /dev/null; then
        alembic upgrade head
        echo -e "${GREEN}✓ Migration completed${NC}"
    else
        echo -e "${YELLOW}⚠ Alembic not found. Run manually:${NC}"
        echo "  cd backend && alembic upgrade head"
    fi
else
    echo -e "${YELLOW}⚠ Virtual environment not found at $PROJECT_ROOT/backend/venv${NC}"
    echo "Please activate your virtual environment and run: alembic upgrade head"
fi

echo ""
echo -e "${BLUE}Step 4: Configuration Files${NC}"
echo ""
echo "Create/update these files with your Firebase credentials:"
echo ""
echo -e "${YELLOW}frontend/.env.local:${NC}"
cat <<EOF
NEXT_PUBLIC_FIREBASE_API_KEY=<your-key-from-firebase-console>
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=<project-id>.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=<your-project-id>
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=<project-id>.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=<sender-id>
NEXT_PUBLIC_FIREBASE_APP_ID=<app-id>
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF

echo ""
echo -e "${YELLOW}backend/.env (additions):${NC}"
cat <<EOF
FIREBASE_CREDENTIALS_FILE=/path/to/service-account-key.json
FIREBASE_PROJECT_ID=<your-project-id>
ENCRYPTION_KEY=<generated-fernet-key>
DEFAULT_ORG_ID=org_demo
EOF

echo ""
echo -e "${BLUE}Step 5: Start Services${NC}"
echo ""
echo "Terminal 1 - Backend:"
echo -e "${YELLOW}cd $PROJECT_ROOT/backend${NC}"
echo -e "${YELLOW}source venv/bin/activate${NC}"
echo -e "${YELLOW}python -m uvicorn main:app --reload${NC}"
echo ""
echo "Terminal 2 - Frontend:"
echo -e "${YELLOW}cd $PROJECT_ROOT/frontend${NC}"
echo -e "${YELLOW}npm run dev${NC}"
echo ""
echo "Terminal 3 - Browser:"
echo -e "${YELLOW}open http://localhost:3000/auth/sign-in${NC}"
echo ""

echo -e "${BLUE}Step 6: Test Authentication${NC}"
echo ""
echo "1. Click 'Continue with Google'"
echo "2. Complete Google sign-in"
echo "3. Should redirect to /conversations"
echo "4. Check browser DevTools (F12) → Application → Session Storage for 'access_token'"
echo ""

echo ""
echo "=========================================="
echo -e "${GREEN}Setup instructions complete!${NC}"
echo "=========================================="
echo ""
echo "📚 Documentation:"
echo "  - SETUP_AUTH_ENCRYPTION.md (detailed guide)"
echo "  - QUICK_START_AUTH.md (quick reference)"
echo "  - IMPLEMENTATION_SUMMARY.md (architecture)"
echo "  - AUTH_ENCRYPTION_CHECKLIST.md (verification)"
echo ""
echo "🔗 Firebase Console:"
echo "  https://console.firebase.google.com/"
echo ""
echo "🚀 Next steps:"
echo "  1. Set up Firebase project"
echo "  2. Update environment files"
echo "  3. Run database migration"
echo "  4. Start backend and frontend"
echo "  5. Test authentication"
echo ""
