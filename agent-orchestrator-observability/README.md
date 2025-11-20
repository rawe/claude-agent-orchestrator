# Agent Orchestration Observability

Real-time monitoring for Agent Orchestrator sessions. See agent activity, tool calls, and session lifecycle events as they happen.

## Quick Start

### Option 1: Docker Setup (Recommended)

**Start everything with one command:**
```bash
docker-compose up -d
```

This will:
- Build and start the backend on `http://localhost:8765`
- Build and start the frontend on `http://localhost:5173`
- Create a persistent volume for the SQLite database
- Set up networking between services

**View logs:**
```bash
docker-compose logs -f
```

**Stop services:**
```bash
docker-compose down
```

**Rebuild after code changes:**
```bash
docker-compose up -d --build
```

### Option 2: Manual Setup

**1. Install Dependencies**

**Backend:**
```bash
uv sync
```

**Frontend:**
```bash
cd frontend
npm install
cd ..
```

**2. Start the Services**

You need 3 terminals:

**Terminal 1 - Backend:**
```bash
uv run backend/main.py
```
Backend will start on `http://127.0.0.1:8765`

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```
Frontend will start on `http://localhost:5173`

**Terminal 3 - Your Agents:**
```bash
# See docs/USAGE.md for configuration (framework or standalone modes)
# From project root directory
cd ..
uv run commands/ao-new my-test-agent -p "Your task"
```

### View the Dashboard

Open your browser to: **http://localhost:5173**

You should see:
- Session list on the left sidebar
- Event timeline when a session is selected
- Real-time updates as agents execute

## Usage

This observability platform has two usage modes:

**1. Agent Orchestrator Framework (Primary)**
- Built-in observability for Agent Orchestrator commands (`ao-new`, `ao-resume`, etc.)
- Automatic session metadata tracking (agent name, project directory)
- Enable via environment variables only - no hook configuration needed

**2. Standalone / Testing (Secondary)**
- Hook-based observability for any Claude Code session
- Useful for testing or non-framework usage
- Requires hook configuration in `.claude/settings.json`

**📖 See `docs/USAGE.md` for configuration, setup instructions, and detailed workflows.**

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG_LOGGING` | `false` | Backend: Enable verbose debug output for troubleshooting. Set to `true`, `1`, or `yes` to enable. |
| `VITE_BACKEND_URL` | `http://localhost:8765` | Frontend: Backend API URL for connections. Change if backend runs on different host/port. |

**Example: Enable debug logging:**
```bash
# Docker: Edit docker-compose.yml and set DEBUG_LOGGING=true, then restart
docker-compose up -d

# Manual: Set env variable when running
DEBUG_LOGGING=true uv run backend/main.py
```

**Example: Change backend URL:**
```bash
# Docker: Edit docker-compose.yml VITE_BACKEND_URL value, then rebuild
docker-compose up -d --build

# Manual: Set env variable when running frontend
cd frontend
VITE_BACKEND_URL=http://192.168.1.100:8765 npm run dev
```

## Features

### What This MVP Includes

- ✅ **Real-time Session Tracking** - See all agent sessions as they start
- ✅ **Tool Call Monitoring** - View every tool call with full input parameters
- ✅ **Tool Results Display** - See tool outputs and execution results
- ✅ **Session Stop Detection** - Track when sessions complete
- ✅ **Error Display** - View errors from failed tool executions
- ✅ **Session List** - Browse all active and historical sessions
- ✅ **Event Timeline** - See chronological event stream per session
- ✅ **WebSocket Updates** - Real-time updates without page refresh
- ✅ **SQLite Persistence** - Events stored in `.agent-orchestrator/observability.db`

### What's NOT Included (Yet)

- ❌ Auto-reconnection (just refresh the page)
- ❌ Filtering/search
- ❌ Export functionality

## Architecture

```
┌─────────────────┐
│  Agent Session  │
│   (Claude)      │
└────────┬────────┘
         │ Hooks
         ▼
  ┌─────────────┐
  │ Hook Script │
  │  (Python)   │
  └──────┬──────┘
         │ HTTP POST
         ▼
  ┌─────────────┐      WebSocket     ┌──────────────┐
  │   Backend   │◄──────────────────►│   Frontend   │
  │  (FastAPI)  │                    │   (React)    │
  └──────┬──────┘                    └──────────────┘
         │
         ▼
  ┌─────────────┐
  │   SQLite    │
  │  Database   │
  └─────────────┘
```

## Testing

### Test Backend

```bash
uv run backend/main.py
# Visit http://127.0.0.1:8765/docs for API documentation
```

### Test Hooks Manually

```bash
# Test session_start hook
echo '{"session_id":"test-123"}' | uv run hooks/session_start_hook.py

# Test pre_tool hook
echo '{"session_id":"test-123","tool_name":"Read","tool_input":{"file_path":"/test.py"}}' | uv run hooks/pre_tool_hook.py

# Check if events were sent (look at backend logs)
```

### Test Frontend

```bash
cd frontend
npm run dev
# Visit http://localhost:5173
```

## Troubleshooting

### Hooks Not Firing

**Problem:** No events appearing in the UI when running agents

**Solutions:**
1. Check that you're using **absolute paths** in `.claude/settings.json`
2. Verify `uv` is in your PATH: `which uv`
3. Test hooks manually (see Testing section above)
4. Check backend logs for incoming POST requests
5. Ensure backend is running on port 8765

### WebSocket Won't Connect

**Problem:** Frontend shows "Disconnected" status

**Solutions:**
1. Verify backend is running: `curl http://127.0.0.1:8765/sessions`
2. Check browser console for WebSocket errors
3. Ensure CORS is configured correctly (should allow localhost:5173)
4. Try refreshing the page

### No Events Showing

**Problem:** Sessions appear but no events in timeline

**Solutions:**
1. Check backend logs for POST requests to `/events`
2. Verify database exists: `ls -la .agent-orchestrator/observability.db`
3. Query database directly:
   ```bash
   sqlite3 .agent-orchestrator/observability.db "SELECT * FROM events;"
   ```
4. Check browser console for errors
5. Try manually triggering a hook (see Testing section)

### Frontend Build Issues

**Problem:** `npm install` fails or `npm run dev` errors

**Solutions:**
1. Ensure Node.js version >= 18: `node --version`
2. Clear npm cache: `npm cache clean --force`
3. Delete `node_modules` and reinstall:
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

### Docker Issues

**Problem:** Containers won't start or can't connect

**Solutions:**
1. Check container status: `docker-compose ps`
2. View logs: `docker-compose logs backend` or `docker-compose logs frontend`
3. Rebuild containers: `docker-compose up -d --build`
4. Check port conflicts: `lsof -i :8765` or `lsof -i :5173`
5. Remove and recreate: `docker-compose down -v && docker-compose up -d`

**Problem:** Database not persisting

**Solution:** Check the volume exists: `docker volume ls | grep observability`

## File Structure

```
agent-orchestrator-observability/
├── README.md                    # This file
├── PLAN.md                      # Detailed MVP plan
├── pyproject.toml               # Python dependencies
├── docker-compose.yml           # Docker orchestration
├── .dockerignore                # Docker ignore patterns
├── backend/
│   ├── main.py                  # FastAPI application
│   ├── database.py              # SQLite operations
│   └── models.py                # Pydantic models
├── hooks/
│   ├── session_start_hook.py    # SessionStart hook
│   └── pre_tool_hook.py         # PreToolUse hook
├── docker/
│   ├── backend.Dockerfile       # Backend container image
│   └── frontend.Dockerfile      # Frontend container image
├── docs/
│   ├── hooks.example.json       # Hooks configuration template
│   ├── USAGE.md                 # Complete usage guide
│   ├── HOOKS_SETUP.md           # Setup guide
│   ├── DOCKER.md                # Docker setup guide
│   ├── DATABASE_SCHEMA.md       # Database schema and tables
│   ├── DATA_MODELS.md           # Shared data models
│   ├── BACKEND_API.md           # Backend API (write/update operations)
│   └── FRONTEND_API.md          # Frontend API (read operations)
└── frontend/
    ├── package.json             # Node dependencies
    ├── vite.config.ts           # Vite configuration
    ├── tsconfig.json            # TypeScript config
    ├── index.html               # HTML entry
    └── src/
        ├── main.tsx             # React entry point
        ├── App.tsx              # Main component
        └── styles.css           # Styles
```

## Development

### Adding New Event Types

1. Update `models.py` to include new event type
2. Create new hook script in `hooks/`
3. Add hook to `.claude/settings.json`
4. Update frontend to display new event type in `App.tsx`

## Documentation

- **`docs/USAGE.md`** - Complete usage guide (framework integration and standalone modes)
- **`docs/HOOKS_SETUP.md`** - Hooks configuration guide
- **`docs/DOCKER.md`** - Docker setup and commands
- **`docs/DATABASE_SCHEMA.md`** - Database schema and table definitions
- **`docs/DATA_MODELS.md`** - Shared data models (Event, Session)
- **`docs/BACKEND_API.md`** - Backend API for writing/updating data (hooks, Python commands)
- **`docs/FRONTEND_API.md`** - Frontend API for reading data (WebSocket + REST)

