#!/bin/bash
# Verify Clerk authentication setup

echo "🔍 CLERK CONFIGURATION VERIFICATION"
echo "==================================="
echo ""

# Check frontend environment
echo "1. Frontend Configuration (.env.local):"
if [ -f "frontend/.env.local" ]; then
    echo "   ✅ .env.local exists"
    
    if grep -q "CLERK_SECRET_KEY=sk_" frontend/.env.local; then
        echo "   ✅ CLERK_SECRET_KEY configured"
    else
        echo "   ❌ CLERK_SECRET_KEY not set (contains placeholder)"
    fi
    
    if grep -q "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_" frontend/.env.local; then
        echo "   ✅ NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY configured"
    else
        echo "   ❌ NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY not set (contains placeholder)"
    fi
    
    if grep -q "NEXT_PUBLIC_CLERK_FRONTEND_API=https://" frontend/.env.local; then
        echo "   ✅ NEXT_PUBLIC_CLERK_FRONTEND_API configured"
    else
        echo "   ❌ NEXT_PUBLIC_CLERK_FRONTEND_API not set (contains placeholder)"
    fi
else
    echo "   ❌ .env.local file missing"
fi
echo ""

# Check backend environment
echo "2. Backend Configuration (.env):"
if [ -f "backend/.env" ]; then
    echo "   ✅ backend/.env exists"
    
    if grep -q "CLERK_SECRET_KEY=sk_" backend/.env; then
        echo "   ✅ CLERK_SECRET_KEY configured"
    else
        echo "   ❌ CLERK_SECRET_KEY not set (contains placeholder)"
    fi
else
    echo "   ❌ backend/.env file missing"
fi
echo ""

# Check if services are running
echo "3. Service Status:"
if pgrep -f "python main.py" >/dev/null; then
    echo "   ✅ Backend server running"
else
    echo "   ❌ Backend server not running"
fi

if pgrep -f "next dev" >/dev/null; then
    echo "   ✅ Frontend dev server running"
else
    echo "   ❌ Frontend dev server not running"
fi
echo ""

echo "🎯 NEXT STEPS:"
echo "- Replace all placeholder values with actual Clerk keys"
echo "- Restart both frontend and backend servers"
echo "- Test authentication at http://localhost:3000"
echo "- Check browser console for Clerk errors"
