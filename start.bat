@echo off
REM Startup script for Claude Code Chatbot (Windows)

echo 🤖 Starting Claude Code Chatbot...

REM Check if .env exists
if not exist .env (
    echo ❌ .env file not found!
    echo 📝 Please copy .env.example to .env and add your Claude API key
    pause
    exit /b 1
)

REM Check if venv exists
if not exist venv (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate venv
call venv\Scripts\activate.bat

REM Install dependencies
echo 📦 Installing dependencies...
pip install -q -r backend\requirements.txt
pip install -q -r frontend\requirements.txt

REM Start backend in background
echo 🚀 Starting backend on http://localhost:8000...
start /B cmd /c "cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

REM Wait for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend
echo 🌐 Starting frontend on http://localhost:8501...
cd frontend
streamlit run streamlit_app.py

REM Cleanup
taskkill /F /IM uvicorn.exe >nul 2>&1
