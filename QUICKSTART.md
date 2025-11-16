# Quick Start Guide

Get Claude Code Chatbot running in 5 minutes!

## Prerequisites

- Python 3.11 or higher
- Claude API key from [Anthropic Console](https://console.anthropic.com/)
- Git installed

## Quick Setup

### Step 1: Clone and Navigate

```bash
git clone <your-repo-url>
cd Analyst_agentic_coder
```

### Step 2: Configure API Key

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your Claude API key
# CLAUDE_API_KEY=sk-ant-your-actual-key-here
```

### Step 3: Run the Application

**Windows**:
```bash
start.bat
```

**Linux/Mac**:
```bash
chmod +x start.sh
./start.sh
```

### Step 4: Open in Browser

The application will automatically open at:
- **Frontend**: http://localhost:8501
- **Backend API**: http://localhost:8000

## First Steps

1. **Choose a repository**:
   - Click "Browse Local" in the sidebar
   - Navigate to any code repository
   - Click "Select"

2. **Start chatting**:
   - Type a message like "What files are in this repository?"
   - Claude will propose operations
   - Review and approve

3. **Try some commands**:
   - "Show me the main Python files"
   - "Search for TODO comments"
   - "What does the README say?"

## Manual Setup (if scripts don't work)

### Terminal 1 - Backend

```bash
# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Install dependencies and run
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### Terminal 2 - Frontend

```bash
# Activate same venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies and run
cd frontend
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Docker Setup (Alternative)

If you prefer Docker:

```bash
# Make sure Docker is running

# Copy .env file
cp .env.example .env
# Edit .env and add your API key

# Start with Docker Compose
docker-compose up --build
```

Access at http://localhost:8501

## Troubleshooting

### "Module not found" errors
```bash
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
```

### Backend won't start
- Check if port 8000 is in use
- Verify Python version: `python --version`
- Check API key in `.env` file

### Frontend can't connect
- Make sure backend is running on port 8000
- Check backend terminal for errors
- Try accessing http://localhost:8000/docs

### Claude API errors
- Verify API key is correct in `.env`
- Check you have API credits at console.anthropic.com
- Try a simple message first

## Need More Help?

- Full documentation: See `README.md`
- API documentation: http://localhost:8000/docs
- Check logs in the terminal windows

## Example Queries to Try

Once running, try these:

1. **File exploration**:
   - "List all Python files in this project"
   - "Show me the contents of README.md"

2. **Code search**:
   - "Find all TODO comments"
   - "Search for functions that handle errors"

3. **Git operations**:
   - "What branch am I on?"
   - "Show me recent changes"

4. **Analysis**:
   - "Explain the structure of this project"
   - "Find potential issues in the code"

Happy coding! 🚀
