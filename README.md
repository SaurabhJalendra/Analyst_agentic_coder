# Analyst Agentic Coder

A powerful AI-powered coding assistant that leverages Claude Code CLI to perform autonomous coding operations including code analysis, file manipulation, git operations, data visualization, and report generation.

## Features

### Core Capabilities
- **AI Chat Interface**: Natural language interaction with Claude AI for coding assistance
- **Autonomous Tool Execution**: Claude Code CLI handles all tool calls autonomously without manual approval
- **Code Analysis**: Explore, understand, and refactor codebases with AI assistance
- **File Operations**: Read, write, edit, and search files across your project
- **Git Operations**: Clone repos, commit changes, manage branches, and handle version control
- **Command Execution**: Run shell commands, scripts, and build processes
- **Data Visualization**: Generate charts, graphs, and visual reports from data
- **Report Generation**: Create HTML, PDF, and Excel reports

### User Experience
- **Modern React UI**: Clean, responsive interface with dark theme
- **Real-time Progress Tracking**: See what Claude is doing in real-time
- **Inline Visualizations**: Generated charts and graphs appear directly in chat messages
- **Session Management**: Isolated workspaces per session with persistent history
- **User Authentication**: JWT-based authentication with user registration
- **Visualizations Panel**: View all generated charts and reports for a session

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│  - Modern UI with TailwindCSS                                   │
│  - Real-time progress indicators                                │
│  - Markdown rendering with syntax highlighting                  │
│  - Inline image display for visualizations                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Nginx Reverse Proxy                          │
│  - Routes /api/* to backend                                     │
│  - Serves static frontend assets                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                             │
│  - REST API for chat, sessions, files                           │
│  - JWT authentication                                           │
│  - Claude Code CLI process management                           │
│  - Workspace file scanning for visualizations                   │
└─────────────────────────────────────────────────────────────────┘
                    │                   │
                    ▼                   ▼
┌──────────────────────────┐  ┌────────────────────────────────┐
│   PostgreSQL Database    │  │      Claude Code CLI           │
│  - User accounts         │  │  - Autonomous tool execution   │
│  - Chat sessions         │  │  - File operations             │
│  - Message history       │  │  - Git operations              │
│  - Tool call records     │  │  - Command execution           │
└──────────────────────────┘  └────────────────────────────────┘
```

### Technology Stack

| Component | Technology |
|-----------|------------|
| Frontend | React 19, TypeScript, TailwindCSS 4, Vite |
| Backend | FastAPI, Python 3.11, Uvicorn |
| Database | PostgreSQL 16 with asyncpg |
| AI Engine | Claude Code CLI (Anthropic) |
| Authentication | JWT (python-jose), bcrypt |
| Containerization | Docker, Docker Compose |
| Reverse Proxy | Nginx |

## Prerequisites

- **Docker** and **Docker Compose** (recommended)
- **Claude Code CLI** authenticated on host machine
- For native setup:
  - Python 3.11+
  - Node.js 20+
  - PostgreSQL 16+

## Quick Start (Docker)

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd Analyst_agentic_coder
```

### 2. Authenticate Claude Code CLI

Before running the application, authenticate Claude Code on your host machine:

```bash
# Install Claude Code CLI if not already installed
npm install -g @anthropic-ai/claude-code

# Authenticate with your Anthropic account
claude /login
```

This creates credentials in `~/.claude/` which will be mounted into the Docker container.

### 3. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

**Required configuration:**
- `JWT_SECRET_KEY`: Generate a secure random key for JWT tokens
- `POSTGRES_PASSWORD`: Set a secure database password
- `DEFAULT_REPO_URL`: (Optional) Repository to auto-clone for each session
- `GITHUB_ACCESS_TOKEN`: (Optional) For private repository access

### 4. Build and Run

```bash
# Build and start all services
docker compose up -d --build

# Check container status
docker compose ps

# View logs
docker compose logs -f
```

### 5. Access the Application

- **Frontend**: http://localhost (port 80)
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### 6. Create Your Account

1. Open http://localhost in your browser
2. Click "Create Account" on the login page
3. Register with username, email, and password
4. Start chatting with the AI assistant!

## Environment Variables

Create a `.env` file in the project root with the following variables:

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `JWT_SECRET_KEY` | Secret key for JWT token signing | `your-secure-random-string-here` |
| `POSTGRES_PASSWORD` | PostgreSQL database password | `your-secure-db-password` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `CLAUDE_MODEL` | Claude model to use | `claude-sonnet-4-5-20250929` |
| `DEFAULT_REPO_URL` | Repository to auto-clone for sessions | (none) |
| `DEFAULT_REPO_BRANCH` | Branch to checkout | `main` |
| `GITHUB_ACCESS_TOKEN` | GitHub PAT for private repos | (none) |
| `POSTGRES_USER` | PostgreSQL username | `coolbot` |
| `POSTGRES_DB` | PostgreSQL database name | `coolbot_db` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `BACKEND_PORT` | Backend API port | `8000` |
| `FRONTEND_PORT` | Frontend port | `80` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token expiry | `1440` (24 hours) |
| `MAX_CONTEXT_LENGTH` | Max context for Claude | `200000` |
| `WORKSPACE_BASE_DIR` | Workspace directory | `./workspaces` |

## Usage

### Getting Started

1. **Login or Register**: Create an account or login with existing credentials
2. **Start a New Chat**: Click "New Chat" in the sidebar
3. **Ask Questions**: Type your coding questions or requests

### Example Prompts

**Code Analysis:**
```
Analyze the codebase structure and explain how the main components work
```

**File Operations:**
```
Show me the contents of main.py and explain what it does
```

**Data Visualization:**
```
Read the sales_data.csv file and create a bar chart showing monthly revenue
```

**Git Operations:**
```
Show me the recent commits and create a summary of changes
```

**Report Generation:**
```
Analyze the data in reports/ folder and create a comprehensive HTML dashboard
```

**Bug Fixing:**
```
Find potential bugs in the authentication module and suggest fixes
```

### Viewing Visualizations

Generated charts and graphs appear in two ways:
1. **Inline in Messages**: Images generated during a response appear directly in that message
2. **Visualizations Panel**: Click the "Visualizations" button in the header to see all session images

## API Reference

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register a new user |
| POST | `/api/auth/login` | Login and get JWT token |
| GET | `/api/auth/me` | Get current user info |
| POST | `/api/auth/refresh` | Refresh JWT token |

### Chat Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send a message and get AI response |
| GET | `/api/session/{id}/history` | Get chat history for a session |
| GET | `/api/progress/{id}` | Get real-time progress for a session |

### Session Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sessions` | List all sessions for current user |
| DELETE | `/api/sessions/{id}` | Delete a specific session |
| DELETE | `/api/sessions` | Delete all sessions (admin) |

### File Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/workspace/{session_id}/files/{path}` | Download a file from workspace |
| GET | `/api/workspace/{session_id}/list/{path}` | List files in a directory |
| GET | `/api/workspace/{session_id}/visualizations` | Get all images/reports for session |

### Repository Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/repos/clone` | Clone a git repository |
| POST | `/api/repos/browse` | Browse a local directory |

Full API documentation available at: http://localhost:8000/docs

## Project Structure

```
Analyst_agentic_coder/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI application & endpoints
│   │   ├── database.py             # SQLAlchemy models & database setup
│   │   ├── auth.py                 # JWT authentication logic
│   │   ├── claude_code_service.py  # Claude Code CLI integration
│   │   ├── workspace_manager.py    # Session workspace management
│   │   ├── progress_tracker.py     # Real-time progress tracking
│   │   ├── git_utils.py            # Git operations utilities
│   │   └── db_utils.py             # Database utilities
│   ├── Dockerfile                  # Backend Docker image
│   └── requirements.txt            # Python dependencies
│
├── frontend-react/
│   ├── src/
│   │   ├── App.tsx                 # Main application component
│   │   ├── components/
│   │   │   ├── ChatMessage.tsx     # Chat message with inline images
│   │   │   ├── ChatInput.tsx       # Message input component
│   │   │   ├── Sidebar.tsx         # Session sidebar
│   │   │   ├── ProgressIndicator.tsx # Progress display
│   │   │   ├── ConnectionStatus.tsx  # Connection status indicator
│   │   │   ├── Login.tsx           # Login/Register page
│   │   │   └── VisualizationsPanel.tsx # All visualizations modal
│   │   ├── hooks/
│   │   │   └── useChat.ts          # Chat state management hook
│   │   ├── services/
│   │   │   └── api.ts              # API client & utilities
│   │   └── types/
│   │       └── index.ts            # TypeScript type definitions
│   ├── Dockerfile                  # Frontend Docker image
│   ├── nginx.conf                  # Nginx configuration
│   ├── package.json                # Node.js dependencies
│   └── tailwind.config.js          # TailwindCSS configuration
│
├── docker-compose.yml              # Docker Compose configuration
├── .env.example                    # Environment variables template
└── README.md                       # This file
```

## Native Development Setup

### Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
cd backend
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/dbname"
export JWT_SECRET_KEY="your-secret-key"

# Run the backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend-react

# Install dependencies
npm install

# Run development server
npm run dev
```

### PostgreSQL Setup

```bash
# Using Docker for PostgreSQL only
docker run -d \
  --name analyst-postgres \
  -e POSTGRES_USER=coolbot \
  -e POSTGRES_PASSWORD=your-password \
  -e POSTGRES_DB=coolbot_db \
  -p 5432:5432 \
  postgres:16-alpine
```

## Troubleshooting

### Container Issues

**Containers won't start:**
```bash
# Check logs
docker compose logs backend
docker compose logs frontend

# Rebuild containers
docker compose down
docker compose up -d --build
```

**Database connection errors:**
```bash
# Check PostgreSQL is healthy
docker compose ps
docker compose logs postgres

# Reset database (warning: deletes all data)
docker compose down -v
docker compose up -d
```

### Authentication Issues

**"Invalid credentials" error:**
- Verify username and password are correct
- Check if user exists in database

**JWT token expired:**
- Login again to get a new token
- Increase `ACCESS_TOKEN_EXPIRE_MINUTES` in .env

### Claude Code Issues

**"Claude Code not responding":**
```bash
# Verify Claude credentials are mounted
docker compose exec backend ls -la /home/appuser/.claude/

# Re-authenticate on host
claude /login

# Restart backend
docker compose restart backend
```

**Tool execution failures:**
- Check workspace permissions
- Verify git is working: `docker compose exec backend git --version`

### Visualization Issues

**Images not appearing:**
- Check browser console for errors
- Verify file serving endpoint: `curl http://localhost:8000/api/workspace/{session_id}/visualizations`
- Check workspace directory permissions

**Wrong images shown:**
- Each message now shows only images created during that specific interaction
- Use "Visualizations" button to see all session images

### Performance Issues

**Slow responses:**
- Claude Code operations can take time for complex tasks
- Check progress indicator for current status
- Consider increasing `timeout` values for long-running operations

## Security Considerations

- **JWT Secret**: Use a strong, unique `JWT_SECRET_KEY` in production
- **Database Password**: Use a secure `POSTGRES_PASSWORD`
- **GitHub Token**: Use minimal-scope tokens, rotate regularly
- **Claude Credentials**: Keep `~/.claude/` credentials secure
- **Network**: Backend is exposed on port 8000 - use firewall rules in production
- **CORS**: Currently allows all origins - restrict in production
- **File Access**: Claude can access files within the workspace directory

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `npm test` / `pytest`
5. Commit changes: `git commit -m "Add my feature"`
6. Push to branch: `git push origin feature/my-feature`
7. Submit a pull request

## Acknowledgments

- Built with [Claude AI](https://www.anthropic.com/claude) by Anthropic
- [Claude Code CLI](https://github.com/anthropics/claude-code) for autonomous tool execution
- [FastAPI](https://fastapi.tiangolo.com/) for backend API
- [React](https://react.dev/) for frontend UI
- [TailwindCSS](https://tailwindcss.com/) for styling
- [PostgreSQL](https://www.postgresql.org/) for database
