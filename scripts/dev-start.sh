#!/bin/bash

# Syntra Development Server Start Script
# Starts both backend and frontend in development mode

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if PostgreSQL is running
if ! pgrep -x "postgres" > /dev/null; then
    print_warning "PostgreSQL not running. Starting..."
    brew services start postgresql@14
    sleep 2
fi

# Function to cleanup background processes
cleanup() {
    print_status "Stopping development servers..."
    jobs -p | xargs -r kill 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

print_success "🚀 Starting Syntra development environment..."

# Start backend
print_status "Starting backend server (http://localhost:8000)..."
cd backend
source venv/bin/activate
python3 main.py &
BACKEND_PID=$!
cd ..

# Give backend time to start
sleep 3

# Start frontend  
print_status "Starting frontend server (http://localhost:3000)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

print_success "✅ Development servers started!"
echo ""
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend:  http://localhost:8000"
echo "📊 Health:   http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for processes
wait $BACKEND_PID $FRONTEND_PID