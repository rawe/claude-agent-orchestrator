# Usage Guide

How to use the Agent Runtime with the Agent Orchestrator framework.

## Quick Start

**1. Start the Agent Runtime server:**

```bash
cd servers/agent-runtime
uv run main.py
```

Server runs on `http://127.0.0.1:8765`

**2. Start the Dashboard:**

```bash
cd dashboard
npm run dev
```

Dashboard runs on `http://localhost:3000`

**3. Run agents:**

```bash
uv run plugins/orchestrator/commands/ao-new my-session -p "Your prompt"
```

The commands automatically connect to the Agent Runtime at the default URL.

## What Gets Tracked

**Session Metadata:**
- `session_id` - Unique identifier from Claude SDK
- `session_name` - Human-readable name
- `agent_name` - Agent blueprint name (if using `--agent`)
- `project_dir` - Working directory

**Events:**
- `session_start` - Session begins
- `message` - User/assistant messages
- `pre_tool` / `post_tool` - Tool execution
- `session_stop` - Session ends

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_ORCHESTRATOR_SESSION_MANAGER_URL` | `http://127.0.0.1:8765` | Agent Runtime URL |
| `DEBUG_LOGGING` | `false` | Enable debug logging (server) |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Allowed CORS origins |

## Troubleshooting

**Events not appearing:**
1. Verify server: `curl http://127.0.0.1:8765/sessions`
2. Check server logs for errors
3. Ensure dashboard WebSocket is connected
