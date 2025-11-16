# Claude Code Chatbot

A powerful chatbot interface that leverages Claude AI to perform various coding operations including file manipulation, code search, command execution, and git operations.

## Features

- **Chat Interface**: Natural language interaction with Claude AI
- **File Operations**: Read, write, and edit files with intelligent suggestions
- **Code Search**: Advanced grep and glob patterns for finding code
- **Git Operations**: Clone, commit, push, pull, and manage repositories
- **Command Execution**: Run shell commands and scripts
- **Plan Approval**: Review all operations before execution for safety
- **Multi-Repository**: Work with multiple repositories and local codebases
- **Session Management**: Isolated workspaces per session
- **Debug Logging**: Comprehensive logging for troubleshooting

## Architecture

- **Backend**: FastAPI with async support
- **Frontend**: Streamlit for intuitive UI
- **AI**: Claude 3.5 Sonnet with tool calling
- **Database**: SQLite for chat history
- **Tools**: Custom implementations of file, search, bash, and git operations

## Prerequisites

- Python 3.11+
- Claude API key from Anthropic
- Git installed on your system
- (Optional) Docker and Docker Compose

## Installation

### Option 1: Native Python Setup

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd Analyst_agentic_coder
   ```

2. **Create and activate virtual environment**:
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/Mac
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install backend dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   cd ..
   ```

4. **Install frontend dependencies**:
   ```bash
   cd frontend
   pip install -r requirements.txt
   cd ..
   ```

5. **Configure environment variables**:
   ```bash
   # Copy the example file
   cp .env.example .env

   # Edit .env and add your Claude API key
   # CLAUDE_API_KEY=your_actual_api_key_here
   ```

6. **Run the application**:

   **Terminal 1 - Backend**:
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   **Terminal 2 - Frontend**:
   ```bash
   cd frontend
   streamlit run streamlit_app.py
   ```

7. **Access the application**:
   - Frontend (Streamlit): http://localhost:8501
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Option 2: Docker Setup

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd Analyst_agentic_coder
   ```

2. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your Claude API key
   ```

3. **Build and run with Docker Compose**:
   ```bash
   docker-compose up --build
   ```

4. **Access the application**:
   - Frontend: http://localhost:8501
   - Backend API: http://localhost:8000

## Usage

### Getting Started

1. **Open the application** at http://localhost:8501

2. **Choose a repository source**:
   - **Browse Local**: Navigate to an existing repository on your machine
   - **Clone from URL**: Clone a repository from GitHub/GitLab
   - **Current Workspace**: Use the session's temporary workspace

3. **Start chatting**: Ask Claude to help with various tasks:

### Example Prompts

**File Operations**:
- "Show me the contents of main.py"
- "Create a new file called utils.py with helper functions"
- "Edit the README and add installation instructions"
- "Find all Python files in this repository"

**Code Search**:
- "Search for all functions named 'process_data'"
- "Find all files that import pandas"
- "Show me where the API endpoints are defined"

**Git Operations**:
- "What files have been changed?"
- "Show me the git diff"
- "Create a commit with message 'Add new feature'"
- "Clone the repository https://github.com/user/repo"

**Command Execution**:
- "Run the tests"
- "Install the dependencies from requirements.txt"
- "Check the Python version"
- "Run npm build"

**Code Analysis**:
- "Analyze this codebase and explain the structure"
- "Find potential bugs in auth.py"
- "Suggest improvements for this function"
- "Review the error handling in this module"

### Plan Approval Workflow

1. **Ask Claude** to perform an operation
2. **Review the plan**: Claude will show what operations it wants to perform
3. **Approve or reject**: Click "Approve & Execute" or "Reject"
4. **View results**: See the execution results and Claude's summary

## Configuration

### Environment Variables

Edit `.env` file:

```env
# Required: Your Claude API key
CLAUDE_API_KEY=sk-ant-...

# Optional: Claude model (default: claude-3-5-sonnet-20241022)
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# Optional: Log level (default: DEBUG)
LOG_LEVEL=DEBUG

# Optional: Workspace directory (default: ./workspaces)
WORKSPACE_BASE_DIR=./workspaces
```

### Advanced Configuration

**Maximum Context Length**:
```python
# In backend/app/claude_service.py
MAX_TOKENS = 4096  # Adjust based on your needs
```

**Workspace Cleanup**:
```python
# Workspaces are session-based and can be cleaned up manually
# Located in: ./workspaces/<session-id>/
```

## API Reference

### Backend Endpoints

- `POST /api/chat` - Send a chat message
- `POST /api/execute` - Execute approved tool calls
- `GET /api/session/{id}/history` - Get chat history
- `POST /api/repos/browse` - Browse local directories
- `POST /api/repos/clone` - Clone a git repository
- `GET /api/files/{path}` - Read a file

Full API documentation: http://localhost:8000/docs

## Troubleshooting

### Backend won't start

- Check that port 8000 is available
- Verify Claude API key is set in `.env`
- Check Python version: `python --version` (should be 3.11+)
- Install dependencies: `pip install -r backend/requirements.txt`

### Frontend won't start

- Check that port 8501 is available
- Verify backend is running on port 8000
- Install dependencies: `pip install -r frontend/requirements.txt`

### Claude API errors

- Verify API key is correct in `.env`
- Check API key permissions at console.anthropic.com
- Check your API usage limits

### Tool execution fails

- Check file permissions in workspace directory
- Verify git is installed: `git --version`
- Check command syntax for bash operations

### Database errors

- Delete `chatbot.db` to reset (will lose chat history)
- Check file permissions on database file

## Development

### Project Structure

```
Analyst_agentic_coder/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── claude_service.py    # Claude API integration
│   │   ├── tool_executor.py     # Tool execution engine
│   │   ├── workspace_manager.py # Session workspaces
│   │   ├── database.py          # SQLite models
│   │   └── tools/               # Tool implementations
│   │       ├── file_ops.py      # File operations
│   │       ├── search.py        # Grep search
│   │       ├── bash.py          # Command execution
│   │       └── git_ops.py       # Git operations
│   └── requirements.txt
├── frontend/
│   ├── streamlit_app.py         # Main UI
│   ├── components/
│   │   ├── chat.py              # Chat interface
│   │   ├── plan_approval.py     # Approval UI
│   │   ├── file_viewer.py       # File viewer
│   │   └── repo_browser.py      # Directory browser
│   └── requirements.txt
├── docker-compose.yml           # Docker setup
├── Dockerfile                   # Docker image
└── README.md                    # This file
```

### Adding New Tools

1. **Define tool in `backend/app/claude_service.py`**:
   ```python
   {
       "name": "my_new_tool",
       "description": "Description of what it does",
       "input_schema": {
           "type": "object",
           "properties": {
               "param1": {"type": "string", "description": "..."}
           },
           "required": ["param1"]
       }
   }
   ```

2. **Implement tool in appropriate file**:
   ```python
   async def my_new_tool(param1: str) -> dict:
       # Implementation
       return {"result": "..."}
   ```

3. **Add to tool executor in `tool_executor.py`**:
   ```python
   elif tool_name == "my_new_tool":
       result = await self.my_ops.my_new_tool(
           param1=tool_input.get("param1")
       )
   ```

## Security Considerations

- **API Key**: Never commit `.env` file with real API key
- **Command Execution**: Commands run with same permissions as the application
- **File Access**: Can access any file the application user can access
- **Network**: Backend is open to local network by default
- **Authentication**: No built-in auth - suitable for local/trusted use only

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

[Your License Here]

## Support

For issues and questions:
- GitHub Issues: [Your Issues URL]
- Documentation: This README
- API Docs: http://localhost:8000/docs

## Acknowledgments

- Built with [Claude AI](https://www.anthropic.com/claude) by Anthropic
- [FastAPI](https://fastapi.tiangolo.com/) for backend
- [Streamlit](https://streamlit.io/) for frontend
- Inspired by [Claude Code CLI](https://github.com/anthropics/claude-code)
