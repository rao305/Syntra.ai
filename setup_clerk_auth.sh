#!/bin/bash
# Clerk Authentication Setup Script

echo "🔐 CLERK AUTHENTICATION SETUP"
echo "============================="
echo ""

echo "📋 REQUIRED STEPS:"
echo ""

echo "1. 📝 Get Clerk API Keys:"
echo "   - Go to https://dashboard.clerk.com/"
echo "   - Select your application"
echo "   - Go to 'API Keys' section"
echo "   - Copy the following keys:"
echo ""

echo "2. ✏️  Configure Frontend (.env.local):"
echo "   - File: frontend/.env.local"
echo "   - Set: CLERK_SECRET_KEY (the secret key)"
echo "   - Set: NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY"
echo "   - Set: NEXT_PUBLIC_CLERK_FRONTEND_API"
echo ""

echo "3. ✏️  Configure Backend (.env):"
echo "   - File: backend/.env"
echo "   - Set: CLERK_SECRET_KEY (the secret key, NOT publishable)"
echo ""

echo "4. 🔄 Restart Services:"
echo "   - Backend: cd backend && python main.py"
echo "   - Frontend: cd frontend && npm run dev"
echo ""

echo "⚠️  IMPORTANT NOTES:"
echo "   - Backend needs SECRET KEY (starts with 'sk_test_' or 'sk_live_')"
echo "   - Frontend needs SECRET KEY + PUBLISHABLE KEY (both required)"
echo "   - Frontend API URL looks like: https://your-app.clerk.accounts.dev"
echo "   - Use the SAME SECRET KEY for both frontend and backend"
echo ""

echo "✅ TEST AFTER SETUP:"
echo "   - Open browser to http://localhost:3000"
echo "   - Try to sign in with Clerk"
echo "   - Check browser console for errors"
echo "   - Backend should accept Clerk tokens and return JWTs"
echo ""

echo "🔗 CLERK DOCUMENTATION:"
echo "   https://clerk.com/docs/quickstarts/nextjs"
