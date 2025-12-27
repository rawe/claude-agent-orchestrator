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

## Creating a New Executor

### 1. Create the folder

```bash
mkdir executors/my-executor
```

### 2. Create the executable

The executable must:
- Be named `ao-*-exec` (the runner scans for this pattern)
- Be executable (`chmod +x`)
- Read JSON payload from stdin
- Follow the invocation schema (see below)

```bash
touch executors/my-executor/ao-my-executor-exec
chmod +x executors/my-executor/ao-my-executor-exec
```

### 3. Implement the invocation schema

The executor receives a JSON payload via stdin (Schema 2.0):

```json
{
  "schema_version": "2.0",
  "mode": "start" | "resume",
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
  "metadata": {}
}
```

**Schema 2.0:**
- `agent_blueprint`: Fully resolved blueprint with placeholders replaced (Runner handles resolution)
- Runner fetches blueprint from Coordinator and resolves placeholders before spawning executor

### 4. Use shared libraries

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
from executor_config import get_api_url
```

### 5. Register with runner

No registration needed. The runner auto-discovers executors by scanning this directory.

```bash
# List available executors
./agent-runner --executor-list

# Use your executor
./agent-runner --executor my-executor
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

    if inv.mode == "start":
        # Handle new session
        print(f"Starting session: {inv.session_name}")
    else:
        # Handle resume
        print(f"Resuming session: {inv.session_name}")

if __name__ == "__main__":
    main()
```

## Existing Executors

| Name | Description |
|------|-------------|
| `claude-code` | Claude SDK executor (default) |
| `test-executor` | Simple echo executor for testing |