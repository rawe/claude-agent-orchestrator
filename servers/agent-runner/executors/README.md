# Executors

This directory contains executor implementations that handle run execution for the Agent Runner.

## Directory Structure

Each executor lives in its own folder with a specific naming pattern:

```
executors/
├── <executor-name>/
│   ├── ao-<executor-name>-exec    # Main executable (required)
│   └── lib/                       # Optional executor-specific libraries
└── ...
```

## Executor Profiles

Executors are configured via **profiles** (see [Executor Profiles](../../../docs/features/executor-profiles.md)). A profile specifies:

- Which executor to run (`command`)
- Executor-specific configuration (`config`)

```json
// profiles/coding.json
{
  "type": "claude-code",
  "command": "executors/claude-code/ao-claude-code-exec",
  "config": {
    "permission_mode": "bypassPermissions",
    "model": "opus"
  }
}
```

The runner passes `config` to the executor via the `executor_config` field in the invocation payload.

## Creating a New Executor

### 1. Create the folder

```bash
mkdir executors/my-executor
```

### 2. Create the executable

The executable must:
- Be named `ao-*-exec`
- Be executable (`chmod +x`)
- Read JSON payload from stdin
- Follow the invocation schema (see below)

```bash
touch executors/my-executor/ao-my-executor-exec
chmod +x executors/my-executor/ao-my-executor-exec
```

### 3. Implement the invocation schema

The executor receives a JSON payload via stdin (Schema 2.1):

```json
{
  "schema_version": "2.1",
  "mode": "start",
  "session_id": "ses_abc123",
  "prompt": "User input text",
  "project_dir": "/path/to/project",
  "agent_blueprint": {
    "name": "worker-agent",
    "system_prompt": "You are a worker agent...",
    "mcp_servers": {
      "orchestrator": {
        "type": "http",
        "url": "http://127.0.0.1:54321",
        "headers": {
          "X-Agent-Session-Id": "ses_abc123"
        }
      }
    }
  },
  "executor_config": {
    "permission_mode": "bypassPermissions",
    "model": "opus"
  },
  "metadata": {}
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `schema_version` | Yes | Must be `"2.1"` |
| `mode` | Yes | `"start"` or `"resume"` |
| `session_id` | Yes | Coordinator-generated session identifier |
| `prompt` | Yes | User input text |
| `project_dir` | No | Working directory (start mode only) |
| `agent_blueprint` | No | Fully resolved blueprint with placeholders replaced |
| `executor_config` | No | Executor-specific configuration from profile |
| `metadata` | No | Extensible key-value map |

**Schema 2.1 changes:**
- `executor_config`: Configuration from the executor profile (e.g., permission mode, model)
- Runner fetches blueprint and resolves placeholders before spawning executor

### 4. Handle executor_config

Executors should read `executor_config` and apply settings with fallbacks:

```python
def get_config(invocation: ExecutorInvocation) -> dict:
    config = invocation.executor_config or {}
    return {
        "permission_mode": config.get("permission_mode", "bypassPermissions"),
        "model": config.get("model"),  # None = use default
    }
```

Unknown config keys should be ignored (forward compatibility).

### 5. Use shared libraries

Executors can import shared libraries from `agent-runner/lib/`:

```python
import sys
from pathlib import Path

# Add runner lib to path
runner_lib = Path(__file__).parent.parent.parent / "lib"
sys.path.insert(0, str(runner_lib))

# Now import shared modules
from invocation import ExecutorInvocation
from session_client import SessionClient
```

### 6. Create a profile

Create a profile that references your executor:

```json
// profiles/my-profile.json
{
  "type": "my-executor",
  "command": "executors/my-executor/ao-my-executor-exec",
  "config": {
    "some_setting": "value"
  }
}
```

### 7. Run with the profile

```bash
# List available profiles
./agent-runner --profile-list

# Use your profile
./agent-runner --profile my-profile
```

## Example: Minimal Executor

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///

import sys
from pathlib import Path

# Add runner lib
runner_lib = Path(__file__).parent.parent.parent / "lib"
sys.path.insert(0, str(runner_lib))

from invocation import ExecutorInvocation

def main():
    # Parse stdin JSON
    inv = ExecutorInvocation.from_stdin()

    # Read executor config (from profile)
    config = inv.executor_config or {}
    permission_mode = config.get("permission_mode", "default")

    if inv.mode == "start":
        print(f"Starting session: {inv.session_id}")
        print(f"Permission mode: {permission_mode}")
    else:
        print(f"Resuming session: {inv.session_id}")

if __name__ == "__main__":
    main()
```

## Existing Executors

| Name | Description |
|------|-------------|
| `claude-code` | Claude Agent SDK executor (default) |
| `test-executor` | Simple echo executor for testing |

## Default Behavior

When the runner starts without a `--profile` flag:
- Uses the default executor: `executors/claude-code/ao-claude-code-exec`
- No `executor_config` is passed (executor uses internal defaults)
- Registers with coordinator as `executor_profile: "claude-code"`

This ensures backward compatibility with existing deployments.