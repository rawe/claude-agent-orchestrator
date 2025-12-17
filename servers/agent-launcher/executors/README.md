# Executors

This directory contains executor implementations that handle run execution for the Agent Launcher.

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
- Be named `ao-*-exec` (the launcher scans for this pattern)
- Be executable (`chmod +x`)
- Read JSON payload from stdin
- Follow the invocation schema (see below)

```bash
touch executors/my-executor/ao-my-executor-exec
chmod +x executors/my-executor/ao-my-executor-exec
```

### 3. Implement the invocation schema

The executor receives a JSON payload via stdin:

```json
{
  "schema_version": "1.0",
  "mode": "start" | "resume",
  "session_name": "unique-session-name",
  "prompt": "User input text",
  "agent_name": "optional-agent-blueprint",
  "project_dir": "/path/to/project",
  "metadata": {}
}
```

### 4. Use shared libraries

Executors can import shared libraries from `agent-launcher/lib/`:

```python
import sys
from pathlib import Path

# Add launcher lib to path
launcher_lib = Path(__file__).parent.parent.parent / "lib"
sys.path.insert(0, str(launcher_lib))

# Now import shared modules
from invocation import ExecutorInvocation
from session_client import SessionClient
from executor_config import get_api_url
```

### 5. Register with launcher

No registration needed. The launcher auto-discovers executors by scanning this directory.

```bash
# List available executors
./agent-launcher --executor-list

# Use your executor
./agent-launcher --executor my-executor
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

# Add launcher lib
launcher_lib = Path(__file__).parent.parent.parent / "lib"
sys.path.insert(0, str(launcher_lib))

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