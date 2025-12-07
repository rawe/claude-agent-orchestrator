# Agent Callback Architecture

## Status

**Draft** - Feature Design & Implementation Specification

## Overview

This document describes the Agent Callback Architecture and its implementation via the **Agent Launcher** component. The launcher replaces the temporary Agent Control API and provides the foundation for callback-driven orchestration.

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
                      │ Agent Runtime detects completion
                      │ Checks: is orchestrator idle?
                      ▼
           ┌─────────────────────┐
           │   Agent Launcher    │
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

**Implementation Note:** The notification queue is stored as an **in-memory dict** within the Callback Processor service, keyed by parent session name. This means pending notifications are lost if Agent Runtime restarts - acceptable for POC.

## Goals

1. **Replace Agent Control API** - Eliminate the current MCP-server-based control API
2. **Enable Callbacks** - Provide the infrastructure for Agent Runtime to resume orchestrator sessions
3. **Minimal Implementation** - Simplest path to a working POC
4. **Foundation for Future** - Design that can evolve (multiple launchers, direct SDK integration)

## Callback Feature Constraints

### Fundamental Limitation

**Callbacks only work when the parent agent is started and controlled by the Agent Orchestrator framework.**

The callback mechanism requires the ability to resume the parent session. This is only possible if:
- The parent was started via the Job API → Launcher
- The framework has control over the parent's lifecycle
- The launcher can execute `ao-resume` on the parent

| Parent Started By | Framework Controls? | Can Resume? | Callbacks Work? |
|-------------------|---------------------|-------------|-----------------|
| Dashboard → Job API → Launcher | ✅ Yes | ✅ Yes | ✅ Yes |
| User runs `claude` CLI directly | ❌ No | ❌ No | ❌ No |
| Claude Desktop | ❌ No | ❌ No | ❌ No |
| External MCP client | ❌ No | ❌ No | ❌ No |

**Rationale:** Claude Code CLI and Claude Desktop have no external API or hook for injecting resume commands. If the framework didn't start the parent, it cannot resume it.

### Callback Opt-In Mechanism

**Callbacks are opt-in.** The orchestrator must explicitly request callback behavior when spawning a child agent.

#### Why Opt-In?

1. **Backward compatibility**: Existing `async=true` behavior (fire-and-forget with manual polling) continues to work unchanged
2. **Explicit intent**: The orchestrator consciously chooses callback-based coordination vs polling
3. **Resource control**: Callbacks consume resources (resume jobs, parent context tracking); only use when needed

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
1. MCP server reads `AGENT_SESSION_NAME` from environment (set by Launcher for parent)
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

1. **Launcher sets environment variable** when starting a session:
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
1. Launcher starts orchestrator:
   AGENT_SESSION_NAME=orchestrator ao-start orchestrator -p "..."

2. Orchestrator calls MCP tool with callback=true:
   start_agent_session(name="child", prompt="...", async_mode=true, callback=true)

3. MCP server spawns ao-start with env var:
   AGENT_SESSION_NAME=orchestrator ao-start child -p "..."
   → ao-start reads AGENT_SESSION_NAME=orchestrator
   → Child session created with parent_session_name=orchestrator

4. Child completes (session_stop event)
   → Callback Processor checks: does child have parent_session_name?
   → Yes: parent_session_name=orchestrator
   → Create resume job for "orchestrator"

5. Launcher resumes orchestrator:
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
1. Launcher starts Claude Code via SDK:
   - Sets AGENT_SESSION_NAME=orchestrator in environment
   - Provides optional agent name to the ao-start/ao-resume command

MCP Config (retrieved from agent-runtime endpoints):
   {
     "mcpServers": {
       "agent-orchestrator": {
         "type": "http",
         "url": "http://localhost:9500/mcp",
         "headers": {
           "X-Agent-Session-Name": "${AGENT_SESSION_NAME}"
         }
       }
     }
   }

3. ao-start/ao-resume builds MCP config:
   - Fetches agent blueprint from Agent Runtime (includes MCP config with placeholder, see example above)
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

The Launcher sets the `AGENT_SESSION_NAME` environment variable before spawning `ao-start`/`ao-resume`. The **ao-* commands** then:

1. Read the environment variable
2. Fetch the agent blueprint from Agent Runtime (which contains MCP config with `${AGENT_SESSION_NAME}` placeholder)
3. Replace the placeholder with the actual session name (done in `agent_api.py` which understands the MCP config model)
4. Pass the resolved config to the Claude Agent Python SDK

This approach:
- Keeps the pattern consistent with Claude Code's config syntax
- Is transparent to the agent (no explicit parameter passing)
- Works identically whether using Skill or MCP server
- Keeps the Launcher simple (just sets env var and spawns subprocess)

#### Required Changes

**1. Dashboard MCP Server Schema** (`dashboard/src/types/agent.ts`):
```typescript
export interface MCPServerHttp {
  type: 'http';
  url: string;
  headers?: Record<string, string>;  // NEW
}
```

**2. Default MCP Template** (`dashboard/src/utils/mcpTemplates.ts`):
```typescript
'agent-orchestrator-http': {
  type: 'http',
  url: 'http://localhost:9500/mcp',
  headers: {
    'X-Agent-Session-Name': '${AGENT_SESSION_NAME}'
  }
}
```

**3. MCP Server** (`interfaces/agent-orchestrator-mcp-server/`):
- Extract `X-Agent-Session-Name` header from incoming HTTP requests
- Pass as `AGENT_SESSION_NAME` environment variable to `ao-start`/`ao-resume` subprocesses
- Uses FastMCP's `get_http_headers()` helper to access headers

**4. Launcher SDK Integration**:
- When building MCP config for SDK, replace `${AGENT_SESSION_NAME}` placeholder
- Use the session_name of the agent being started

## Terminology

### Job vs Session

| Term | Definition | Lifecycle | Persistence |
|------|------------|-----------|-------------|
| **Session** | A Claude Code agent conversation with its own ID, state, events, and result. Represents the agent's ongoing work and context. | Long-lived: `started` → `running` → `finished`/`error` | Persisted in Agent Runtime database |
| **Job** | A discrete command for the launcher to execute. Represents a single operation request. | Short-lived: `pending` → `running` → `completed`/`failed` | Transient (in-memory queue) |

**Relationship:**
- A Job triggers Session operations
- Job types: `start_session`, `resume_session`
- One Session may be acted upon by multiple Jobs over time (start once, resume many times)
- Jobs are consumed by the Launcher; Sessions are tracked by the Runtime

```
Job: "start_session"     →  Creates Session "task-1"
Job: "resume_session"    →  Resumes Session "task-1" (callback)
Job: "resume_session"    →  Resumes Session "task-1" (another callback)
```

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Agent Runtime (Docker) :8765                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │  Sessions API   │  │  Callbacks API  │  │     Launcher API        │  │
│  │  (existing)     │  │  (NEW)          │  │     (NEW)               │  │
│  └─────────────────┘  └─────────────────┘  └───────────┬─────────────┘  │
│                                                        │                 │
│  ┌─────────────────────────────────────────────────────┴───────────────┐│
│  │                        Job Queue                                     ││
│  │  - Pending jobs waiting for launcher                                 ││
│  │  - In-memory for POC (future: persistent)                           ││
│  └─────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP Long-polling
                                    │ (Launcher polls for jobs)
                                    │
┌───────────────────────────────────┴─────────────────────────────────────┐
│                    Agent Launcher (Host Machine)                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │  Registration   │  │   Job Poller    │  │    Job Executor         │  │
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

### Launcher Lifecycle

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
                  │ (get jobs)  │       │  (monitor   │       │  Thread     │
                  └──────┬──────┘       │  processes) │       └─────────────┘
                         │              └──────┬──────┘
                         │                     │
                         ▼                     ▼
                  ┌─────────────────────────────────────┐
                  │         Running Jobs Registry       │
                  │  job_id → { subprocess, status }    │
                  └─────────────────────────────────────┘
```

### Concurrent Execution Model

The launcher **must** support concurrent job execution. This is required because:

1. **Orchestrator scenario**: Dashboard starts an orchestrator (Job 1), which then starts child agents (Job 2, 3, ...). If the launcher could only run one job, the orchestrator would be blocked.

2. **Callback scenario**: Multiple child agents may complete while the orchestrator is waiting, triggering multiple resume jobs.

**Concurrency Design:**

| Component | Responsibility |
|-----------|----------------|
| **Poll Thread** | Continuously polls for new jobs, spawns subprocess for each |
| **Running Jobs Registry** | In-memory dict tracking `job_id → subprocess` |
| **Supervisor Thread** | Monitors subprocesses, detects completion/failure, reports status |
| **Heartbeat Thread** | Sends periodic heartbeats to Agent Runtime |

**Subprocess Management:**

```python
# Simplified model
running_jobs: Dict[str, subprocess.Popen] = {}

# Poll thread: spawn new job
proc = subprocess.Popen(["ao-start", ...], ...)
running_jobs[job_id] = proc
report_job_started(job_id)

# Supervisor thread: check completion
for job_id, proc in running_jobs.items():
    if proc.poll() is not None:  # Process finished
        if proc.returncode == 0:
            report_job_completed(job_id)
        else:
            report_job_failed(job_id, proc.stderr)
        del running_jobs[job_id]
```

**Max Concurrency (optional for POC):**

For POC, we can allow unlimited concurrent jobs (practical limit ~10-20 based on system resources). Future enhancement could add `max_concurrent_jobs` configuration.

## Protocol Design

### Registration Flow

On startup, the launcher registers with the Agent Runtime to receive a unique identifier.

```
Launcher                              Agent Runtime
   │                                       │
   │  POST /launcher/register              │
   │  { }                                  │
   │──────────────────────────────────────►│
   │                                       │
   │  200 OK                               │
   │  {                                    │
   │    "launcher_id": "lnch_abc123",      │
   │    "poll_endpoint": "/launcher/jobs", │
   │    "poll_timeout_seconds": 30         │
   │  }                                    │
   │◄──────────────────────────────────────│
   │                                       │
```

### Job Polling Flow (Long-polling)

The launcher continuously polls for jobs. The server holds the connection open until a job is available or timeout occurs.

```
Launcher                              Agent Runtime
   │                                       │
   │  GET /launcher/jobs?launcher_id=X     │
   │  (blocks up to 30 seconds)            │
   │──────────────────────────────────────►│
   │                                       │
   │         ... server waits ...          │
   │                                       │
   │  200 OK (job available)               │
   │  {                                    │
   │    "job": {                           │
   │      "job_id": "job_xyz789",          │
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
   │  204 No Content (timeout, no jobs)    │
   │◄──────────────────────────────────────│
   │                                       │
```

### Job Execution Flow

```
Launcher                              Agent Runtime
   │                                       │
   │  (receives job from poll)             │
   │                                       │
   │  POST /launcher/jobs/{job_id}/started │
   │  { "launcher_id": "lnch_abc123" }     │
   │──────────────────────────────────────►│
   │                                       │
   │  (executes ao-start/ao-resume)        │
   │  (subprocess runs...)                 │
   │                                       │
   │  POST /launcher/jobs/{job_id}/completed│
   │  {                                    │
   │    "launcher_id": "lnch_abc123",      │
   │    "status": "success"                │
   │  }                                    │
   │──────────────────────────────────────►│
   │                                       │
   │  OR (on failure)                      │
   │                                       │
   │  POST /launcher/jobs/{job_id}/failed  │
   │  {                                    │
   │    "launcher_id": "lnch_abc123",      │
   │    "error": "ao-start failed: ..."    │
   │  }                                    │
   │──────────────────────────────────────►│
   │                                       │
```

### Resume Job (For Callbacks)

When a child agent completes and triggers a callback, the Callback Processor creates a `resume_session` job.

```json
{
  "job_id": "job_callback_001",
  "type": "resume_session",
  "session_name": "orchestrator-main",
  "prompt": "## Agent Callback Notification\n\nAgent session `task-1` has completed with status: finished.\n\nTo retrieve the result: `ao-get-result task-1`"
}
```

The launcher executes:
```bash
ao-resume orchestrator-main -p "Child session completed..."
```

## API Specification

### Launcher API Endpoints (New in Agent Runtime)

#### POST /launcher/register

Register a new launcher instance.

**Request:** `{}` (empty body for anonymous registration)

**Response:**
```json
{
  "launcher_id": "lnch_abc123def",
  "poll_endpoint": "/launcher/jobs",
  "poll_timeout_seconds": 30,
  "heartbeat_interval_seconds": 60
}
```

#### GET /launcher/jobs

Long-poll for available jobs.

**Query Parameters:**
- `launcher_id` (required): The registered launcher ID

**Response (job available):** `200 OK`
```json
{
  "job": {
    "job_id": "job_xyz789",
    "type": "start_session",
    "session_name": "task-worker-1",
    "agent_name": "researcher",
    "prompt": "Research the topic...",
    "project_dir": "/Users/ramon/project"
  }
}
```

**Response (no jobs):** `204 No Content`

#### POST /launcher/jobs/{job_id}/started

Report job execution has started.

**Request:**
```json
{
  "launcher_id": "lnch_abc123"
}
```

**Response:** `200 OK`

#### POST /launcher/jobs/{job_id}/completed

Report job completed successfully.

**Request:**
```json
{
  "launcher_id": "lnch_abc123",
  "status": "success"
}
```

**Response:** `200 OK`

#### POST /launcher/jobs/{job_id}/failed

Report job execution failed.

**Request:**
```json
{
  "launcher_id": "lnch_abc123",
  "error": "Error message from subprocess"
}
```

**Response:** `200 OK`

#### POST /launcher/heartbeat

Keep launcher registration alive.

**Request:**
```json
{
  "launcher_id": "lnch_abc123"
}
```

**Response:** `200 OK`

### Job Creation Endpoints

#### POST /jobs

Create a new job (used by Dashboard, future ao-start).

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
  "job_id": "job_abc123",
  "status": "pending"
}
```

#### GET /jobs/{job_id}

Get job status.

**Response:**
```json
{
  "job_id": "job_abc123",
  "type": "start_session",
  "status": "completed",
  "created_at": "2025-01-15T10:00:00Z",
  "started_at": "2025-01-15T10:00:01Z",
  "completed_at": "2025-01-15T10:00:45Z"
}
```

## Job Types

| Type | Purpose | Parameters | Executed As |
|------|---------|------------|-------------|
| `start_session` | Start a new agent session | `session_name`, `agent_name`, `prompt`, `project_dir` | `ao-start` subprocess |
| `resume_session` | Resume an existing session | `session_name`, `prompt` | `ao-resume` subprocess |

**Note:** `resume_session` does not require `project_dir` - the `ao-resume` command fetches the original `project_dir` from the session API, ensuring consistency with the original session.

## Callback Flow

The Agent Launcher enables the following callback flow:

```
1. Launcher starts orchestrator with env var:
   AGENT_SESSION_NAME=orchestrator ao-start orchestrator -p "..."

2. Orchestrator starts child via ao-start:
   └─► ao-start reads AGENT_SESSION_NAME from env
   └─► Child session created with parent_session_name=orchestrator

3. Child agent completes (session_stop event)
   └─► Callback Processor detects completion
   └─► Checks: does child have parent_session_name? → Yes

4. Callback Processor checks: is parent idle?
   └─► Parent session status = "finished" → Yes, idle

5. Callback Processor creates resume job
   └─► Job queued: type=resume_session, session_name=orchestrator

6. Launcher polls and receives resume job
   └─► Executes: ao-resume orchestrator -p "Child session completed..."

7. Orchestrator resumes with callback notification
   └─► Can call ao-get-result to retrieve child's output
```

## Implementation Plan

### Phase 1: Launcher API in Agent Runtime

**Files to modify:** `servers/agent-runtime/`

1. **Add Job queue (in-memory, thread-safe)**
   - Use `threading.Lock` to protect concurrent access
   - Job states: `pending` → `claimed` → `running` → `completed`/`failed`
   - Atomic `claim_job()` operation marks job as `claimed` before returning
   - Multiple accessors: Poll endpoint, Dashboard POST, Callback Processor

2. **Add Launcher registry (in-memory)**
   - Track registered launchers by ID
   - Track last heartbeat time

3. **Implement endpoints:**
   - `POST /launcher/register`
   - `GET /launcher/jobs` (with long-polling)
   - `POST /launcher/jobs/{id}/started`
   - `POST /launcher/jobs/{id}/completed`
   - `POST /launcher/jobs/{id}/failed`
   - `POST /launcher/heartbeat`
   - `POST /jobs`
   - `GET /jobs/{id}`

### Phase 2: Agent Launcher Process

**New directory:** `servers/agent-launcher/`

1. **Create launcher CLI**
   - Python script that runs as a standalone process
   - Configuration via environment variables or CLI args

2. **Implement registration**
   - On startup, POST to /launcher/register
   - Store launcher_id for subsequent requests

3. **Implement Running Jobs Registry**
   - Thread-safe dict: `job_id → { process: Popen, started_at: datetime }`
   - Methods: `add_job()`, `remove_job()`, `get_running_jobs()`

4. **Implement Poll Thread**
   - Runs in background thread
   - Long-poll GET /launcher/jobs
   - Handle timeout (204) → retry immediately
   - Handle job → spawn subprocess, add to registry, report started

5. **Implement Supervisor Thread**
   - Runs in background thread
   - Periodically checks all running subprocesses (`proc.poll()`)
   - On completion: report completed/failed, remove from registry
   - Interval: ~1 second

6. **Implement Job Executor**
   - Map job type to subprocess command
   - `start_session` → `ao-start --name X --agent Y --prompt "Z"`
   - `resume_session` → `ao-resume --session X --message "Y"`
   - Use `subprocess.Popen()` for non-blocking execution
   - **Command Discovery**: Auto-discover `ao-*` commands relative to project root (same pattern as MCP server in `interfaces/agent-orchestrator-mcp-server/agent-orchestrator-mcp.py`). Don't use `AGENT_ORCHESTRATOR_COMMAND_PATH` env var for override.
   - **Logging**: Log job execution to stdout/stderr (concise, not verbose) for visibility during POC

7. **Implement Heartbeat Thread**
   - Background thread sending periodic heartbeats

### Phase 3: Dashboard Integration

**Files to modify:** `dashboard/`

1. **Update Chat tab**
   - Change from Agent Control API to new `/jobs` endpoint
   - Create job via `POST /jobs`
   - Rely on existing WebSocket connection for session updates (no job status polling)
   - IMPORTANT: Also liststen for session start events for the current sessean name in the websocket, as now the resume can autoamatically start the session again. 

2. **Remove Agent Control API dependency**
   - Remove `VITE_AGENT_CONTROL_API_URL` usage

### Phase 4: Parent Session Context (ao-* Commands & Sessions API)

**Files to modify:**
- `plugins/orchestrator/skills/orchestrator/commands/ao-start`
- `plugins/orchestrator/skills/orchestrator/commands/ao-resume`
- `plugins/orchestrator/skills/orchestrator/commands/lib/`
- `servers/agent-runtime/` (sessions API)

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

4. **Update Launcher executor**
   - Set `AGENT_SESSION_NAME={session_name}` when spawning subprocess
   - This propagates parent context to child agents

### Phase 5: Callback Integration

**Files to modify:** `servers/agent-runtime/`

1. **Implement Callback Processor**
   - Called directly from Sessions API when `session_stop` event is received (synchronous function call)
   - Maintains in-memory notification queue (dict keyed by parent session name)
   - Check if session has `parent_session_name`
   - Check parent session status (must be `finished` = idle)
   - If parent is idle: create resume_session job immediately
   - If parent is still running: add to notification queue
   - When parent's own `session_stop` event arrives: check queue and create aggregated resume job

2. **Wire into session events**
   - Sessions API calls Callback Processor directly on `session_stop` events
   - Generate resume message: "Child session X completed..."

## File Structure (Proposed)

```
├── servers/
│   ├── agent-runtime/
│   │   ├── routers/
│   │   │   ├── launcher.py          # NEW: Launcher API endpoints
│   │   │   ├── jobs.py              # NEW: Job management endpoints
│   │   │   └── ...
│   │   ├── services/
│   │   │   ├── job_queue.py         # NEW: In-memory job queue
│   │   │   ├── launcher_registry.py # NEW: Launcher tracking
│   │   │   ├── callback_processor.py # NEW: Callback logic
│   │   │   └── ...
│   │   └── models/
│   │       ├── job.py               # NEW: Job model
│   │       └── ...
│   └── agent-launcher/
│       ├── agent-launcher           # Main script (uv run --script)
│       └── lib/                     # Service modules
│           ├── __init__.py
│           ├── config.py            # Configuration
│           ├── registry.py          # Running Jobs Registry (thread-safe)
│           ├── poller.py            # Poll Thread - fetches jobs from runtime
│           ├── supervisor.py        # Supervisor Thread - monitors subprocesses
│           ├── executor.py          # Job execution (subprocess spawning)
│           └── api_client.py        # HTTP client for Agent Runtime API
```

### Agent Launcher Script Pattern

Following the same pattern as `ao-start` and `ao-resume`:

**Main script** (`agent-launcher`):
```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx",
#     "typer",
# ]
# ///
"""Agent Launcher - Connects to Agent Runtime and executes jobs."""

import sys
from pathlib import Path

# Add lib to path for service modules
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from config import LauncherConfig
from registry import RunningJobsRegistry
from poller import JobPoller
from supervisor import JobSupervisor
from api_client import RuntimeAPIClient

# ... main implementation
```

**Service modules** (`lib/*.py`) - plain Python files, no special headers needed.

**Benefits:**
- No installation required - `uv` handles dependencies automatically
- Run from any directory: `./servers/agent-launcher/agent-launcher`
- Modular code with clean separation of concerns
- Same pattern as existing ao-* commands

## Configuration

### Agent Launcher

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_RUNTIME_URL` | `http://localhost:8765` | Agent Runtime URL to connect to |
| `POLL_TIMEOUT` | `30` | Long-poll timeout in seconds |
| `HEARTBEAT_INTERVAL` | `60` | Heartbeat interval in seconds |
| `PROJECT_DIR` | cwd | Default project directory for ao-* commands |

### Agent Runtime

| Variable | Default | Description |
|----------|---------|-------------|
| `LAUNCHER_POLL_TIMEOUT` | `30` | How long to hold poll requests |
| `LAUNCHER_HEARTBEAT_TIMEOUT` | `120` | Mark launcher as dead after this |

## Migration Path

1. **Implement Launcher API** in Agent Runtime (no breaking changes)
2. **Create Agent Launcher** process
3. **Update Dashboard** to use `/jobs` endpoint
4. **Deprecate Agent Control API** - stop using/documenting
5. **Remove Agent Control API** - delete code from MCP server

## Success Criteria (POC)

- [ ] Launcher registers with Agent Runtime
- [ ] Dashboard can start sessions via `/jobs` endpoint
- [ ] Launcher executes `ao-start` and reports completion
- [ ] Launcher executes `ao-resume` and reports completion
- [ ] Callback flow works: child completes → orchestrator resumes
- [ ] Agent Control API can be disabled

## Future Enhancements (Post-POC)

1. **Multiple launchers** - Launcher selection, load balancing
2. **Persistent job queue** - SQLite storage for jobs
3. **Direct SDK integration** - Launcher uses Claude SDK directly
4. **ao-start via API** - Commands create jobs instead of running directly
5. **Launcher capabilities** - Different launchers for different agent types
6. **Authentication** - Secure launcher registration

## Known Limitations (POC)

The following are explicitly **out of scope** for the POC:

1. **Error handling** - No retry logic for failed callbacks, no handling of deleted parent sessions, no recovery from Launcher crashes mid-job

2. **Job failure notification to Dashboard** - If a job fails (e.g., `ao-start` errors), the Dashboard has no way to know. It creates a job and relies on WebSocket for session updates; if the session never starts, the Dashboard sees nothing. Future: broadcast job failures via WebSocket or have Dashboard poll job status briefly after creation.

3. **Callback strategies** - Only "immediate with aggregation" is implemented. No configurable strategies like "wait for all children" or "batch with delay".

4. **Parent session cleanup** - When a parent session is deleted while children are running or callbacks are pending, the callbacks will fail gracefully (Callback Processor logs an error). No automatic cleanup of pending notifications.

5. **Heartbeat timeout handling** - When a Launcher's heartbeat times out, it is marked as dead but orphaned jobs remain in their current state. No automatic job recovery or reassignment.

## Related Documents

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Overall system architecture
- [DATABASE_SCHEMA.md](../agent-runtime/DATABASE_SCHEMA.md) - Current database schema
