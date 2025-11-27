# Claude Code Integration Setup

This application now uses **Claude Code CLI** instead of the Claude API, allowing you to leverage your $100/month Claude Code subscription instead of paying per-token API costs.

## 🎯 How It Works

### Automatic Repository Setup
- When a user starts a new chat session, the system **automatically clones** the configured repository
- Claude Code CLI starts with **full autonomous permissions** in that repository
- Users can immediately ask Claude to run scripts, generate reports, or modify files
- **One persistent Claude Code instance per session** maintains conversation context

### User Workflow Example

```
User starts session
  ↓
System automatically clones: statement-pipelines repo
  ↓
Claude Code CLI starts in repo directory
  ↓
User: "Find all Python scripts for sales analysis"
  ↓
Claude Code: Searches repo, lists scripts
  ↓
User: "Run the monthly sales report"
  ↓
Claude Code: Executes script, returns results
  ↓
User: "Create a quarterly version of that script"
  ↓
Claude Code: Creates new script based on context
```

## ⚙️ Configuration

### 1. Environment Variables (`.env`)

```env
# Default Repository (Required)
DEFAULT_REPO_URL=https://github.com/SaurabhJalendra/statement-pipelines.git
DEFAULT_REPO_BRANCH=main

# Claude Model (Optional)
CLAUDE_MODEL=claude-sonnet-4-5-20250929

# Workspace Directory (Optional)
WORKSPACE_BASE_DIR=./workspaces

# Logging (Optional)
LOG_LEVEL=DEBUG
```

### 2. Claude Code CLI

**Must be installed and authenticated:**
```bash
# Check if Claude Code is installed
claude --version

# Should show: 2.0.50 (Claude Code)
```

**Location on Windows:**
```
C:\Users\<YourUsername>\.local\bin\claude.exe
```

## 🚀 Starting the Application

### Option 1: Using Start Scripts

**Windows:**
```bash
start.bat
```

**Linux/Mac:**
```bash
./start.sh
```

### Option 2: Manual Start

**Backend:**
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
streamlit run streamlit_app.py
```

## 📁 Architecture

### Session Lifecycle

```
1. User opens chat → New session created
                    ↓
2. System clones repo → workspaces/<session-id>/repo/
                    ↓
3. Claude Code starts → In repo directory with full permissions
                    ↓
4. User sends messages → Same Claude Code instance handles all
                    ↓
5. Session ends → Claude Code instance terminated
```

### Directory Structure

```
workspaces/
├── <session-1-id>/
│   ├── .claude/
│   │   └── settings.local.json  # Auto-generated permissions
│   └── repo/                     # Cloned statement-pipelines
│       ├── scripts/
│       ├── data/
│       └── ...
├── <session-2-id>/
│   └── repo/                     # Separate clone for session 2
└── ...
```

### Permissions Configuration

Each workspace gets `.claude/settings.local.json`:
```json
{
  "permissions": {
    "allow": ["*"],  // Auto-approve everything
    "deny": [],
    "ask": []
  }
}
```

This ensures Claude Code runs **fully autonomously** without prompting for permission.

## 🔧 Key Features

### ✅ Persistent Sessions
- One Claude Code CLI process per chat session
- Maintains conversation context across multiple messages
- Claude remembers previous files, scripts, and actions

### ✅ Full Autonomy
- Claude Code can read, write, execute any file
- Runs scripts automatically
- Commits and pushes changes if needed
- No manual approval required

### ✅ Multi-User Support
- Each user gets an isolated workspace
- Concurrent sessions supported
- No interference between users

### ✅ Automatic Cleanup
- Old workspaces cleaned up after 7 days
- Claude Code instances terminated on session end
- Graceful shutdown on server stop

## 🎭 Use Cases

### 1. Running Existing Scripts
```
User: "Run the sales report script"
Claude Code:
  - Finds scripts/sales_report.py
  - Executes: python scripts/sales_report.py
  - Returns results
```

### 2. Creating New Scripts
```
User: "Generate a customer churn analysis"
Claude Code:
  - Reads data structure
  - Creates analysis/customer_churn.py
  - Runs the script
  - Returns analysis report
```

### 3. Multi-Step Tasks
```
User: "Find all data processing scripts and run them in order"
Claude Code:
  - Searches for *.py with "process" or "data"
  - Determines correct execution order
  - Runs: clean_data.py → transform_data.py → analyze_data.py
  - Summarizes results
```

## 🐛 Troubleshooting

### Claude Code Instance Not Starting

**Check if Claude Code is installed:**
```bash
claude --version
```

**Check if authenticated:**
```bash
claude chat
# Should open Claude Code, not show login prompt
```

### Repository Not Cloning

**Check .env configuration:**
```bash
cat .env | grep DEFAULT_REPO_URL
```

**Check git access:**
```bash
git clone https://github.com/SaurabhJalendra/statement-pipelines.git test-clone
```

### Output Not Parsing Correctly

The Claude Code CLI output parser is still being refined. If responses aren't captured:

1. Check logs for parsing errors
2. Examine `backend/app/parsers/claude_output_parser.py`
3. Adjust `_read_response()` timeout and completion detection

## 📊 Monitoring

### View Active Sessions
```bash
curl http://localhost:8000/api/sessions
```

### Check Claude Code Instances
The backend logs show:
- When Claude Code instances start (PID shown)
- When messages are sent
- When instances are cleaned up

### Progress Tracking
```bash
curl http://localhost:8000/api/progress/<session-id>
```

## 💰 Cost Savings

### Before (Claude API)
- ~$3 per million input tokens
- ~$15 per million output tokens
- Variable cost per request

### After (Claude Code CLI)
- Fixed $100/month subscription
- Unlimited usage within subscription
- No per-token charges

**Estimated savings:** Significant if you have more than ~10-20 chat sessions per day.

## ⚠️ Important Notes

### Terms of Service
Using Claude Code CLI in an automated backend **may violate Anthropic's terms of service**. This implementation:
- Is experimental
- May break with Claude Code updates
- Should be used with Anthropic's approval

**Recommendation:** Contact Anthropic to confirm this usage is allowed under your subscription.

### Limitations
- No official API for Claude Code CLI
- Output parsing is fragile
- Updates to Claude Code may break integration
- Harder to debug than API calls

## 🔄 Fallback to API

If you need to switch back to Claude API:

1. Uncomment in `backend/app/main.py`:
```python
claude_service = ClaudeService()
```

2. Replace chat endpoint logic with API-based version

3. Add `CLAUDE_API_KEY` to `.env`

## 📝 Development

### Adding Custom Repositories

Users can still clone other repos during a session:
```
User: "Clone https://github.com/other/repo"
Claude Code: [clones to workspace/other-repo]
```

### Modifying Permissions

Edit the generated `.claude/settings.local.json` in workspaces, or modify:
```python
# backend/app/claude_code_service.py
def _setup_autonomous_permissions(self):
    settings = {
        "permissions": {
            "allow": ["specific", "tools"],
            "ask": ["dangerous_operations"]
        }
    }
```

## 📚 References

- [Claude Code Documentation](https://docs.anthropic.com/claude-code)
- [Claude API Documentation](https://docs.anthropic.com/claude/reference)
- [Repository: statement-pipelines](https://github.com/SaurabhJalendra/statement-pipelines)

---

**Status:** ✅ Implemented | ⚠️ Output parsing needs debugging | 🚧 Active development
