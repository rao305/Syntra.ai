#!/bin/bash

# Syntra Development Environment Setup Script
# This script sets up local PostgreSQL for development
# Production uses Supabase (configured in CI/CD)

set -e

echo "🚀 Setting up Syntra development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "This script is designed for macOS. Please adapt for your OS."
    exit 1
fi

# Install Homebrew if not present
if ! command -v brew &> /dev/null; then
    print_status "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install PostgreSQL
if ! command -v psql &> /dev/null; then
    print_status "Installing PostgreSQL..."
    brew install postgresql@14
    brew services start postgresql@14
    
    # Add to PATH
    echo 'export PATH="/opt/homebrew/opt/postgresql@14/bin:$PATH"' >> ~/.zshrc
    export PATH="/opt/homebrew/opt/postgresql@14/bin:$PATH"
else
    print_success "PostgreSQL already installed"
fi

# Start PostgreSQL service
print_status "Starting PostgreSQL service..."
brew services start postgresql@14 2>/dev/null || true

# Create database and user
print_status "Creating database 'dac'..."
createdb dac 2>/dev/null || print_warning "Database 'dac' may already exist"

# Install Python dependencies
print_status "Setting up Python environment..."
if [ ! -d "backend/venv" ]; then
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    cd ..
else
    print_success "Python virtual environment already exists"
fi

# Setup database tables
print_status "Creating database tables..."
cd backend
source venv/bin/activate
python -c "
import asyncio
from app.database import engine, Base
from app.models import *

async def create_tables():
    async with engine.begin() as conn:
        # Create basic tables (skip vector dependencies for local dev)
        from app.models import Org, User, Thread, Message, AuditLog, ProviderKey, RouterRun
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=[
            Org.__table__, User.__table__, Thread.__table__, Message.__table__, 
            AuditLog.__table__, ProviderKey.__table__, RouterRun.__table__
        ]))
    print('✅ Database tables created')

asyncio.run(create_tables())
"

# Create default organization
print_status "Creating default organization..."
PGPASSWORD=postgres psql -h localhost -U $USER -d dac -c "
INSERT INTO orgs (id, name, slug) VALUES ('org_demo', 'Demo Organization', 'demo') 
ON CONFLICT (id) DO NOTHING;
" 2>/dev/null || print_warning "Default org may already exist"

cd ..

# Install Node.js dependencies
if [ ! -d "frontend/node_modules" ]; then
    print_status "Installing Node.js dependencies..."
    cd frontend
    npm install
    cd ..
else
    print_success "Node.js dependencies already installed"
fi

# Create environment files if they don't exist
if [ ! -f "backend/.env" ]; then
    print_status "Creating backend .env file..."
    cp backend/env.example backend/.env
    print_warning "Please configure your API keys in backend/.env"
fi

if [ ! -f "frontend/.env.local" ]; then
    print_status "Creating frontend .env.local file..."
    cp frontend/env.example frontend/.env.local
    print_warning "Please configure your Clerk keys in frontend/.env.local"
fi

print_success "🎉 Development environment setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Configure API keys in backend/.env"
echo "   2. Configure Clerk keys in frontend/.env.local" 
echo "   3. Run: ./scripts/dev-start.sh"
echo ""
echo "📚 For production deployment, see: docs/DEPLOYMENT.md"