# Claude Code Authentication Setup - Complete

## ✅ Setup Status

**Authentication:** ✅ Configured
**Backend Server:** ✅ Running on port 8000
**Auto-Clone Repo:** ✅ statement-pipelines
**Claude Code Instances:** ✅ Ready to spawn with auth

---

## 🔐 How Authentication Works

### Your Credentials (Stored in `.env`)
```env
CLAUDE_CODE_ACCESS_TOKEN=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
CLAUDE_CODE_REFRESH_TOKEN=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
```

**Subscription Type:** Max ($100/month)
**Rate Limit Tier:** default_claude_max_5x

### Per-Workspace Authentication

When a user starts a chat session:
1. ✅ Backend creates workspace: `workspaces/<session-id>/`
2. ✅ Creates `.claude/` directory in workspace
3. ✅ Writes `config.json` with your authentication credentials
4. ✅ Writes `settings.local.json` with full permissions
5. ✅ Starts Claude Code CLI in that workspace
6. ✅ Claude Code uses the workspace-specific auth config

**Result:** Each Claude Code instance is authenticated with **your Max subscription** credentials.

---

## 📁 Workspace Structure

```
workspaces/
├── <session-abc123>/
│   ├── .claude/
│   │   ├── config.json          # Your auth credentials (auto-generated)
│   │   └── settings.local.json  # Full permissions (auto-generated)
│   └── repo/                     # Auto-cloned statement-pipelines
│       ├── scripts/
│       ├── data/
│       └── ...
```

### Generated `config.json` (per workspace)
```json
{
  "claudeAiOauth": {
    "accessToken": "sk-ant-oat01-...",
    "refreshToken": "sk-ant-ort01-...",
    "expiresAt": 1763987494015,
    "scopes": ["user:inference", "user:profile", "user:sessions:claude_code"],
    "subscriptionType": "max",
    "rateLimitTier": "default_claude_max_5x"
  }
}
```

### Generated `settings.local.json` (per workspace)
```json
{
  "permissions": {
    "allow": ["*"],
    "deny": [],
    "ask": []
  }
}
```

---

## 🚀 How to Start the Application

### Option 1: Start Script (Easiest)
```bash
start.bat
```

### Option 2: Manual Start

**Terminal 1 - Backend:**
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
streamlit run streamlit_app.py
```

---

## 🎯 User Workflow Example

### 1. User Opens Chat
→ System creates session workspace
→ Auto-clones statement-pipelines repo
→ Generates `.claude/config.json` with your credentials
→ Starts Claude Code CLI (authenticated)

### 2. User Asks: "Find all Python scripts"
→ Sent to authenticated Claude Code instance
→ Claude Code searches in statement-pipelines repo
→ Returns list of scripts

### 3. User Asks: "Run the sales report script"
→ Same Claude Code instance (persistent session)
→ Autonomously finds and executes script
→ Returns output to user

### 4. User Asks: "Create a monthly version"
→ Same instance (has context from previous messages)
→ Creates new script based on the sales report
→ Shows created file and results

---

## ⚙️ Configuration Files

### `.env` (Main Configuration)
```env
# Claude Model
CLAUDE_MODEL=claude-sonnet-4-5-20250929

# Authentication (YOUR CREDENTIALS)
CLAUDE_CODE_ACCESS_TOKEN=sk-ant-oat01-...
CLAUDE_CODE_REFRESH_TOKEN=sk-ant-ort01-...

# Default Repository
DEFAULT_REPO_URL=https://github.com/SaurabhJalendra/statement-pipelines.git
DEFAULT_REPO_BRANCH=main

# Workspace
WORKSPACE_BASE_DIR=./workspaces

# Logging
LOG_LEVEL=DEBUG
```

---

## 🔒 Security Notes

### ⚠️ Important
1. **Never commit `.env` to git** - It contains your private credentials
2. **`.env` is in `.gitignore`** - Already protected
3. **Workspace configs auto-generated** - Per session, cleaned up after 7 days
4. **Tokens have expiration** - `expiresAt: 1763987494015` (May 2025)

### Token Refresh
- Access tokens expire automatically
- Backend uses refresh token to get new access token
- You may need to update credentials periodically

### Sharing Credentials
**DO NOT SHARE:**
- Your access token (sk-ant-oat01-...)
- Your refresh token (sk-ant-ort01-...)
- Your `.env` file

---

## 🧪 Testing

### Test 1: Verify Server is Running
```bash
curl http://localhost:8000/
```
**Expected:** `{"message":"Claude Code Chatbot API","status":"running"}`

### Test 2: Create a Session (via Frontend)
1. Open Streamlit UI: http://localhost:8501
2. Send a message: "Hello, can you list files?"
3. Watch backend logs for:
   - ✅ Session created
   - ✅ Repo cloned
   - ✅ Claude Code instance started
   - ✅ Auth configured

### Test 3: Check Workspace Generation
```bash
dir workspaces
```
You should see session directories, each with:
- `.claude/config.json` (your auth)
- `.claude/settings.local.json` (permissions)
- `repo/` (cloned statement-pipelines)

---

## 📊 Monitoring

### Backend Logs to Watch For

**✅ Good Signs:**
```
{"event": "auto_cloning_default_repo", ...}
{"event": "default_repo_cloned", ...}
{"event": "Creating new Claude Code instance", ...}
{"event": "Configured Claude Code authentication", ...}
{"event": "Claude Code instance started", "pid": 12345}
```

**⚠️ Warnings:**
```
{"event": "No Claude Code credentials found in environment"}
```
→ Check your `.env` file

**❌ Errors:**
```
{"event": "Failed to start Claude Code", ...}
```
→ Check if `claude.exe` is accessible
→ Check credentials are valid

---

## 🐛 Troubleshooting

### Issue: "No Claude Code credentials found"
**Solution:**
1. Check `.env` file has `CLAUDE_CODE_ACCESS_TOKEN` and `CLAUDE_CODE_REFRESH_TOKEN`
2. Restart backend server
3. Check environment variables are loaded

### Issue: "Claude Code instance failed to start"
**Solution:**
1. Verify Claude Code is installed: `claude --version`
2. Check `claude.exe` path: `C:\Users\Saurabh\.local\bin\claude.exe`
3. Try manual start: `claude chat` (should work without browser auth now)

### Issue: "Tokens expired"
**Solution:**
1. Tokens expire in May 2025
2. When expired, re-authenticate Claude Code manually
3. Copy new tokens from `%USERPROFILE%\.claude\config.json`
4. Update `.env` file with new tokens

---

## 📝 Summary

✅ **Authentication configured** for backend Claude Code instances
✅ **Each session gets its own authenticated Claude Code instance**
✅ **Credentials stored securely in `.env`** (not committed to git)
✅ **Workspace-specific auth configs** auto-generated
✅ **Full autonomous permissions** for script execution
✅ **statement-pipelines auto-cloned** for each session

**Next Step:** Start using the application! Open the Streamlit UI and start chatting with Claude Code.

---

**Last Updated:** 2025-11-24
**Authentication Status:** ✅ Active
**Subscription:** Claude Max ($100/month)
