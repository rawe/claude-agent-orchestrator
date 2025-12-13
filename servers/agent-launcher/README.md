# Agent Launcher

The Agent Launcher is a standalone process that polls Agent Runtime for jobs and executes them via a configurable executor. It enables callback-driven orchestration by allowing the framework to resume parent sessions when child agents complete.

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) installed
- Agent Runtime running (default: `http://localhost:8765`)

### Start the Launcher

```bash
# From project root
./servers/agent-launcher/agent-launcher

# Or with explicit runtime URL
./servers/agent-launcher/agent-launcher --runtime-url http://localhost:8765

# Verbose mode for debugging
./servers/agent-launcher/agent-launcher -v
```

The launcher will:
1. Register with Agent Runtime
2. Start polling for jobs
3. Execute jobs via the configured executor (default: `executors/claude-code/ao-claude-code-exec`)
4. Report job status back to the runtime

### Stop the Launcher

Press `Ctrl+C` for graceful shutdown.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_ORCHESTRATOR_API_URL` | `http://localhost:8765` | Agent Runtime URL |
| `AGENT_EXECUTOR_PATH` | `executors/claude-code/ao-claude-code-exec` | Executor script path (relative to agent-launcher dir) |
| `POLL_TIMEOUT` | `30` | Long-poll timeout in seconds |
| `HEARTBEAT_INTERVAL` | `60` | Heartbeat interval in seconds |
| `PROJECT_DIR` | Current directory | Default project directory |

#### Executor Selection

Use `--executor` / `-x` to switch between executors by name:

```bash
# List available executors
./agent-launcher --executor-list

# Use Claude SDK executor (default)
./agent-launcher -x claude-code

# Use test executor
./agent-launcher -x test-executor
```

Or use environment variable with full path:

```bash
AGENT_EXECUTOR_PATH=executors/test-executor/ao-test-exec ./agent-launcher
```

### CLI Options

```
--runtime-url, -r     Agent Runtime URL (overrides AGENT_ORCHESTRATOR_API_URL)
--executor, -x        Executor name (e.g., 'claude-code', 'test-executor')
--executor-path, -e   Full executor script path (overrides AGENT_EXECUTOR_PATH)
--executor-list, -l   List available executors and exit
--project-dir, -p     Default project directory (overrides PROJECT_DIR)
--verbose, -v         Enable verbose logging
```

Note: `--executor` and `--executor-path` are mutually exclusive.

## Directory Structure

```
servers/agent-launcher/
├── agent-launcher           # Main launcher script (uv script)
├── lib/                     # Shared libraries
│   ├── config.py            # LauncherConfig
│   ├── executor_config.py   # Executor Config (for ao-*-exec scripts)
│   ├── invocation.py        # JSON payload schema
│   ├── session_client.py    # Session API client
│   ├── agent_api.py         # Agent blueprints API client
│   └── ...
├── executors/               # Executor implementations
│   ├── claude-code/         # Claude SDK executor
│   │   ├── ao-claude-code-exec
│   │   └── lib/claude_client.py
│   └── test-executor/       # Test/dummy executor
│       └── ao-test-exec
└── tests/                   # Unit tests
```

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Agent Launcher                          │
├────────────────────────────────────────────────────────────┤
│  Poll Thread      │ Long-polls /launcher/jobs endpoint    │
│  Supervisor       │ Monitors subprocess completion        │
│  Heartbeat        │ Sends periodic heartbeats             │
│  Registry         │ Tracks running jobs (thread-safe)     │
└────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP
                              ▼
                    ┌─────────────────┐
                    │  Agent Runtime  │
                    │    :8765        │
                    └─────────────────┘
```

## Job Types

Jobs are passed to the executor as JSON via stdin:

| Type | Mode | Parameters |
|------|------|------------|
| `start_session` | `start` | `session_name`, `agent_name`, `prompt`, `project_dir` |
| `resume_session` | `resume` | `session_name`, `prompt` |

## How It Works

1. **Registration**: On startup, launcher registers with Agent Runtime and receives a unique `launcher_id`
2. **Polling**: Poll thread continuously long-polls for pending jobs
3. **Execution**: When a job arrives, executor spawns appropriate subprocess with environment variables
4. **Monitoring**: Supervisor thread monitors subprocess completion and reports status
5. **Heartbeat**: Background thread sends periodic heartbeats to keep registration alive

## Callback Flow

The launcher enables callback-driven orchestration:

```
1. Dashboard creates job → Agent Runtime queues it
2. Launcher picks up job → Spawns executor with mode=start (sets AGENT_SESSION_NAME)
3. Orchestrator runs → Spawns child agents with callback=true
4. Child completes → Runtime creates resume job
5. Launcher picks up resume job → Spawns executor with mode=resume
6. Orchestrator continues with callback notification
```

## Logs

The launcher logs to stdout:

```
2025-01-15 10:00:00 [INFO] agent-launcher: Connecting to Agent Runtime at http://localhost:8765
2025-01-15 10:00:00 [INFO] agent-launcher: Registered as lnch_abc123
2025-01-15 10:00:00 [INFO] agent-launcher: Launcher started - waiting for jobs
2025-01-15 10:00:05 [INFO] poller: Received job job_xyz789 (start_session)
2025-01-15 10:00:05 [INFO] executor: Starting session my-agent with agent researcher
```

Use `-v` for debug-level logs.

## Troubleshooting

### Launcher won't connect

- Ensure Agent Runtime is running: `curl http://localhost:8765/health`
- Check the runtime URL is correct

### Jobs not being picked up

- Verify launcher is registered (check logs for `Registered as lnch_...`)
- Check Agent Runtime logs for job queue status

### Subprocess failures

- Check that the executor script exists at `AGENT_EXECUTOR_PATH`
- Verify `PROJECT_DIR` points to a valid directory
- Use `-v` flag for detailed subprocess output

## Related Documentation

- [Agent Callback Architecture](../../docs/features/agent-callback-architecture.md)
- [Work Package 2: Agent Launcher Process](../../docs/features/02-agent-launcher-process.md)
