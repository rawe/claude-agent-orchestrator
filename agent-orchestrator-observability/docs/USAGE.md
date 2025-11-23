# Usage Guide

This document explains how to use the Agent Orchestrator Observability platform.

## Overview

The observability platform supports **two distinct usage modes**:

1. **Framework Mode (Primary)** - Built-in observability for Agent Orchestrator commands
2. **Standalone Mode (Testing)** - Hook-based observability for any Claude Code session

Choose the mode based on your use case.

---

## Mode 1: Framework Integration (Primary Usage)

### When to Use

Use this mode when:
- Running agents via Agent Orchestrator commands (`ao-new`, `ao-resume`, etc.)
- Managing multiple concurrent agent sessions
- Using agent definitions with specialized system prompts and MCP servers
- Working in production environments

### How It Works

Observability is **built directly into the framework commands**:
- Events are captured programmatically via the Claude Agent SDK hooks system
- Session metadata (agent name, project directory) is automatically tracked
- No hook configuration needed
- Works seamlessly with all framework features

### Setup

**1. Start the observability backend:**

```bash
# Start backend (from agent-orchestrator-observability directory)
uv run backend/main.py
```

Backend runs on `http://127.0.0.1:8765`

**2. Start the frontend:**

```bash
# Start frontend
cd frontend
npm run dev
```

Frontend runs on `http://localhost:5173`

**3. Enable observability in your shell:**

```bash
export AGENT_ORCHESTRATOR_OBSERVABILITY_ENABLED=true
export AGENT_ORCHESTRATOR_OBSERVABILITY_URL=http://127.0.0.1:8765
```

Add these to `~/.zshrc` or `~/.bashrc` to make permanent.

**4. Run your agents normally:**

```bash
cd /path/to/your/project
uv run commands/ao-new my-task -p "Your prompt here"
```

That's it! Observability is automatic.

### What Gets Tracked

When running framework commands with observability enabled, the backend automatically receives:

**Session Metadata:**
- `session_id` - Unique identifier from Claude SDK
- `session_name` - Human-readable name you provide
- `agent_name` - Agent definition name (if using `--agent` flag)
- `project_dir` - Working directory path

**Events:**
- `session_start` - When session begins
- `message` - User prompts and assistant responses
- `pre_tool` - Before each tool execution (with input parameters)
- `post_tool` - After each tool execution (with output and any errors)
- `session_stop` - When session completes

**Session Status:**
- `running` - Session is active
- `finished` - Session completed successfully
- `error` - Session encountered an error

### Example Workflow

```bash
# Enable observability
export AGENT_ORCHESTRATOR_OBSERVABILITY_ENABLED=true

# Create a new session with an agent
cd /path/to/your/project
uv run commands/ao-new researcher --agent research-bot -p "Research AI trends in 2025"

# The dashboard automatically shows:
# - Session: "researcher"
# - Agent: "research-bot" (🤖 icon)
# - Project: /path/to/your/project (📁 icon)
# - All tool calls in real-time

# Resume the session later
uv run commands/ao-resume researcher -p "Now focus on LLM advancements"

# The dashboard continues tracking the same session
```

### Multi-Agent Workflow

Track multiple concurrent agents:

```bash
# Start several specialized agents
uv run commands/ao-new architect --agent system-architect -p "Design the system"
uv run commands/ao-new developer --agent senior-dev -p "Implement the design"
uv run commands/ao-new reviewer --agent security-expert -p "Review for security"

# Dashboard shows all three sessions simultaneously
# Each with its own agent name, project directory, and event timeline
```

### Configuration Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_ORCHESTRATOR_OBSERVABILITY_ENABLED` | `false` | Enable observability integration |
| `AGENT_ORCHESTRATOR_OBSERVABILITY_URL` | `http://127.0.0.1:8765` | Backend URL |

### How Framework Sends Events

The framework integration works at the SDK level:

**In `claude_client.py`:**
1. Sets observability URL globally
2. Registers programmatic hooks when creating `ClaudeAgentOptions`
3. Hooks capture events during session execution
4. Events are sent via HTTP POST to the backend

**Session Metadata Timing:**
- Metadata is sent when `SystemMessage` (subtype='init') is received
- This happens **before** Claude starts processing the task
- Ensures the dashboard has session info immediately

**No Hooks Configuration Needed:**
- Unlike standalone mode, framework mode doesn't use `.claude/settings.json`
- Hooks are registered programmatically in code
- This keeps framework sessions isolated from other Claude Code usage

### Troubleshooting

**Events not appearing:**
1. Check environment variables are set: `echo $AGENT_ORCHESTRATOR_OBSERVABILITY_ENABLED`
2. Verify backend is running: `curl http://127.0.0.1:8765/sessions`
3. Check backend logs for incoming POST requests

**Session metadata missing:**
- Ensure you're using framework commands (`ao-new`, `ao-resume`)
- Metadata is only sent for new sessions, not resumed sessions
- If resuming, metadata is preserved from the original session

---

## Mode 2: Standalone Hooks (Testing/Development)

### When to Use

Use this mode when:
- Testing the observability UI with a single Claude Code instance
- Using Claude Code directly (not via framework commands)
- Debugging hook integrations
- Developing new observability features

### How It Works

Uses Claude Code's hook system:
- Hook scripts are registered in `.claude/settings.json`
- Claude Code runtime calls hooks at specific lifecycle points
- Hook scripts read event data from stdin and POST to backend
- Works with **any** Claude Code session (framework or not)

### Setup

**1. Start backend and frontend** (same as Framework Mode)

**2. Configure hooks:**

**Option A: Using Environment Variable (Recommended)**

```bash
# Set base path
export AGENT_ORCHESTRATOR_OBSERVABILITY_BASE_PATH="$(pwd)"
# Add to ~/.zshrc or ~/.bashrc to make permanent

# Copy example hooks configuration
cp docs/hooks.example.json ../.claude/settings.json
```

**Option B: Using Absolute Paths**

Edit `.claude/settings.json` manually:

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "uv run /ABSOLUTE/PATH/TO/agent-orchestrator-observability/hooks/session_start_hook.py",
        "timeout": 2000
      }]
    }],
    "PreToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "uv run /ABSOLUTE/PATH/TO/agent-orchestrator-observability/hooks/pre_tool_hook.py",
        "timeout": 2000
      }]
    }],
    "PostToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "uv run /ABSOLUTE/PATH/TO/agent-orchestrator-observability/hooks/post_tool_hook.py",
        "timeout": 2000
      }]
    }]
  }
}
```

**3. Run any Claude Code session:**

```bash
# Just use Claude Code normally
# Hooks will automatically fire for all sessions
```

### What Gets Tracked

Hook scripts capture:
- `session_start` - Session begins (SessionStart hook)
- `pre_tool` - Before tool execution (PreToolUse hook)
- `post_tool` - After tool execution (PostToolUse hook)
- Tool inputs and outputs
- Error messages

**Limitations:**
- Session metadata (agent_name, project_dir) is not automatically tracked
- Only captures what the hooks are configured for
- Hooks fire for ALL sessions (can't selectively enable)

### Hook Scripts

**Available hooks:**

```
hooks/
├── session_start_hook.py       # SessionStart hook
├── pre_tool_hook.py           # PreToolUse hook (before tool execution)
├── post_tool_hook.py          # PostToolUse hook (after tool execution)
├── user_prompt_submit_hook.py # UserPromptSubmit hook (user messages)
└── stop_hook.py               # Stop hook (session completion)
```

**How hooks work:**
1. Claude Code calls hook script with JSON on stdin
2. Hook script parses JSON and extracts event data
3. Hook script sends HTTP POST to observability backend
4. Backend stores event in database and broadcasts to WebSocket clients

### Testing Hooks Manually

Test hook scripts directly:

```bash
# Test session_start hook
echo '{"session_id":"test-123"}' | uv run hooks/session_start_hook.py

# Test pre_tool hook
echo '{"session_id":"test-123","tool_name":"Read","tool_input":{"file_path":"/test.py"}}' | uv run hooks/pre_tool_hook.py

# Check backend logs for incoming POST requests
```

### Troubleshooting

**Hooks not firing:**
1. Check absolute paths in `.claude/settings.json`
2. Verify `uv` is in PATH: `which uv`
3. Test hooks manually (see above)
4. Check backend logs for POST requests

**Wrong events captured:**
- Verify you're using the correct hook (PreToolUse vs PostToolUse)
- Check hook matcher patterns in `.claude/settings.json`

---

## Comparison: Framework vs Standalone

| Aspect | Framework Mode | Standalone Mode |
|--------|----------------|-----------------|
| **Primary Use Case** | Production agent orchestration | Testing, development |
| **Configuration** | Environment variables | `.claude/settings.json` hooks |
| **Scope** | Only `ao-*` commands | All Claude Code sessions |
| **Session Metadata** | Automatic (agent, project_dir) | Not captured |
| **Implementation** | Programmatic SDK hooks | CLI hook scripts |
| **Setup Complexity** | Low (just env vars) | Medium (hook configuration) |
| **Agent Awareness** | Yes (from agent definitions) | No |
| **Selective Enabling** | Yes (per shell session) | No (global for all sessions) |

---

## Advanced Topics

### Custom Backend URL

**Framework Mode:**
```bash
export AGENT_ORCHESTRATOR_OBSERVABILITY_URL=http://192.168.1.100:8765
```

**Standalone Mode:**
Edit hook scripts to change the `BACKEND_URL` constant.

### Disabling Observability Temporarily

**Framework Mode:**
```bash
unset AGENT_ORCHESTRATOR_OBSERVABILITY_ENABLED
# Or set to false
export AGENT_ORCHESTRATOR_OBSERVABILITY_ENABLED=false
```

**Standalone Mode:**
Remove or comment out hooks in `.claude/settings.json`.

### Running Backend on Different Port

Edit `backend/main.py`:
```python
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8888)  # Change port here
```

Then update the observability URL in your configuration.

### Docker Deployment

Use Docker Compose for production:

```bash
# Start with Docker
docker-compose up -d

# Backend: http://localhost:8765
# Frontend: http://localhost:5173
```

See `docs/DOCKER.md` for details.

---

## Best Practices

### Framework Mode

**Do:**
- ✅ Set environment variables in your shell config (~/.zshrc)
- ✅ Use descriptive session names for easy identification
- ✅ Leverage agent definitions for specialized agents
- ✅ Monitor the dashboard while agents run for real-time feedback

**Don't:**
- ❌ Mix framework mode with standalone hooks (causes duplicate events)
- ❌ Use session names with special characters (stick to alphanumeric + dash/underscore)

### Standalone Mode

**Do:**
- ✅ Use absolute paths in hook configuration
- ✅ Test hooks manually before relying on them
- ✅ Keep hook scripts simple and fast (2 second timeout)

**Don't:**
- ❌ Use for production (framework mode is more reliable)
- ❌ Add complex logic to hook scripts (keep them as thin wrappers)

---

## Related Documentation

- **`HOOKS_SETUP.md`** - Step-by-step hook configuration guide
- **`DATABASE_SCHEMA.md`** - Database schema and tables
- **`BACKEND_API.md`** - Backend HTTP API reference
- **`FRONTEND_API.md`** - Frontend WebSocket and REST API

---

## Getting Help

**Common Issues:**

1. **No events appearing** → Check backend is running and environment variables are set
2. **Session metadata missing** → Ensure using framework mode (not standalone hooks)
3. **Duplicate events** → Don't enable both framework mode and standalone hooks simultaneously

**Still stuck?**
- Check backend logs for errors: `uv run backend/main.py`
- Verify database exists: `ls -la .agent-orchestrator/observability.db`
- Test manually: `curl http://127.0.0.1:8765/sessions`
