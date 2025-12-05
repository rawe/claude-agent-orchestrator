# Environment Variables Reference

## Overview

The Agent Orchestrator Skill uses environment variables to configure the project directory, logging, and observability integration. Session and agent management is handled via the Agent Runtime API (which also includes agent blueprint management).

**Configuration Precedence:** CLI Flags > Environment Variables > Defaults

## Quick Reference

| Variable | Default | Type | Description |
|----------|---------|------|-------------|
| `AGENT_ORCHESTRATOR_API_URL` | `http://127.0.0.1:8765` | URL | Agent Orchestrator API endpoint (sessions + blueprints) |
| `AGENT_ORCHESTRATOR_PROJECT_DIR` | `$PWD` | Path | Project working directory |
| `AGENT_ORCHESTRATOR_ENABLE_LOGGING` | `false` | Boolean | Enable debug logging |
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

### Logging Configuration

#### `AGENT_ORCHESTRATOR_ENABLE_LOGGING`
**Default:** `false` (disabled)
**Type:** Boolean (`"1"`, `"true"`, `"yes"` = enabled, case-insensitive)
**Purpose:** Enable debug logging for troubleshooting configuration issues.

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
| `--project-dir` | `AGENT_ORCHESTRATOR_PROJECT_DIR` | `ao-start` |

**Note:** The `--project-dir` flag is only available in `ao-start` because it sets the working directory for new Claude sessions. Other commands retrieve session information (including project directory) from the API.

Observability settings (`OBSERVABILITY_ENABLED`, `OBSERVABILITY_URL`) and logging (`ENABLE_LOGGING`) can only be configured via environment variables, not CLI flags.

### Example Usage

```bash
# Override project directory when starting a new session
ao-start mysession --project-dir /path/to/project -p "Build feature"
```

---

## Configuration Resolution Order

1. **CLI Flags** (highest priority) - `--project-dir`
2. **Environment Variables** (medium priority) - `AGENT_ORCHESTRATOR_*`
3. **Defaults** (lowest priority) - `$PWD`

**Example Resolution:**
```bash
# Environment variable set
export AGENT_ORCHESTRATOR_PROJECT_DIR="/home/user/project-a"

# Command with CLI override
ao-start test --project-dir /home/user/project-b -p "Hello"

# Resolution:
# project_dir = /home/user/project-b   (CLI flag wins)
```

---

## Common Patterns

### Pattern 1: Project-Specific with Observability
Enable monitoring for your project.

```bash
# In project directory or .env file
export AGENT_ORCHESTRATOR_OBSERVABILITY_ENABLED="true"
export AGENT_ORCHESTRATOR_OBSERVABILITY_URL="http://localhost:8765"
```

### Pattern 2: Claude Code Local Settings
Configure via `.claude/settings.local.json` for persistence across sessions.

```json
{
  "env": {
    "AGENT_ORCHESTRATOR_PROJECT_DIR": "/Users/username/my-project",
    "AGENT_ORCHESTRATOR_OBSERVABILITY_ENABLED": "true",
    "AGENT_ORCHESTRATOR_OBSERVABILITY_URL": "http://127.0.0.1:8765"
  }
}
```
