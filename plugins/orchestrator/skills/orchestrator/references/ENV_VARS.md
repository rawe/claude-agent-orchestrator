# Environment Variables Reference

## Overview

The Agent Orchestrator Skill uses environment variables to configure directory paths, logging, and observability integration. These variables control where agent blueprints, sessions, and logs are stored, and how sessions interact with monitoring systems.

**Configuration Precedence:** CLI Flags > Environment Variables > Defaults

## Quick Reference

| Variable | Default | Type | Description |
|----------|---------|------|-------------|
| `AGENT_ORCHESTRATOR_PROJECT_DIR` | `$PWD` | Path | Project working directory |
| `AGENT_ORCHESTRATOR_SESSIONS_DIR` | `{project_dir}/.agent-orchestrator/agent-sessions` | Path | Session storage directory |
| `AGENT_ORCHESTRATOR_AGENTS_DIR` | `{project_dir}/.agent-orchestrator/agents` | Path | Agent blueprints directory |
| `AGENT_ORCHESTRATOR_ENABLE_LOGGING` | `false` | Boolean | Enable session logging |
| `AGENT_ORCHESTRATOR_OBSERVABILITY_ENABLED` | `true` | Boolean | Enable observability events |
| `AGENT_ORCHESTRATOR_OBSERVABILITY_URL` | `http://127.0.0.1:8765` | URL | Observability backend endpoint |

## Detailed Descriptions

### Directory Configuration

#### `AGENT_ORCHESTRATOR_PROJECT_DIR`
**Default:** Current working directory (`$PWD`)
**Type:** Absolute or relative path
**Purpose:** Sets the working directory where agent sessions execute. All commands run by Claude during the session inherit this as their current working directory.

**Validation:** Must exist, must be a directory, must be readable.

**Example:**
```bash
export AGENT_ORCHESTRATOR_PROJECT_DIR="/Users/username/my-project"
```

---

#### `AGENT_ORCHESTRATOR_SESSIONS_DIR`
**Default:** `{project_dir}/.agent-orchestrator/agent-sessions`
**Type:** Absolute or relative path
**Purpose:** Directory for storing session files (.jsonl) and metadata (.meta.json). Sessions can be resumed by reading these files. Centralize sessions across projects by setting this to a fixed path.

**Validation:** Parent directory must be writable (auto-creates if missing).

**Example:**
```bash
# Store all sessions in a central location
export AGENT_ORCHESTRATOR_SESSIONS_DIR="/Users/username/.agent-sessions"
```

---

#### `AGENT_ORCHESTRATOR_AGENTS_DIR`
**Default:** `{project_dir}/.agent-orchestrator/agents`
**Type:** Absolute or relative path
**Purpose:** Directory containing agent blueprint files (agent.json, agent.system-prompt.md, agent.mcp.json). Use this to share agent configurations across multiple projects.

**Validation:** Parent directory must be writable (auto-creates if missing).

**Example:**
```bash
# Share agent blueprints across projects
export AGENT_ORCHESTRATOR_AGENTS_DIR="/Users/username/.shared-agents"
```

---

### Logging Configuration

#### `AGENT_ORCHESTRATOR_ENABLE_LOGGING`
**Default:** `false` (disabled)
**Type:** Boolean (`"1"`, `"true"`, `"yes"` = enabled, case-insensitive)
**Purpose:** Enable detailed logging of session commands, prompts, and results to `.log` files in the sessions directory.

**Log Location:** `{sessions_dir}/{session_name}.log`
**Log Contents:** Command invocations, full prompts, environment variables, timestamps, results.

**Example:**
```bash
# Enable logging
export AGENT_ORCHESTRATOR_ENABLE_LOGGING="true"
```

---

### Observability Configuration

#### `AGENT_ORCHESTRATOR_OBSERVABILITY_ENABLED`
**Default:** `true` (enabled)
**Type:** Boolean (`"0"`, `"false"`, `"no"` = disabled, case-insensitive)
**Purpose:** Enable real-time event streaming to an observability backend. Captures session lifecycle events, tool calls, and assistant messages for monitoring and analysis.

**Events Tracked:**
- `session_start` - Session initialization
- `message` - User prompts and assistant responses
- `pre_tool` - Before tool execution
- `post_tool` - After tool execution (includes errors)
- `session_stop` - Session completion

**Example:**
```bash
# Disable observability
export AGENT_ORCHESTRATOR_OBSERVABILITY_ENABLED="false"
```

---

#### `AGENT_ORCHESTRATOR_OBSERVABILITY_URL`
**Default:** `http://127.0.0.1:8765`
**Type:** URL (HTTP endpoint)
**Purpose:** Base URL of the observability backend service. Events are sent to `{url}/events` via HTTP POST.

**Requirements:**
- Must be accessible from where skill commands run
- Must accept JSON POST requests to `/events` endpoint
- Failures are silent (won't block session execution)

**Example:**
```bash
# Use custom observability backend
export AGENT_ORCHESTRATOR_OBSERVABILITY_URL="http://localhost:9000"
```

---

## CLI Flag Overrides

The following CLI flags override environment variables when specified:

| CLI Flag | Overrides | Available In |
|----------|-----------|--------------|
| `--project-dir` | `AGENT_ORCHESTRATOR_PROJECT_DIR` | `ao-start`, `ao-resume`, `ao-show-config`, `ao-status`, `ao-delete-all` |
| `--sessions-dir` | `AGENT_ORCHESTRATOR_SESSIONS_DIR` | `ao-start`, `ao-resume`, `ao-show-config`, `ao-list-sessions`, `ao-status`, `ao-get-result`, `ao-delete-all` |
| `--agents-dir` | `AGENT_ORCHESTRATOR_AGENTS_DIR` | `ao-start`, `ao-resume`, `ao-list-blueprints` |

**Note:** Observability settings (`OBSERVABILITY_ENABLED`, `OBSERVABILITY_URL`) and logging (`ENABLE_LOGGING`) can only be configured via environment variables, not CLI flags.

### Example Usage

```bash
# Override project directory for a single command
ao-start mysession --project-dir /path/to/project -p "Build feature"

# Override sessions directory to use centralized storage
ao-list-sessions --sessions-dir /Users/username/.agent-sessions

# Override agents directory to use shared agent blueprints
ao-start research --agent web-researcher --agents-dir /shared/agents
```

---

## Configuration Resolution Order

1. **CLI Flags** (highest priority) - `--project-dir`, `--sessions-dir`, `--agents-dir`
2. **Environment Variables** (medium priority) - `AGENT_ORCHESTRATOR_*`
3. **Defaults** (lowest priority) - `$PWD` or `{project}/.agent-orchestrator/*`

**Example Resolution:**
```bash
# Environment variables set
export AGENT_ORCHESTRATOR_PROJECT_DIR="/home/user/project-a"
export AGENT_ORCHESTRATOR_SESSIONS_DIR="/home/user/.sessions"

# Command with CLI override
ao-start test --project-dir /home/user/project-b -p "Hello"

# Resolution:
# project_dir  = /home/user/project-b   (CLI flag wins)
# sessions_dir = /home/user/.sessions   (from env var)
# agents_dir   = /home/user/project-b/.agent-orchestrator/agents (default)
```

---

## Common Patterns

### Pattern 1: Centralized Sessions and Agents
Useful for maintaining all agent work in a dedicated location, regardless of which project you're working in.

```bash
# In ~/.bashrc or ~/.zshrc
export AGENT_ORCHESTRATOR_SESSIONS_DIR="$HOME/.agent-orchestrator/sessions"
export AGENT_ORCHESTRATOR_AGENTS_DIR="$HOME/.agent-orchestrator/agents"
export AGENT_ORCHESTRATOR_ENABLE_LOGGING="true"
```

### Pattern 2: Project-Specific with Observability
Keep sessions and agents per-project but enable monitoring.

```bash
# In project directory or .env file
export AGENT_ORCHESTRATOR_OBSERVABILITY_ENABLED="true"
export AGENT_ORCHESTRATOR_OBSERVABILITY_URL="http://localhost:8765"

# Sessions go to ./.agent-orchestrator/agent-sessions (default)
# Agents go to ./.agent-orchestrator/agents (default)
```

### Pattern 3: Claude Code Local Settings
Configure via `.claude/settings.local.json` for persistence across sessions.

```json
{
  "env": {
    "AGENT_ORCHESTRATOR_SESSIONS_DIR": "/Users/username/projects/ai/orchestrator/.agent-orchestrator/agent-sessions",
    "AGENT_ORCHESTRATOR_AGENTS_DIR": "/Users/username/projects/ai/orchestrator/.agent-orchestrator/agents",
    "AGENT_ORCHESTRATOR_OBSERVABILITY_ENABLED": "true",
    "AGENT_ORCHESTRATOR_OBSERVABILITY_URL": "http://127.0.0.1:8765"
  }
}
```
