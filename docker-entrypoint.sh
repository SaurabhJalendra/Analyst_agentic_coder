#!/bin/bash
set -e

# Start backend in background
cd /app/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Wait for backend to be ready
echo "Waiting for backend to start..."
sleep 5

# Start frontend
cd /app/frontend
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
