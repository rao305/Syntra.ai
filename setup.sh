#!/bin/bash
# Quick setup script for Cross-LLM Thread Hub

set -e

echo "🚀 Cross-LLM Thread Hub Setup"
echo "================================"
echo

# Check prerequisites
echo "Checking prerequisites..."
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 is required but not installed."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js is required but not installed."; exit 1; }
echo "✅ Prerequisites OK"
echo

# Backend setup
echo "📦 Setting up backend..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo "⚠️  Please edit backend/.env with your credentials!"
else
    echo "✅ backend/.env already exists"
fi

cd ..
echo

# Frontend setup
echo "🎨 Setting up frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "Installing Node dependencies..."
    npm install --silent
else
    echo "✅ Node modules already installed"
fi

if [ ! -f ".env.local" ]; then
    echo "Creating .env.local from template..."
    cp .env.example .env.local
    echo "⚠️  Please edit frontend/.env.local with your credentials!"
else
    echo "✅ frontend/.env.local already exists"
fi

cd ..
echo

# Generate keys
echo "🔑 Generating secret keys..."
echo
echo "Add these to your .env files:"
echo "----------------------------"
echo "SECRET_KEY=$(openssl rand -hex 32)"
echo "NEXTAUTH_SECRET=$(openssl rand -base64 32)"
echo
echo "For ENCRYPTION_KEY, run:"
echo "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
echo

echo "✅ Setup complete!"
echo
echo "Next steps:"
echo "1. Edit backend/.env with your database and service credentials"
echo "2. Edit frontend/.env.local with your auth credentials"
echo "3. Run migrations: cd backend && alembic upgrade head"
echo "4. Start backend: cd backend && python main.py"
echo "5. Start frontend: cd frontend && npm run dev"
echo
echo "📚 See README.md for detailed instructions"
