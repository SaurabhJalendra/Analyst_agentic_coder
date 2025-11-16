#!/bin/bash
# Startup script for Claude Code Chatbot (Linux/Mac)

echo "🤖 Starting Claude Code Chatbot..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📝 Please copy .env.example to .env and add your Claude API key"
    exit 1
fi

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies if needed
echo "📦 Checking dependencies..."
pip install -q -r backend/requirements.txt
pip install -q -r frontend/requirements.txt

# Start backend in background
echo "🚀 Starting backend on http://localhost:8000..."
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start frontend
echo "🌐 Starting frontend on http://localhost:8501..."
cd frontend
streamlit run streamlit_app.py

# Cleanup on exit
trap "kill $BACKEND_PID" EXIT
