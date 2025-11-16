# Hooks Setup Guide

Configure Claude Code hooks to enable observability.

## Setup

### 1. Set Environment Variable

Add to `~/.zshrc` or `~/.bashrc`:

```bash
export AGENT_ORCHESTRATION_OBSERVABILITY_BASE_PATH="/path/to/agent-orchestration-observability"
```

Replace with the absolute path to this folder. Then reload:
```bash
source ~/.zshrc
```

### 2. Configure Hooks

Copy the example configuration to `.claude/settings.json`:

```bash
cp docs/hooks.example.json ../.claude/settings.json
```

Or manually copy the contents from `docs/hooks.example.json` to your `.claude/settings.json`.

### 3. Start Observability

```bash
# Terminal 1 - Backend
uv run backend/main.py

# Terminal 2 - Frontend (in agent-orchestration-observability/frontend)
cd frontend
npm run dev

# Terminal 3 - Your agents (from project root)
cd ..
uv run commands/ao-new my-agent -p "Your task"
```

Open http://localhost:5173 to view your agents in real-time.

---

## Alternative: Absolute Paths

If you don't want to use environment variables, edit `.claude/settings.json` directly:

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "uv run /absolute/path/to/agent-orchestration-observability/hooks/session_start_hook.py",
        "timeout": 2000
      }]
    }],
    "PreToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "uv run /absolute/path/to/agent-orchestration-observability/hooks/pre_tool_hook.py",
        "timeout": 2000
      }]
    }]
  }
}
```

Replace `/absolute/path/to/` with your actual path to the agent-orchestration-observability folder.
