# Agent Runner

The Agent Runner is a standalone process that polls Agent Coordinator for runs and executes them via a configurable executor. It enables callback-driven orchestration by allowing the framework to resume parent sessions when child agents complete.

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) installed
- Agent Coordinator running (default: `http://localhost:8765`)

### Start the Runner

```bash
# From project root
./servers/agent-runner/agent-runner

# Or with explicit coordinator URL
./servers/agent-runner/agent-runner --coordinator-url http://localhost:8765

# Verbose mode for debugging
./servers/agent-runner/agent-runner -v
```

The runner will:
1. Register with Agent Coordinator
2. Start polling for runs
3. Execute runs via the configured executor (default: `executors/claude-code/ao-claude-code-exec`)
4. Report run status back to the Agent Coordinator

### Stop the Runner

Press `Ctrl+C` for graceful shutdown.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_ORCHESTRATOR_API_URL` | `http://localhost:8765` | Agent Coordinator URL |
| `AGENT_EXECUTOR_PATH` | `executors/claude-code/ao-claude-code-exec` | Executor script path (relative to agent-runner dir) |
| `POLL_TIMEOUT` | `30` | Long-poll timeout in seconds |
| `HEARTBEAT_INTERVAL` | `60` | Heartbeat interval in seconds |
| `PROJECT_DIR` | Current directory | Default project directory |

#### Executor Selection

Use `--executor` / `-x` to switch between executors by name:

```bash
# List available executors
./agent-runner --executor-list

# Use Claude SDK executor (default)
./agent-runner -x claude-code

# Use test executor
./agent-runner -x test-executor
```

Or use environment variable with full path:

```bash
AGENT_EXECUTOR_PATH=executors/test-executor/ao-test-exec ./agent-runner
```

### CLI Options

```
--coordinator-url, -c  Agent Coordinator URL (overrides AGENT_ORCHESTRATOR_API_URL)
--executor, -x        Executor name (e.g., 'claude-code', 'test-executor')
--executor-path, -e   Full executor script path (overrides AGENT_EXECUTOR_PATH)
--executor-list, -l   List available executors and exit
--project-dir, -p     Default project directory (overrides PROJECT_DIR)
--verbose, -v         Enable verbose logging
```

Note: `--executor` and `--executor-path` are mutually exclusive.

## Directory Structure

```
servers/agent-runner/
├── agent-runner             # Main runner script (uv script)
├── lib/                     # Shared libraries
│   ├── config.py            # RunnerConfig
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

### Component Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            AGENT RUNNER PROCESS                                  │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │                         MAIN THREAD                                         ││
│  │                                                                             ││
│  │  • Initialization (Auth0 client, config)                                   ││
│  │  • Registration with Coordinator                                           ││
│  │  • Signal handling (SIGINT, SIGTERM)                                       ││
│  │  • Graceful shutdown orchestration                                         ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ HEARTBEAT       │  │ POLLER          │  │ SUPERVISOR      │                  │
│  │ THREAD          │  │ THREAD          │  │ THREAD          │                  │
│  │                 │  │                 │  │                 │                  │
│  │ Sends periodic  │  │ Long-polls for  │  │ Monitors exec   │                  │
│  │ heartbeats to   │  │ pending runs    │  │ subprocesses    │                  │
│  │ keep alive      │  │ from Coord.     │  │ for completion  │                  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘                  │
│           │                    │                    │                           │
│           │ HTTP               │ HTTP               │ HTTP                      │
│           │ (auth)             │ (auth)             │ (auth)                    │
│           ▼                    ▼                    ▼                           │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │                     AUTH0 M2M CLIENT (shared instance)                      ││
│  │                                                                             ││
│  │  • Token caching with auto-refresh                                         ││
│  │  • Single instance shared by ALL components                                ││
│  │  • Prevents duplicate M2M token requests                                   ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                                                                  │
│  ┌─────────────────────────────┐  ┌─────────────────────────────────────────┐   │
│  │ COORDINATOR PROXY           │  │ EMBEDDED MCP SERVER                     │   │
│  │ THREAD                      │  │ THREAD                                  │   │
│  │ (127.0.0.1:<dynamic>)       │  │ (127.0.0.1:<dynamic>)                   │   │
│  │                             │  │                                         │   │
│  │ • HTTP proxy to Coord.      │  │ • FastMCP HTTP server                   │   │
│  │ • Injects auth headers      │  │ • 7 orchestration tools                 │   │
│  │ • Used by executor for      │  │ • Facade to Coordinator API             │   │
│  │   session/agent API calls   │  │ • Used by Claude for child agents       │   │
│  │                             │  │                                         │   │
│  └──────────────┬──────────────┘  └──────────────────┬──────────────────────┘   │
│                 │                                     │                          │
└─────────────────┼─────────────────────────────────────┼──────────────────────────┘
                  │                                     │
                  │ HTTP (adds Bearer token)            │ HTTP (adds Bearer token)
                  │                                     │
                  └──────────────┬──────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   AGENT COORDINATOR     │
                    │       :8765             │
                    │                         │
                    │  • Sessions API         │
                    │  • Runs API             │
                    │  • Agents API           │
                    │  • Runner Registry      │
                    └─────────────────────────┘
```

### Executor Subprocess Spawning

When a run is received, the Runner spawns an executor subprocess:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            AGENT RUNNER PROCESS                                  │
│                                                                                  │
│   POLLER receives run                                                           │
│         │                                                                        │
│         ▼                                                                        │
│   ┌─────────────────────────────────────────────────────────────────┐           │
│   │  RUN EXECUTOR                                                    │           │
│   │                                                                  │           │
│   │  1. Fetch blueprint from Coordinator (via Auth0 client)         │           │
│   │  2. Resolve placeholders:                                        │           │
│   │     • ${AGENT_ORCHESTRATOR_MCP_URL} → http://127.0.0.1:<mcp>    │           │
│   │     • ${AGENT_SESSION_ID} → ses_abc123                          │           │
│   │  3. Build Schema 2.0 JSON payload                                │           │
│   │  4. Spawn executor subprocess                                    │           │
│   └─────────────────────────────────────────────────────────────────┘           │
│         │                                                                        │
│         │ subprocess.Popen()                                                     │
│         │ stdin: JSON payload                                                    │
│         │ env: AGENT_ORCHESTRATOR_API_URL=<proxy_url>                           │
│         │      AGENT_SESSION_ID=ses_abc123                                       │
│         ▼                                                                        │
└─────────┼────────────────────────────────────────────────────────────────────────┘
          │
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        EXECUTOR SUBPROCESS                                       │
│                    (ao-claude-code-exec)                                        │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────┐          │
│  │  Reads JSON from stdin (Schema 2.0):                              │          │
│  │  {                                                                 │          │
│  │    "schema_version": "2.0",                                       │          │
│  │    "mode": "start",                                               │          │
│  │    "session_id": "ses_abc123",                                    │          │
│  │    "prompt": "...",                                               │          │
│  │    "agent_blueprint": {                                           │          │
│  │      "name": "researcher",                                        │          │
│  │      "system_prompt": "...",                                      │          │
│  │      "mcp_servers": {                                             │          │
│  │        "orchestrator": {                                          │          │
│  │          "url": "http://127.0.0.1:54321"  ◄─ resolved             │          │
│  │        }                                                          │          │
│  │      }                                                            │          │
│  │    }                                                              │          │
│  │  }                                                                │          │
│  └───────────────────────────────────────────────────────────────────┘          │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────┐          │
│  │  CLAUDE SDK (Agent)                                               │          │
│  │                                                                   │          │
│  │  • Uses system_prompt from blueprint                              │          │
│  │  • Connects to MCP servers from blueprint                         │          │
│  │  • Can call orchestration tools via embedded MCP server           │          │
│  └────────────────────────────────┬──────────────────────────────────┘          │
│                                   │                                              │
│                                   │ MCP tool calls                              │
│                                   │ (start_agent_session, etc.)                 │
│                                   ▼                                              │
└───────────────────────────────────┼──────────────────────────────────────────────┘
                                    │
                                    │ HTTP POST to embedded MCP server
                                    │
          ┌─────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            AGENT RUNNER PROCESS                                  │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │              EMBEDDED MCP SERVER (127.0.0.1:<mcp_port>)                     ││
│  │                                                                             ││
│  │  Receives: start_agent_session(agent_name="worker", prompt="...")          ││
│  │                                                                             ││
│  │  Tools available:                                                           ││
│  │  • list_agent_blueprints    • get_agent_session_status                     ││
│  │  • list_agent_sessions      • get_agent_session_result                     ││
│  │  • start_agent_session      • delete_all_agent_sessions                    ││
│  │  • resume_agent_session                                                     ││
│  │                                                                             ││
│  │  Forwards to Coordinator API with Auth0 token ──────────────────────────►  ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP (authenticated)
                                    ▼
                    ┌─────────────────────────┐
                    │   AGENT COORDINATOR     │
                    │                         │
                    │  Creates new run for    │
                    │  child agent session    │
                    └─────────────────────────┘
```

### Data Flow Summary

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                DATA FLOW                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  1. REGISTRATION & POLLING                                                       │
│     Runner ──[HTTP+Auth]──► Coordinator                                         │
│                                                                                  │
│  2. RUN ASSIGNMENT                                                               │
│     Coordinator ──[Run JSON]──► Runner (via long-poll response)                 │
│                                                                                  │
│  3. BLUEPRINT RESOLUTION                                                         │
│     Runner ──[GET /agents/{name}]──► Coordinator                                │
│     Runner resolves ${AGENT_ORCHESTRATOR_MCP_URL} → MCP server URL              │
│     Runner resolves ${AGENT_SESSION_ID} → session ID                            │
│                                                                                  │
│  4. EXECUTOR SPAWNING                                                            │
│     Runner ──[stdin JSON]──► Executor subprocess                                │
│     Env: AGENT_ORCHESTRATOR_API_URL=<proxy_url>                                 │
│                                                                                  │
│  5. EXECUTOR → COORDINATOR (via Proxy)                                          │
│     Executor ──[HTTP]──► Proxy ──[HTTP+Auth]──► Coordinator                     │
│     (session binding, event reporting, etc.)                                    │
│                                                                                  │
│  6. CLAUDE → EMBEDDED MCP → COORDINATOR (for child orchestration)              │
│     Claude ──[MCP]──► MCP Server ──[HTTP+Auth]──► Coordinator                   │
│     (start_agent_session, resume_agent_session, etc.)                           │
│                                                                                  │
│  7. STATUS REPORTING                                                             │
│     Supervisor ──[HTTP+Auth]──► Coordinator                                     │
│     (run started, completed, failed, stopped)                                   │
│                                                                                  │
│  8. HEARTBEAT                                                                    │
│     Heartbeat thread ──[HTTP+Auth]──► Coordinator (every 60s)                   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Thread & Process Summary

| Component | Type | Port | Purpose |
|-----------|------|------|---------|
| Main Thread | Thread | - | Init, registration, signal handling |
| Heartbeat | Thread | - | Keep registration alive |
| Poller | Thread | - | Long-poll for runs |
| Supervisor | Thread | - | Monitor executor completion |
| Coordinator Proxy | Thread | dynamic | Auth proxy for executors |
| Embedded MCP Server | Thread | dynamic | Orchestration tools for Claude |
| Executor | Subprocess | - | Runs Claude SDK agent |

### Auth0 Token Sharing

```
                    ┌─────────────────────────────────────────┐
                    │         AUTH0 M2M CLIENT                │
                    │                                         │
                    │  • Created ONCE in Runner.__init__()   │
                    │  • Token cached with expiry             │
                    │  • Auto-refresh before expiry           │
                    │                                         │
                    └──────────────────┬──────────────────────┘
                                       │
           ┌───────────────────────────┼───────────────────────────┐
           │                           │                           │
           ▼                           ▼                           ▼
    ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
    │ API Client   │          │ Coord Proxy  │          │ MCP Server   │
    │              │          │              │          │              │
    │ (polling,    │          │ (forwards    │          │ (orchestr.   │
    │  heartbeat,  │          │  executor    │          │  tools)      │
    │  status)     │          │  requests)   │          │              │
    └──────────────┘          └──────────────┘          └──────────────┘
           │                           │                           │
           │                           │                           │
           └───────────────────────────┴───────────────────────────┘
                                       │
                                       │ All use SAME token
                                       │ (no duplicate M2M requests)
                                       ▼
                        ┌─────────────────────────┐
                        │   AGENT COORDINATOR     │
                        └─────────────────────────┘
```

## Run Types

Runs are passed to the executor as JSON via stdin (Schema 2.0):

| Type | Mode | Parameters |
|------|------|------------|
| `start_session` | `start` | `session_id`, `prompt`, `project_dir`, `agent_blueprint` |
| `resume_session` | `resume` | `session_id`, `prompt`, `agent_blueprint` |

**Schema 2.0 Notes:**
- `agent_blueprint`: Fully resolved blueprint with placeholders replaced. The Runner fetches the blueprint from the Coordinator and resolves placeholders like `${AGENT_ORCHESTRATOR_MCP_URL}` and `${AGENT_SESSION_ID}` before spawning the executor.
- Executor uses `agent_blueprint` directly without making Coordinator API calls.

## How It Works

1. **Registration**: On startup, runner registers with Agent Coordinator and receives a unique `runner_id`
2. **Polling**: Poll thread continuously long-polls for pending runs
3. **Execution**: When a run arrives, executor spawns appropriate subprocess with environment variables
4. **Monitoring**: Supervisor thread monitors subprocess completion and reports status
5. **Heartbeat**: Background thread sends periodic heartbeats to keep registration alive

## Callback Flow

The runner enables callback-driven orchestration:

```
1. Dashboard creates run → Agent Coordinator queues it
2. Runner picks up run → Spawns executor with mode=start (sets AGENT_SESSION_NAME)
3. Orchestrator runs → Spawns child agents with callback=true
4. Child completes → Coordinator creates resume run
5. Runner picks up resume run → Spawns executor with mode=resume
6. Orchestrator continues with callback notification
```

## Logs

The runner logs to stdout:

```
2025-01-15 10:00:00 [INFO] agent-runner: Connecting to Agent Coordinator at http://localhost:8765
2025-01-15 10:00:00 [INFO] agent-runner: Registered as lnch_abc123
2025-01-15 10:00:00 [INFO] agent-runner: Runner started - waiting for runs
2025-01-15 10:00:05 [INFO] poller: Received run run_xyz789 (start_session)
2025-01-15 10:00:05 [INFO] executor: Starting session my-agent with agent researcher
```

Use `-v` for debug-level logs.

## Troubleshooting

### Runner won't connect

- Ensure Agent Coordinator is running: `curl http://localhost:8765/health`
- Check the Agent Coordinator URL is correct

### Runs not being picked up

- Verify runner is registered (check logs for `Registered as lnch_...`)
- Check Agent Coordinator logs for run queue status

### Subprocess failures

- Check that the executor script exists at `AGENT_EXECUTOR_PATH`
- Verify `PROJECT_DIR` points to a valid directory
- Use `-v` flag for detailed subprocess output

## Related Documentation

- [Agent Callback Architecture](../../docs/features/agent-callback-architecture.md)
- [Work Package 2: Agent Runner Process](../../docs/features/02-agent-runner-process.md)
