# Agent Callback Architecture

## Status

**Draft** - Feature Design & Implementation Specification

## Overview

This document describes the Agent Callback Architecture and its implementation via the **Agent Runner** component. The runner replaces the temporary Agent Control API and provides the foundation for callback-driven orchestration.

## Motivation

### Current Agent Execution Patterns

The Agent Orchestrator framework currently supports two patterns for spawning and managing child agents:

| Pattern | Description | Orchestrator Behavior | Result Retrieval |
|---------|-------------|----------------------|------------------|
| **Synchronous** | Blocking execution | Waits for completion | Immediate return |
| **Async (Polling)** | Fire-and-forget with status checks | Continues working, polls periodically | `ao-status` + `ao-get-result` |

### Problem Statement

Both patterns have limitations in orchestration scenarios:

1. **Synchronous**: Orchestrator is blocked and cannot perform other work or spawn additional agents in parallel.

2. **Polling**:
   - Orchestrator must actively poll, consuming compute time and tokens in the context window.
   - Polling interval creates a tradeoff between latency and resource usage
   - Orchestrator cannot truly "idle" - it must remain active to poll
   - Complex multi-agent coordination requires tracking multiple sessions

### Proposed Solution: Callback-Based Async

A third pattern where the **spawned agent notifies the orchestrator upon completion**, rather than the orchestrator polling:

```
Orchestrator ──start──► Child Agent ──runs──► completes
    │                        │                    │
    │◄──returns immediately──┘                    │
    │                                             │
    ├──continues work──►                          │
    │                                             │
    └──becomes idle (session ends)                │
                                                  │
                      ┌───────────────────────────┘
                      │ Agent Coordinator detects completion
                      │ Checks: is orchestrator idle?
                      ▼
           ┌─────────────────────┐
           │   Agent Runner      │
           │  (resumes session)  │
           └──────────┬──────────┘
                      │
                      ▼
            Orchestrator resumes with message:
            "Agent 'child-1' has completed.
             Retrieve results with ao-get-result."
```

### Why Callback-Based Async?

1. **Resource Efficiency**: Orchestrator can fully idle without consuming resources for polling loops.

2. **Natural Multi-Agent Coordination**: Multiple child agents can run in parallel, and the orchestrator gets notified when each (or all) complete.

3. **Transparent to Child Agents**: The callback mechanism is handled by the session management layer - child agents don't know they're being observed.

4. **Scalable Orchestration**: Enables patterns like fork/join parallelism, event-driven workflows, and hierarchical agent coordination.

### Use Cases

1. **Parallel Task Execution**: Orchestrator spawns 5 agents for independent tasks, idles, then resumes when all complete to aggregate results.

2. **Pipeline Patterns**: Agent A completes → triggers Agent B → triggers Agent C → orchestrator resumes with final result.

3. **Long-Running Tasks**: Child agent runs a 30-minute build/test cycle; orchestrator doesn't need to poll every minute.

### Callback Aggregation (POC Behavior)

For the POC, callbacks use an **immediate strategy with aggregation**:

1. When a child completes, check if parent is idle (`status = "finished"`)
2. **If parent is idle**: Resume immediately with notification about this child
3. **If parent is still running**: Queue the notification. When parent becomes idle, resume with aggregated message listing all completed children

This naturally handles parallel spawns - if an orchestrator spawns 5 agents and continues working, it receives one resume message listing all children that completed while it was busy.

**Implementation Note:** The notification queue is stored as an **in-memory dict** within the Callback Processor service, keyed by parent session name. This means pending notifications are lost if Agent Coordinator restarts - acceptable for POC.

## Goals

1. **Replace Agent Control API** - Eliminate the current MCP-server-based control API
2. **Enable Callbacks** - Provide the infrastructure for Agent Coordinator to resume orchestrator sessions
3. **Minimal Implementation** - Simplest path to a working POC
4. **Foundation for Future** - Design that can evolve (multiple runners, direct SDK integration)

## Callback Feature Constraints

### Fundamental Limitation

**Callbacks only work when the parent agent is started and controlled by the Agent Orchestrator framework.**

The callback mechanism requires the ability to resume the parent session. This is only possible if:
- The parent was started via the Run API → Runner
- The framework has control over the parent's lifecycle
- The runner can execute `ao-resume` on the parent

| Parent Started By | Framework Controls? | Can Resume? | Callbacks Work? |
|-------------------|---------------------|-------------|-----------------|
| Dashboard → Run API → Runner | ✅ Yes | ✅ Yes | ✅ Yes |
| User runs `claude` CLI directly | ❌ No | ❌ No | ❌ No |
| Claude Desktop | ❌ No | ❌ No | ❌ No |
| External MCP client | ❌ No | ❌ No | ❌ No |

**Rationale:** Claude Code CLI and Claude Desktop have no external API or hook for injecting resume commands. If the framework didn't start the parent, it cannot resume it.

### Callback Opt-In Mechanism

**Callbacks are opt-in.** The orchestrator must explicitly request callback behavior when spawning a child agent.

#### Why Opt-In?

1. **Backward compatibility**: Existing `async=true` behavior (fire-and-forget with manual polling) continues to work unchanged
2. **Explicit intent**: The orchestrator consciously chooses callback-based coordination vs polling
3. **Resource control**: Callbacks consume resources (resume runs, parent context tracking); only use when needed

#### MCP Server Parameter Change

The MCP server `start_agent_session` and `resume_agent_session` tools gain a new parameter:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `async_mode` | boolean | `false` | Existing: fire-and-forget execution |
| `callback` | boolean | `false` | **NEW**: Request callback when child completes |

**Interaction:**
- `async_mode=false, callback=false` → Synchronous (blocking) execution
- `async_mode=true, callback=false` → Async fire-and-forget, use polling
- `async_mode=true, callback=true` → Async with callback on completion
- `async_mode=false, callback=true` → Invalid (ignored, sync already waits)

#### MCP Server Implementation

When `callback=true`:
1. MCP server reads `AGENT_SESSION_NAME` from environment (set by Runner for parent)
2. Sets `AGENT_SESSION_NAME={parent_session_name}` in subprocess environment when spawning `ao-start`
3. `ao-start` reads env var and passes `parent_session_name` to Sessions API

```python
# In MCP server execute_script_async()
async def execute_script_async(config, args, callback: bool = False):
    env = os.environ.copy()

    if callback:
        parent_session = os.environ.get("AGENT_SESSION_NAME")
        if parent_session:
            env["AGENT_SESSION_NAME"] = parent_session
        else:
            logger.warn("callback=true but AGENT_SESSION_NAME not set - callback will not work")

    process = subprocess.Popen(uv_args, env=env, ...)
```

### Parent Session Context

For callbacks to work, child agents must know their parent's identity. This requires:

1. **Runner sets environment variable** when starting a session:
   ```bash
   AGENT_SESSION_NAME=orchestrator ao-start orchestrator -p "..."
   ```

2. **MCP server propagates** when `callback=true`:
   - Reads `AGENT_SESSION_NAME` from its own environment
   - Sets it in child subprocess environment

3. **ao-start/ao-resume read this variable** and include it in API calls:
   ```python
   parent_session_name = os.environ.get("AGENT_SESSION_NAME")
   ```

4. **Sessions API extended** to track parent-child relationships:
   ```json
   POST /sessions
   {
     "session_id": "uuid",
     "session_name": "child-task",
     "parent_session_name": "orchestrator",  // NEW
     ...
   }
   ```

5. **Sessions table extended** with new column:
   ```sql
   ALTER TABLE sessions ADD COLUMN parent_session_name TEXT;
   ```

### Required Changes to ao-* Commands

**ao-start:**
- Read `AGENT_SESSION_NAME` environment variable
- Pass `parent_session_name` to `POST /sessions` API
- This identifies which session started this child

**ao-resume:**
- Read `AGENT_SESSION_NAME` environment variable
- Include in session metadata updates
- Ensures resumed sessions maintain parent context

**Sessions API:**
- Accept optional `parent_session_name` field in session creation/update
- Store in sessions table
- Callback Processor uses this to find parent when child completes

### Callback Flow with Parent Context

```
1. Runner starts orchestrator:
   AGENT_SESSION_NAME=orchestrator ao-start orchestrator -p "..."

2. Orchestrator calls MCP tool with callback=true:
   start_agent_session(name="child", prompt="...", async_mode=true, callback=true)

3. MCP server spawns ao-start with env var:
   AGENT_SESSION_NAME=orchestrator ao-start child -p "..."
   → ao-start reads AGENT_SESSION_NAME=orchestrator
   → Child session created with parent_session_name=orchestrator

4. Child completes (run_completed event)
   → Callback Processor checks: does child have parent_session_name?
   → Yes: parent_session_name=orchestrator
   → Create resume run for "orchestrator"

5. Runner resumes orchestrator:
   ao-resume orchestrator -p "Child task completed..."
```

### Parent Session Context via MCP HTTP Mode

When agents use the Agent Orchestrator **MCP server in HTTP mode** (instead of the Skill), a different mechanism is needed to propagate the parent session name. The environment variable approach used by the Skill doesn't work because the MCP server runs as a separate process.

#### Solution: HTTP Headers

The parent session name is passed via a custom HTTP header when Claude Code connects to the MCP server.

**Naming Convention:**
| Component | Name |
|-----------|------|
| Environment Variable | `AGENT_SESSION_NAME` |
| HTTP Header | `X-Agent-Session-Name` |
| Placeholder Pattern | `${AGENT_SESSION_NAME}` |

#### Flow Diagram

```
1. Runner starts Claude Code via SDK:
   - Sets AGENT_SESSION_NAME=orchestrator in environment
   - Provides optional agent name to the ao-start/ao-resume command

MCP Config (retrieved from agent-coordinator endpoints):
   {
     "mcpServers": {
       "agent-orchestrator": {
         "type": "http",
         "url": "${runner.orchestrator_mcp_url}",
         "headers": {
           "X-Agent-Session-Id": "${runtime.session_id}"
         }
       }
     }
   }

3. ao-start/ao-resume builds MCP config:
   - Fetches agent blueprint from Agent Coordinator (includes MCP config with placeholder, see example above)
   - Reads AGENT_SESSION_NAME from environment
   - Replaces ${AGENT_SESSION_NAME} → e.g. with "orchestrator"
   - Passes resolved config to Claude Agent SDK

4. Claude Code calls MCP server:
   - HTTP request includes: X-Agent-Session-Name: orchestrator

5. MCP Server receives request:
   - Extracts X-Agent-Session-Name header
   - Sets AGENT_SESSION_NAME=orchestrator in subprocess environment
   - Spawns ao-start/ao-resume with this env var

6. ao-start/ao-resume:
   - Reads AGENT_SESSION_NAME from environment (same as Skill flow)
   - Creates session with parent_session_name=orchestrator
```

#### How Placeholder Replacement Works

The Runner sets the `AGENT_SESSION_NAME` environment variable before spawning `ao-start`/`ao-resume`. The **ao-* commands** then:

1. Read the environment variable
2. Fetch the agent blueprint from Agent Coordinator (which contains MCP config with `${AGENT_SESSION_NAME}` placeholder)
3. Replace the placeholder with the actual session name (done in `agent_api.py` which understands the MCP config model)
4. Pass the resolved config to the Claude Agent Python SDK

This approach:
- Keeps the pattern consistent with Claude Code's config syntax
- Is transparent to the agent (no explicit parameter passing)
- Works identically whether using Skill or MCP server
- Keeps the Runner simple (just sets env var and spawns subprocess)

#### Required Changes

**1. Dashboard MCP Server Schema** (`apps/dashboard/src/types/agent.ts`):
```typescript
export interface MCPServerHttp {
  type: 'http';
  url: string;
  headers?: Record<string, string>;  // NEW
}
```

**2. Default MCP Template** (`apps/dashboard/src/utils/mcpTemplates.ts`):
```typescript
'agent-orchestrator-http': {
  type: 'http',
  url: '${runner.orchestrator_mcp_url}',
  headers: {
    'X-Agent-Session-Id': '${runtime.session_id}'
  }
}
```

**3. MCP Server** (`interfaces/agent-orchestrator-mcp-server/`):
- Extract `X-Agent-Session-Name` header from incoming HTTP requests
- Pass as `AGENT_SESSION_NAME` environment variable to `ao-start`/`ao-resume` subprocesses
- Uses FastMCP's `get_http_headers()` helper to access headers

**4. Runner SDK Integration**:
- When building MCP config for SDK, replace `${AGENT_SESSION_NAME}` placeholder
- Use the session_name of the agent being started

## Terminology

### Run vs Session

| Term | Definition | Lifecycle | Persistence |
|------|------------|-----------|-------------|
| **Session** | A Claude Code agent conversation with its own ID, state, events, and result. Represents the agent's ongoing work and context. | Long-lived: `started` → `running` → `finished`/`error` | Persisted in Agent Coordinator database |
| **Run** | A discrete command for the runner to execute. Represents a single operation request. | Short-lived: `pending` → `running` → `completed`/`failed` | Transient (in-memory queue) |

**Relationship:**
- A Run triggers Session operations
- Run types: `start_session`, `resume_session`
- One Session may be acted upon by multiple Runs over time (start once, resume many times)
- Runs are consumed by the Runner; Sessions are tracked by the Coordinator

```
Run: "start_session"     →  Creates Session "task-1"
Run: "resume_session"    →  Resumes Session "task-1" (callback)
Run: "resume_session"    →  Resumes Session "task-1" (another callback)
```

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Agent Coordinator (Docker) :8765                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │  Sessions API   │  │  Callbacks API  │  │     Runner API          │  │
│  │  (existing)     │  │  (NEW)          │  │     (NEW)               │  │
│  └─────────────────┘  └─────────────────┘  └───────────┬─────────────┘  │
│                                                        │                 │
│  ┌─────────────────────────────────────────────────────┴───────────────┐│
│  │                        Run Queue                                     ││
│  │  - Pending runs waiting for runner                                   ││
│  │  - In-memory for POC (future: persistent)                           ││
│  └─────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP Long-polling
                                    │ (Runner polls for runs)
                                    │
┌───────────────────────────────────┴─────────────────────────────────────┐
│                    Agent Runner (Host Machine)                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │  Registration   │  │   Run Poller    │  │    Run Executor         │  │
│  │  (on startup)   │  │  (long-poll)    │  │  (subprocess ao-*)      │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Subprocess
                                    ▼
                            ┌───────────────┐
                            │  Claude Code  │
                            │  (ao-start,   │
                            │   ao-resume)  │
                            └───────────────┘
```

### Runner Lifecycle

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Startup   │────►│  Register   │────►│  Main Loop  │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                         ┌─────────────────────┼─────────────────────┐
                         │                     │                     │
                         ▼                     ▼                     ▼
                  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
                  │ Poll Thread │       │  Supervisor │       │  Heartbeat  │
                  │ (get runs)  │       │  (monitor   │       │  Thread     │
                  └──────┬──────┘       │  processes) │       └─────────────┘
                         │              └──────┬──────┘
                         │                     │
                         ▼                     ▼
                  ┌─────────────────────────────────────┐
                  │         Running Runs Registry       │
                  │  run_id → { subprocess, status }    │
                  └─────────────────────────────────────┘
```

### Concurrent Execution Model

The runner **must** support concurrent run execution. This is required because:

1. **Orchestrator scenario**: Dashboard starts an orchestrator (Run 1), which then starts child agents (Run 2, 3, ...). If the runner could only run one run, the orchestrator would be blocked.

2. **Callback scenario**: Multiple child agents may complete while the orchestrator is waiting, triggering multiple resume runs.

**Concurrency Design:**

| Component | Responsibility |
|-----------|----------------|
| **Poll Thread** | Continuously polls for new runs, spawns subprocess for each |
| **Running Runs Registry** | In-memory dict tracking `run_id → subprocess` |
| **Supervisor Thread** | Monitors subprocesses, detects completion/failure, reports status |
| **Heartbeat Thread** | Sends periodic heartbeats to Agent Coordinator |

**Subprocess Management:**

```python
# Simplified model
running_runs: Dict[str, subprocess.Popen] = {}

# Poll thread: spawn new run
proc = subprocess.Popen(["ao-start", ...], ...)
running_runs[run_id] = proc
report_run_started(run_id)

# Supervisor thread: check completion
for run_id, proc in running_runs.items():
    if proc.poll() is not None:  # Process finished
        if proc.returncode == 0:
            report_run_completed(run_id)
        else:
            report_run_failed(run_id, proc.stderr)
        del running_runs[run_id]
```

**Max Concurrency (optional for POC):**

For POC, we can allow unlimited concurrent runs (practical limit ~10-20 based on system resources). Future enhancement could add `max_concurrent_runs` configuration.

## Protocol Design

### Registration Flow

On startup, the runner registers with the Agent Coordinator to receive a unique identifier.

```
Runner                                Agent Coordinator
   │                                       │
   │  POST /runner/register                │
   │  { }                                  │
   │──────────────────────────────────────►│
   │                                       │
   │  200 OK                               │
   │  {                                    │
   │    "runner_id": "lnch_abc123",        │
   │    "poll_endpoint": "/runner/runs",   │
   │    "poll_timeout_seconds": 30         │
   │  }                                    │
   │◄──────────────────────────────────────│
   │                                       │
```

### Run Polling Flow (Long-polling)

The runner continuously polls for runs. The server holds the connection open until a run is available or timeout occurs.

```
Runner                                Agent Coordinator
   │                                       │
   │  GET /runner/runs?runner_id=X         │
   │  (blocks up to 30 seconds)            │
   │──────────────────────────────────────►│
   │                                       │
   │         ... server waits ...          │
   │                                       │
   │  200 OK (run available)               │
   │  {                                    │
   │    "run": {                           │
   │      "run_id": "run_xyz789",          │
   │      "type": "start_session",         │
   │      "session_name": "task-1",        │
   │      "agent_name": "researcher",      │
   │      "prompt": "Research topic X",    │
   │      "project_dir": "/path/to/proj"   │
   │    }                                  │
   │  }                                    │
   │◄──────────────────────────────────────│
   │                                       │
   │  OR                                   │
   │                                       │
   │  204 No Content (timeout, no runs)    │
   │◄──────────────────────────────────────│
   │                                       │
```

### Run Execution Flow

```
Runner                                Agent Coordinator
   │                                       │
   │  (receives run from poll)             │
   │                                       │
   │  POST /runner/runs/{run_id}/started   │
   │  { "runner_id": "lnch_abc123" }       │
   │──────────────────────────────────────►│
   │                                       │
   │  (executes ao-start/ao-resume)        │
   │  (subprocess runs...)                 │
   │                                       │
   │  POST /runner/runs/{run_id}/completed │
   │  {                                    │
   │    "runner_id": "lnch_abc123",        │
   │    "status": "success"                │
   │  }                                    │
   │──────────────────────────────────────►│
   │                                       │
   │  OR (on failure)                      │
   │                                       │
   │  POST /runner/runs/{run_id}/failed    │
   │  {                                    │
   │    "runner_id": "lnch_abc123",        │
   │    "error": "ao-start failed: ..."    │
   │  }                                    │
   │──────────────────────────────────────►│
   │                                       │
```

### Resume Run (For Callbacks)

When a child agent completes and triggers a callback, the Callback Processor creates a `resume_session` run.

```json
{
  "run_id": "run_callback_001",
  "type": "resume_session",
  "session_name": "orchestrator-main",
  "prompt": "## Agent Callback Notification\n\nAgent session `task-1` has completed with status: finished.\n\nTo retrieve the result: `ao-get-result task-1`"
}
```

The runner executes:
```bash
ao-resume orchestrator-main -p "Child session completed..."
```

## API Specification

### Runner API Endpoints (New in Agent Coordinator)

#### POST /runner/register

Register a new runner instance.

**Request:** `{}` (empty body for anonymous registration)

**Response:**
```json
{
  "runner_id": "lnch_abc123def",
  "poll_endpoint": "/runner/runs",
  "poll_timeout_seconds": 30,
  "heartbeat_interval_seconds": 60
}
```

#### GET /runner/runs

Long-poll for available runs.

**Query Parameters:**
- `runner_id` (required): The registered runner ID

**Response (run available):** `200 OK`
```json
{
  "run": {
    "run_id": "run_xyz789",
    "type": "start_session",
    "session_name": "task-worker-1",
    "agent_name": "researcher",
    "prompt": "Research the topic...",
    "project_dir": "/Users/ramon/project"
  }
}
```

**Response (no runs):** `204 No Content`

#### POST /runner/runs/{run_id}/started

Report run execution has started.

**Request:**
```json
{
  "runner_id": "lnch_abc123"
}
```

**Response:** `200 OK`

#### POST /runner/runs/{run_id}/completed

Report run completed successfully.

**Request:**
```json
{
  "runner_id": "lnch_abc123",
  "status": "success"
}
```

**Response:** `200 OK`

#### POST /runner/runs/{run_id}/failed

Report run execution failed.

**Request:**
```json
{
  "runner_id": "lnch_abc123",
  "error": "Error message from subprocess"
}
```

**Response:** `200 OK`

#### POST /runner/heartbeat

Keep runner registration alive.

**Request:**
```json
{
  "runner_id": "lnch_abc123"
}
```

**Response:** `200 OK`

### Run Creation Endpoints

#### POST /runs

Create a new run (used by Dashboard, future ao-start).

**Request:**
```json
{
  "type": "start_session",
  "session_name": "my-agent",
  "agent_name": "researcher",
  "prompt": "Do the thing",
  "project_dir": "/path/to/project"
}
```

**Response:**
```json
{
  "run_id": "run_abc123",
  "status": "pending"
}
```

#### GET /runs/{run_id}

Get run status.

**Response:**
```json
{
  "run_id": "run_abc123",
  "type": "start_session",
  "status": "completed",
  "created_at": "2025-01-15T10:00:00Z",
  "started_at": "2025-01-15T10:00:01Z",
  "completed_at": "2025-01-15T10:00:45Z"
}
```

## Run Types

| Type | Purpose | Parameters | Executed As |
|------|---------|------------|-------------|
| `start_session` | Start a new agent session | `session_name`, `agent_name`, `prompt`, `project_dir` | `ao-start` subprocess |
| `resume_session` | Resume an existing session | `session_name`, `prompt` | `ao-resume` subprocess |

**Note:** `resume_session` does not require `project_dir` - the `ao-resume` command fetches the original `project_dir` from the session API, ensuring consistency with the original session.

## Callback Flow

The Agent Runner enables the following callback flow:

```
1. Runner starts orchestrator with env var:
   AGENT_SESSION_NAME=orchestrator ao-start orchestrator -p "..."

2. Orchestrator starts child via ao-start:
   └─► ao-start reads AGENT_SESSION_NAME from env
   └─► Child session created with parent_session_name=orchestrator

3. Child agent completes (run_completed event)
   └─► Callback Processor detects completion
   └─► Checks: does child have parent_session_name? → Yes

4. Callback Processor checks: is parent idle?
   └─► Parent session status = "finished" → Yes, idle

5. Callback Processor creates resume run
   └─► Run queued: type=resume_session, session_name=orchestrator

6. Runner polls and receives resume run
   └─► Executes: ao-resume orchestrator -p "Child session completed..."

7. Orchestrator resumes with callback notification
   └─► Can call ao-get-result to retrieve child's output
```

## Callback Trigger Implementation

This section documents where callback notifications to parent agents are triggered in the codebase.

### Trigger Locations

All callback triggers are unified in the Runner API endpoints:

| Event | Trigger Location | Endpoint/Handler | Notes |
|-------|------------------|------------------|-------|
| **Success** | `main.py` | `POST /runner/runs/{run_id}/completed` | Triggered when runner reports run completion |
| **Failure** | `main.py` | `POST /runner/runs/{run_id}/failed` | Triggered when runner reports run failure |
| **Stopped** | `main.py` | `POST /runner/runs/{run_id}/stopped` | Triggered when runner reports run was stopped |

### Implementation Details

**Success Callback** (`POST /runner/runs/{run_id}/completed`):
- Triggered by: Agent Runner (supervisor) calling `report_completed()` when process exits with code 0
- Flow: Run marked as `COMPLETED` → session status updated to `finished` → checks `run.parent_session_id` → calls `callback_processor.on_child_completed()`
- Result passed: Yes (retrieves child result via `get_session_result()`)

**Failure Callback** (`POST /runner/runs/{run_id}/failed`):
- Triggered by: Agent Runner calling `report_failed()` when subprocess exits with error
- Flow: Run marked as `FAILED` → checks `run.parent_session_id` → calls `callback_processor.on_child_completed(child_failed=True)`
- Error passed: Yes (error from runner's `request.error`)

**Stopped Callback** (`POST /runner/runs/{run_id}/stopped`):
- Triggered by: Agent Runner calling `report_stopped()` after terminating a process
- Flow: Run marked as `STOPPED` → session status updated to `stopped` → checks `run.parent_session_id` → calls `callback_processor.on_child_completed(child_failed=True)`
- Error passed: Yes (hardcoded message: "Session was manually stopped")

### Architectural Note

All callback triggers are now unified in the Runner API endpoints, providing a consistent pattern:
- The agent runner's supervisor monitors executor processes
- When a process exits, the appropriate endpoint is called (completed/failed/stopped)
- The coordinator updates run and session status, then triggers callbacks if applicable
- Executors no longer send lifecycle events (run_start, run_completed) - this is handled by the runner

## Implementation Plan

### Phase 1: Runner API in Agent Coordinator

**Files to modify:** `servers/agent-coordinator/`

1. **Add Run queue (in-memory, thread-safe)**
   - Use `threading.Lock` to protect concurrent access
   - Run states: `pending` → `claimed` → `running` → `completed`/`failed`
   - Atomic `claim_run()` operation marks run as `claimed` before returning
   - Multiple accessors: Poll endpoint, Dashboard POST, Callback Processor

2. **Add Runner registry (in-memory)**
   - Track registered runners by ID
   - Track last heartbeat time

3. **Implement endpoints:**
   - `POST /runner/register`
   - `GET /runner/runs` (with long-polling)
   - `POST /runner/runs/{id}/started`
   - `POST /runner/runs/{id}/completed`
   - `POST /runner/runs/{id}/failed`
   - `POST /runner/heartbeat`
   - `POST /runs`
   - `GET /runs/{id}`

### Phase 2: Agent Runner Process

**New directory:** `servers/agent-runner/`

1. **Create runner CLI**
   - Python script that runs as a standalone process
   - Configuration via environment variables or CLI args

2. **Implement registration**
   - On startup, POST to /runner/register
   - Store runner_id for subsequent requests

3. **Implement Running Runs Registry**
   - Thread-safe dict: `run_id → { process: Popen, started_at: datetime }`
   - Methods: `add_run()`, `remove_run()`, `get_running_runs()`

4. **Implement Poll Thread**
   - Runs in background thread
   - Long-poll GET /runner/runs
   - Handle timeout (204) → retry immediately
   - Handle run → spawn subprocess, add to registry, report started

5. **Implement Supervisor Thread**
   - Runs in background thread
   - Periodically checks all running subprocesses (`proc.poll()`)
   - On completion: report completed/failed, remove from registry
   - Interval: ~1 second

6. **Implement Run Executor**
   - Map run type to subprocess command
   - `start_session` → `ao-start --name X --agent Y --prompt "Z"`
   - `resume_session` → `ao-resume --session X --message "Y"`
   - Use `subprocess.Popen()` for non-blocking execution
   - **Command Discovery**: Auto-discover `ao-*` commands relative to project root. Don't use `AGENT_ORCHESTRATOR_COMMAND_PATH` env var for override.
   - **Logging**: Log run execution to stdout/stderr (concise, not verbose) for visibility during POC

7. **Implement Heartbeat Thread**
   - Background thread sending periodic heartbeats

### Phase 3: Dashboard Integration

**Files to modify:** `apps/dashboard/`

1. **Update Chat tab**
   - Change from Agent Control API to new `/runs` endpoint
   - Create run via `POST /runs`
   - Rely on existing SSE connection for session updates (no run status polling)
   - IMPORTANT: Also listen for session start events for the current session name via SSE, as now the resume can automatically start the session again.

2. **Remove Agent Control API dependency**
   - Remove `VITE_AGENT_CONTROL_API_URL` usage

### Phase 4: Parent Session Context (ao-* Commands & Sessions API)

**Files to modify:**
- `plugins/orchestrator/skills/orchestrator/commands/ao-start`
- `plugins/orchestrator/skills/orchestrator/commands/ao-resume`
- `plugins/orchestrator/skills/orchestrator/commands/lib/`
- `servers/agent-coordinator/` (sessions API)

1. **Extend Sessions API**
   - Add `parent_session_name` field to session creation/update
   - Add column to sessions table: `parent_session_name TEXT`
   - Return `parent_session_name` in session queries

2. **Update ao-start**
   - Read `AGENT_SESSION_NAME` environment variable
   - Pass as `parent_session_name` to `POST /sessions` API
   - No new CLI flags needed - transparent to caller

3. **Update ao-resume**
   - Read `AGENT_SESSION_NAME` environment variable
   - Include in session metadata updates

4. **Update Runner executor**
   - Set `AGENT_SESSION_NAME={session_name}` when spawning subprocess
   - This propagates parent context to child agents

### Phase 5: Callback Integration

**Files to modify:** `servers/agent-coordinator/`

1. **Implement Callback Processor**
   - Called directly from Sessions API when `run_completed` event is received (synchronous function call)
   - Maintains in-memory notification queue (dict keyed by parent session name)
   - Check if session has `parent_session_name`
   - Check parent session status (must be `finished` = idle)
   - If parent is idle: create resume_session run immediately
   - If parent is still running: add to notification queue
   - When parent's own `run_completed` event arrives: check queue and create aggregated resume run

2. **Wire into session events**
   - Sessions API calls Callback Processor directly on `run_completed` events
   - Generate resume message: "Child session X completed..."

## File Structure (Proposed)

```
├── servers/
│   ├── agent-coordinator/
│   │   ├── routers/
│   │   │   ├── runner.py            # NEW: Runner API endpoints
│   │   │   ├── runs.py              # NEW: Run management endpoints
│   │   │   └── ...
│   │   ├── services/
│   │   │   ├── run_queue.py         # NEW: In-memory run queue
│   │   │   ├── runner_registry.py   # NEW: Runner tracking
│   │   │   ├── callback_processor.py # NEW: Callback logic
│   │   │   └── ...
│   │   └── models/
│   │       ├── run.py               # NEW: Run model
│   │       └── ...
│   └── agent-runner/
│       ├── agent-runner             # Main script (uv run --script)
│       └── lib/                     # Service modules
│           ├── __init__.py
│           ├── config.py            # Configuration
│           ├── registry.py          # Running Runs Registry (thread-safe)
│           ├── poller.py            # Poll Thread - fetches runs from Agent Coordinator
│           ├── supervisor.py        # Supervisor Thread - monitors subprocesses
│           ├── executor.py          # Run execution (subprocess spawning)
│           └── api_client.py        # HTTP client for Agent Coordinator API
```

### Agent Runner Script Pattern

Following the same pattern as `ao-start` and `ao-resume`:

**Main script** (`agent-runner`):
```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx",
#     "typer",
# ]
# ///
"""Agent Runner - Connects to Agent Coordinator and executes runs."""

import sys
from pathlib import Path

# Add lib to path for service modules
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from config import RunnerConfig
from registry import RunningRunsRegistry
from poller import RunPoller
from supervisor import RunSupervisor
from api_client import CoordinatorAPIClient

# ... main implementation
```

**Service modules** (`lib/*.py`) - plain Python files, no special headers needed.

**Benefits:**
- No installation required - `uv` handles dependencies automatically
- Run from any directory: `./servers/agent-runner/agent-runner`
- Modular code with clean separation of concerns
- Same pattern as existing ao-* commands

## Configuration

### Agent Runner

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_ORCHESTRATOR_API_URL` | `http://localhost:8765` | Agent Coordinator URL to connect to |
| `POLL_TIMEOUT` | `30` | Long-poll timeout in seconds |
| `HEARTBEAT_INTERVAL` | `60` | Heartbeat interval in seconds |
| `PROJECT_DIR` | cwd | Default project directory for ao-* commands |

### Agent Coordinator

| Variable | Default | Description |
|----------|---------|-------------|
| `RUNNER_POLL_TIMEOUT` | `30` | How long to hold poll requests |
| `RUNNER_HEARTBEAT_TIMEOUT` | `120` | Mark runner as dead after this |

## Migration Path

1. **Implement Runner API** in Agent Coordinator (no breaking changes)
2. **Create Agent Runner** process
3. **Update Dashboard** to use `/runs` endpoint
4. **Deprecate Agent Control API** - stop using/documenting
5. **Remove Agent Control API** - delete code from MCP server

## Success Criteria (POC)

- [ ] Runner registers with Agent Coordinator
- [ ] Dashboard can start sessions via `/runs` endpoint
- [ ] Runner executes `ao-start` and reports completion
- [ ] Runner executes `ao-resume` and reports completion
- [ ] Callback flow works: child completes → orchestrator resumes
- [ ] Agent Control API can be disabled

## Future Enhancements (Post-POC)

1. **Multiple runners** - Runner selection, load balancing
2. **Persistent run queue** - SQLite storage for runs
3. **Direct SDK integration** - Runner uses Claude SDK directly
4. **ao-start via API** - Commands create runs instead of running directly
5. **Runner capabilities** - Different runners for different agent types
6. **Authentication** - Secure runner registration

## Known Limitations (POC)

The following are explicitly **out of scope** for the POC:

1. **Error handling** - No retry logic for failed callbacks, no handling of deleted parent sessions, no recovery from Runner crashes mid-run

2. **Run failure notification to Dashboard** - If a run fails (e.g., `ao-start` errors), the Dashboard has no way to know. It creates a run and relies on SSE for session updates; if the session never starts, the Dashboard sees nothing. Future: broadcast run failures via SSE or have Dashboard poll run status briefly after creation.

3. **Callback strategies** - Only "immediate with aggregation" is implemented. No configurable strategies like "wait for all children" or "batch with delay".

4. **Parent session cleanup** - When a parent session is deleted while children are running or callbacks are pending, the callbacks will fail gracefully (Callback Processor logs an error). No automatic cleanup of pending notifications.

5. **Heartbeat timeout handling** - When a Runner's heartbeat times out, it is marked as dead but orphaned runs remain in their current state. No automatic run recovery or reassignment.

## Testing the Callback Mechanism

### Test Scenario: Parallel Agent Callbacks with Busy Parent

This test validates that callbacks are correctly queued when the parent is busy and delivered when it becomes idle.

**Setup:** Start an orchestrator agent with the following prompt:

```
You are a helpful agent and use the agent orchestrator mcp wisely to help the user.
You check for available specialist agents before starting an agent.

---

Test the callback delivery mechanism of the agent orchestrator framework:

1. Start 4 child agents in parallel, all with async_mode=true and callback=true:
   - wait-10-sec: Wait for 10 seconds, then respond "Done 10s"
   - wait-15-sec: Wait for 15 seconds, then respond "Done 15s"
   - wait-20-sec: Wait for 20 seconds, then respond "Done 20s"
   - wait-25-sec: Wait for 25 seconds, then respond "Done 25s"

2. Immediately after starting all 4 agents, execute a blocking command: `sleep 20`

3. After the sleep completes, wait for the user to give you further instructions.
```

**Follow-up prompt** (after callbacks arrive):

```
Now review your conversation history and document:
- Which callbacks did you explicitly receive (look for "## Child Result" messages)?
- Which callbacks are missing?

For any missing callbacks, use get_agent_session_status and get_agent_session_result
to verify the agents actually completed.

Report your findings: How many callbacks were lost during your busy state vs.
delivered successfully?
```

**Expected behavior:**
- Agents completing while parent is busy (sleep 20) should have callbacks queued
- When parent becomes idle, it should receive aggregated callback notification
- All 4 child completions should eventually be reported

## Related Documents

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Overall system architecture
- [DATABASE_SCHEMA.md](../components/agent-coordinator/DATABASE_SCHEMA.md) - Current database schema
