# Agent Runner

The Agent Runner is a standalone process that polls Agent Coordinator for runs and executes them via a configurable executor. It enables callback-driven orchestration by allowing the framework to resume parent sessions when child agents complete.

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) installed
- Agent Coordinator running (default: `http://localhost:8765`)

### Start the Runner

```bash
# From project root (uses default executor)
./servers/agent-runner/agent-runner

# With an executor profile
./servers/agent-runner/agent-runner --profile coding

# List available profiles
./servers/agent-runner/agent-runner --profile-list

# Verbose mode for debugging
./servers/agent-runner/agent-runner -v
```

The runner will:
1. Register with Agent Coordinator (with profile info)
2. Start polling for runs
3. Execute runs via the configured executor
4. Report run status back to the Agent Coordinator

### Stop the Runner

Press `Ctrl+C` for graceful shutdown.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_ORCHESTRATOR_API_URL` | `http://localhost:8765` | Agent Coordinator URL |
| `POLL_TIMEOUT` | `30` | Long-poll timeout in seconds |
| `HEARTBEAT_INTERVAL` | `60` | Heartbeat interval in seconds |
| `PROJECT_DIR` | Current directory | Default project directory |

### Executor Profiles

Profiles define executor configuration (permission mode, model, settings). Located in `profiles/`.

See [Profiles Documentation](profiles/PROFILES.md) for the naming convention and available profiles.

```bash
# List available profiles
./agent-runner --profile-list

# Start with a profile
./agent-runner --profile full-access-project-best
```

**Profile schema**:
```json
{
  "type": "string",           // Executor type (e.g., "claude-code", "procedural")
  "command": "string",        // Path to executor script (relative to agent-runner dir)
  "config": {},               // Executor-specific configuration
  "agents_dir": "string"      // Optional: Path to agent definitions directory
}
```

**Example** (`profiles/full-access-project-best.json`):
```json
{
  "type": "claude-code",
  "command": "executors/claude-code/ao-claude-code-exec",
  "config": {
    "permission_mode": "bypassPermissions",
    "setting_sources": ["project", "local"],
    "model": "opus"
  }
}
```

Without `--profile`, the runner uses the default executor with no config.

### Runner-Owned Agents

Profiles can specify an `agents_dir` to load agent definitions that are bundled with the runner. These agents are registered with the Agent Coordinator when the runner starts and removed when the runner stops.

**Example** (`profiles/echo.json`):
```json
{
  "type": "procedural",
  "command": "executors/procedural-executor/ao-procedural-exec",
  "agents_dir": "executors/procedural-executor/scripts/echo/agents",
  "config": {}
}
```

Agent definitions are JSON files in the `agents_dir`:
```json
{
  "name": "echo",
  "description": "Simple echo agent that returns the input message",
  "command": "scripts/echo/echo",
  "parameters_schema": {
    "type": "object",
    "required": ["message"],
    "properties": {
      "message": { "type": "string" }
    }
  }
}
```

Runner-owned agents:
- Are registered with the coordinator on runner startup
- Appear in `/agents` endpoint with `type: "procedural"` and `runner_id` set
- Are automatically removed when the runner deregisters
- Cannot be edited via the dashboard (read-only)

### CLI Options

```
--coordinator-url, -c      Agent Coordinator URL
--profile, -x              Executor profile name (loads profiles/<name>.json)
--profile-list, -l         List available profiles and exit
--require-matching-tags    Only accept runs with at least one matching tag
--project-dir, -p          Default project directory
--tags, -t                 Comma-separated capability tags
--mcp-port, -m             Port for embedded MCP server (fixed port)
--external-mcp-url, -e     External MCP server URL (disables embedded MCP server)
--verbose, -v              Enable verbose logging
```

### Shared MCP Server (Multiple Runners)

When running multiple Agent Runners on the same host, you can share a single MCP server to reduce resource usage:

```bash
# Primary runner: starts embedded MCP server on fixed port 9001
./agent-runner --profile coding --mcp-port 9001 --project-dir /project/a

# Secondary runners: use external MCP server (no embedded server started)
./agent-runner --profile testing --external-mcp-url http://127.0.0.1:9001/mcp --project-dir /project/b
./agent-runner --profile docs --external-mcp-url http://127.0.0.1:9001/mcp --project-dir /project/c
```

**Notes:**
- `--mcp-port` and `--external-mcp-url` are mutually exclusive
- The external URL must include protocol, host, port, and path (e.g., `http://127.0.0.1:9001/mcp`)
- All runners share the same MCP server for orchestration tools
- Each runner still has its own Runner Gateway for authentication

## Directory Structure

```
servers/agent-runner/
├── agent-runner             # Main runner script (uv script)
├── profiles/                # Executor profiles
│   ├── PROFILES.md          # Profile naming convention
│   ├── full-access-project-best.json
│   ├── full-access-isolated-best.json
│   ├── restricted-project-best.json
│   └── full-access-project-quick.json
├── lib/                     # Shared libraries
│   ├── config.py            # RunnerConfig
│   ├── executor.py          # Profile loading, RunExecutor
│   ├── invocation.py        # JSON payload schema (2.1)
│   ├── runner_gateway.py    # Gateway for executor communication
│   ├── session_client.py    # HTTP client for gateway
│   └── ...
├── docs/                    # Documentation
│   └── runner-gateway-api.md
├── executors/               # Executor implementations
│   ├── claude-code/         # Claude SDK executor (autonomous)
│   │   ├── ao-claude-code-exec
│   │   └── lib/claude_client.py
│   ├── test-executor/       # Test/dummy executor (autonomous)
│   │   └── ao-test-exec
│   └── procedural-executor/ # CLI command executor (procedural)
│       ├── ao-procedural-exec
│       └── scripts/         # Bundled agent scripts
│           └── echo/
│               ├── echo     # Echo script
│               └── agents/
│                   └── echo.json
└── tests/                   # Unit tests
```

## Executor Types

The runner supports different executor types for different agent behaviors:

### Autonomous Executors

Autonomous executors run AI agents that interpret intent and can be resumed:

| Executor | Type | Description |
|----------|------|-------------|
| `claude-code` | autonomous | Claude SDK with full coding capabilities |
| `test-executor` | autonomous | Simple echo executor for testing |

Autonomous agents:
- Interpret natural language prompts
- Maintain conversation state (can be resumed)
- Produce `result_text` only (no structured data)

### Procedural Executor

The procedural executor runs CLI commands with structured parameters:

| Executor | Type | Description |
|----------|------|-------------|
| `procedural` | procedural | Executes CLI scripts with `--key value` arguments |

Procedural agents:
- Execute a single CLI command per invocation
- Are stateless (cannot be resumed)
- Receive parameters as CLI arguments (`--key value` style)
- Produce `result_data` only (`result_text` is always null)

**How it works:**
1. Runner receives run with `agent_name` pointing to a procedural agent
2. Executor looks up the agent's `command` from the coordinator
3. Executor builds CLI arguments from parameters (`--key value` style)
4. Executor runs the command with arguments
5. Executor parses stdout and sends `result` event with `result_data`

**Parameter mapping (input):**
| Parameter Type | CLI Argument |
|---------------|--------------|
| `"key": "value"` | `--key value` |
| `"flag": true` | `--flag` |
| `"flag": false` | (omitted) |
| `"items": [1,2,3]` | `--items 1,2,3` |

**Result handling (output):**

The executor always returns `result_data` (never `result_text`). The logic is:

| Script stdout | `result_data` |
|---------------|---------------|
| Valid JSON | Passed through as-is |
| Not valid JSON | Fallback structure (see below) |

If stdout is **not valid JSON**, the executor returns a fallback structure:
```json
{
  "return_code": <exit_code>,
  "stdout": "<raw stdout>",
  "stderr": "<raw stderr>"
}
```

**Examples:**

```bash
# Script outputs valid JSON
./echo --message "Hello"
# stdout: {"message": "Hello"}
# result_data: {"message": "Hello"}

# Script outputs plain text (not JSON)
./legacy-script --arg value
# stdout: "Success: processed 5 items"
# result_data: {"return_code": 0, "stdout": "Success: processed 5 items", "stderr": ""}

# Script fails with error
./failing-script --arg value
# stdout: ""
# stderr: "Error: file not found"
# exit code: 1
# result_data: {"return_code": 1, "stdout": "", "stderr": "Error: file not found"}

# Script returns structured error (recommended)
./smart-script --arg value
# stdout: {"error": "file not found", "code": "ENOENT"}
# exit code: 1
# result_data: {"error": "file not found", "code": "ENOENT"}
```

**Best practice for scripts:**
- Always output valid JSON to stdout
- For errors, output JSON with an `error` field: `{"error": "message", ...}`
- Use stderr for debug/progress logging (not included in result unless fallback)

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
│  │ RUNNER GATEWAY              │  │ EMBEDDED MCP SERVER                     │   │
│  │ THREAD                      │  │ THREAD                                  │   │
│  │ (127.0.0.1:<dynamic>)       │  │ (127.0.0.1:<dynamic>)                   │   │
│  │                             │  │                                         │   │
│  │ • Enriches executor reqs    │  │ • FastMCP HTTP server                   │   │
│  │ • Adds hostname, profile    │  │ • 7 orchestration tools                 │   │
│  │ • Injects auth headers      │  │ • Facade to Coordinator API             │   │
│  │ • Routes to Coordinator     │  │ • Used by Claude for child agents       │   │
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
│   │  1. Use resolved blueprint from run payload                     │           │
│   │  2. Resolve Runner-specific placeholder:                        │           │
│   │     • ${runner.orchestrator_mcp_url} → http://127.0.0.1:<mcp>  │           │
│   │  3. Build Schema 2.1 JSON payload (with executor_config)          │           │
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
│  │  Reads JSON from stdin (Schema 2.1):                              │          │
│  │  {                                                                 │          │
│  │    "schema_version": "2.1",                                       │          │
│  │    "mode": "start",                                               │          │
│  │    "session_id": "ses_abc123",                                    │          │
│  │    "prompt": "...",                                               │          │
│  │    "executor_config": { ... },      ◄─ from profile               │          │
│  │    "agent_blueprint": { ... }       ◄─ resolved                   │          │
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
│  3. BLUEPRINT RESOLUTION (at Coordinator)                                        │
│     Coordinator resolves placeholders at run creation                           │
│     Runner receives resolved blueprint in run payload                           │
│     Runner only resolves ${runner.orchestrator_mcp_url} → MCP server URL        │
│                                                                                  │
│  4. EXECUTOR SPAWNING                                                            │
│     Runner ──[stdin JSON]──► Executor subprocess                                │
│     Env: AGENT_ORCHESTRATOR_API_URL=<gateway_url>                               │
│                                                                                  │
│  5. EXECUTOR → COORDINATOR (via Runner Gateway)                                 │
│     Executor ──[HTTP]──► Gateway ──[HTTP+Auth]──► Coordinator                   │
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
| Runner Gateway | Thread | dynamic | Enriches executor requests, handles auth |
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
    │ API Client   │          │ Runner       │          │ MCP Server   │
    │              │          │ Gateway      │          │              │
    │ (polling,    │          │ (enriches &  │          │ (orchestr.   │
    │  heartbeat,  │          │  forwards    │          │  tools)      │
    │  status)     │          │  executor)   │          │              │
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

Runs are passed to the executor as JSON via stdin (Schema 2.1):

| Type | Mode | Parameters |
|------|------|------------|
| `start_session` | `start` | `session_id`, `prompt`, `project_dir`, `executor_config`, `agent_blueprint` |
| `resume_session` | `resume` | `session_id`, `prompt`, `executor_config`, `agent_blueprint` |

**Schema 2.1 Notes:**
- `executor_config`: Configuration from the profile (permission_mode, model, etc.)
- `agent_blueprint`: Fully resolved blueprint with placeholders replaced
- Executor applies `executor_config` to configure itself (e.g., permission mode, model)

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

- Check that the profile's command path exists
- Verify `PROJECT_DIR` points to a valid directory
- Use `-v` flag for detailed subprocess output

## Runner Gateway

Executors communicate with the Agent Coordinator through the **Runner Gateway**, a local HTTP server that enriches requests with runner-owned data (hostname, executor_profile).

**Important:** The gateway exposes endpoints that **do not exist** on the Agent Coordinator:

| Gateway Endpoint | Coordinator Endpoint | Enrichment |
|------------------|---------------------|------------|
| `POST /bind` | `POST /sessions/{id}/bind` | Adds `hostname`, `executor_profile` |
| `POST /events` | `POST /sessions/{id}/events` | Routes by `session_id` |
| `PATCH /metadata` | `PATCH /sessions/{id}/metadata` | Routes by `session_id` |

See [Runner Gateway API](docs/runner-gateway-api.md) for full specification.

## Related Documentation

- [Runner Gateway API](docs/runner-gateway-api.md)
- [Agent Callback Architecture](../../docs/features/agent-callback-architecture.md)
- [Work Package 2: Agent Runner Process](../../docs/features/02-agent-runner-process.md)
