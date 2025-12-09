#!/bin/bash

# Syntra Setup Verification Script
# This script verifies that all dependencies and configurations are set up correctly

set -e

echo "🔍 Verifying Syntra Setup..."
echo "================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track errors
ERRORS=0

# Function to check command
check_cmd() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✅${NC} $1 is installed"
        return 0
    else
        echo -e "${RED}❌${NC} $1 is NOT installed"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Function to check file
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✅${NC} $1 exists"
        return 0
    else
        echo -e "${YELLOW}⚠️${NC}  $1 not found (may be optional)"
        return 1
    fi
}

# Function to check directory
check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✅${NC} $1 exists"
        return 0
    else
        echo -e "${RED}❌${NC} $1 does NOT exist"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

echo "📦 Checking Prerequisites..."
check_cmd python3
check_cmd node
check_cmd npm
check_cmd aws
echo ""

echo "🔐 Checking AWS Configuration..."
if aws sts get-caller-identity &>/dev/null; then
    echo -e "${GREEN}✅${NC} AWS credentials are configured"
    aws sts get-caller-identity --query 'Arn' --output text | sed 's/^/   User: /'
else
    echo -e "${RED}❌${NC} AWS credentials are NOT configured"
    ERRORS=$((ERRORS + 1))
fi
echo ""

echo "🐍 Checking Python Environment..."
check_dir "backend/venv"
if [ -d "backend/venv" ]; then
    echo "   Testing Python imports..."
    cd backend
    source venv/bin/activate
    python -c "import fastapi; print('✅ FastAPI installed')" 2>/dev/null && echo -e "${GREEN}✅${NC} FastAPI installed" || echo -e "${YELLOW}⚠️${NC}  FastAPI import test failed"
    python -c "import sqlalchemy; print('✅ SQLAlchemy installed')" 2>/dev/null && echo -e "${GREEN}✅${NC} SQLAlchemy installed" || echo -e "${YELLOW}⚠️${NC}  SQLAlchemy import test failed"
    deactivate
    cd ..
fi
echo ""

echo "📦 Checking Node.js Dependencies..."
check_dir "frontend/node_modules"
check_dir "apps/web/node_modules" || echo -e "${YELLOW}⚠️${NC}  apps/web/node_modules (optional)"
check_dir "code/node_modules" || echo -e "${YELLOW}⚠️${NC}  code/node_modules (optional)"
echo ""

echo "📝 Checking Environment Files..."
check_file "backend/.env" || check_file "backend/.env.local" || echo -e "${YELLOW}⚠️${NC}  No backend .env file found (create from backend/env.template)"
check_file "frontend/.env.local" || echo -e "${YELLOW}⚠️${NC}  No frontend .env.local file found (create from frontend/env.local.template)"
check_file "backend/env.template" && echo -e "${GREEN}✅${NC} Backend env template exists"
check_file "frontend/env.local.template" && echo -e "${GREEN}✅${NC} Frontend env template exists"
echo ""

echo "📚 Checking Documentation..."
check_file "SETUP_COMPLETE.md" && echo -e "${GREEN}✅${NC} Setup documentation exists"
check_file "README.md" && echo -e "${GREEN}✅${NC} README exists"
echo ""

echo "================================"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ Setup verification complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Create backend/.env from backend/env.template"
    echo "2. Create frontend/.env.local from frontend/env.local.template"
    echo "3. Start infrastructure: docker compose up -d"
    echo "4. Run migrations: cd backend && source venv/bin/activate && alembic upgrade head"
    echo "5. Start backend: cd backend && source venv/bin/activate && python main.py"
    echo "6. Start frontend: cd frontend && npm run dev"
    exit 0
else
    echo -e "${RED}❌ Found $ERRORS issue(s)${NC}"
    echo "Please fix the issues above and run this script again."
    exit 1
fi

