# Agent Callback Architecture Overview

## Summary

The Agent Orchestrator framework enables hierarchical multi-agent coordination through a callback-based asynchronous execution model. Parent agents can spawn child agents and receive automatic notifications when children complete, eliminating the need for polling.

---

## Core Components

### 1. Agent Runtime

**Responsibility:** Central coordination service that manages sessions, jobs, and callbacks.

**Key Capabilities:**
- Session lifecycle management (create, update, query, delete)
- Job queue for asynchronous command execution
- Launcher registration and health tracking
- Callback processing when child sessions complete
- Parent-child session relationship tracking

**API Endpoints:**

| Category | Endpoints |
|----------|-----------|
| Sessions | `POST /sessions`, `GET /sessions`, `GET /sessions/{id}`, `DELETE /sessions/{id}` |
| Jobs | `POST /jobs`, `GET /jobs/{job_id}` |
| Launcher | `POST /launcher/register`, `GET /launcher/jobs`, `POST /launcher/heartbeat` |
| Launchers Management | `GET /launchers`, `DELETE /launchers/{id}` |

**Interactions:**
- Receives job creation requests from MCP Server or Dashboard
- Provides jobs to Agent Launcher via long-polling
- Updates session state based on events from ao-start/ao-resume
- Triggers callbacks when child sessions complete

---

### 2. Agent Launcher

**Responsibility:** Executes jobs by spawning Claude Code (ao-start/ao-resume) as subprocesses.

**Key Capabilities:**
- Registers with Agent Runtime on startup
- Long-polls for pending jobs
- Executes multiple jobs concurrently
- Reports job status (started, completed, failed)
- Maintains heartbeat for health monitoring
- Sets `AGENT_SESSION_NAME` environment variable for session identity
- Auto-exits after 3 consecutive connection failures to Agent Runtime

**Lifecycle:**
```
Startup → Register → Main Loop
                        │
           ┌────────────┼────────────┐
           ▼            ▼            ▼
      Poll Thread   Supervisor   Heartbeat
      (get jobs)    (monitor)    Thread
           │            │
           ▼            ▼
      Running Jobs Registry
```

**Interactions:**
- Polls Agent Runtime for jobs (`GET /launcher/jobs`)
- Spawns ao-start/ao-resume subprocesses
- Reports job status back to Agent Runtime
- Receives deregistration signals (from dashboard or connection failures)

---

### 3. MCP Server

**Responsibility:** Provides MCP tools for Claude Code agents to interact with the orchestration framework.

**Key Capabilities:**
- Exposes agent orchestration as MCP tools
- Calls Agent Runtime Jobs API (not subprocess spawning)
- Extracts parent session context from HTTP headers or environment
- Supports synchronous and asynchronous execution modes
- Enables callback opt-in via `callback=true` parameter

**MCP Tools:**

| Tool | Description |
|------|-------------|
| `start_agent_session` | Start a new agent session |
| `resume_agent_session` | Resume an existing session |
| `get_agent_session_status` | Check session status |
| `get_agent_session_result` | Retrieve session output |
| `list_agent_sessions` | List all sessions |
| `list_agent_blueprints` | List available agent types |
| `delete_all_agent_sessions` | Clean up all sessions |

**Interactions:**
- Receives tool calls from Claude Code agents
- Creates jobs via `POST /jobs` on Agent Runtime
- Polls for completion (sync mode) or returns immediately (async mode)
- Passes `parent_session_name` when `callback=true`

---

### 4. ao-start / ao-resume Commands

**Responsibility:** Execute Claude Code sessions using the Claude Agent SDK.

**Key Capabilities:**
- Start new agent sessions with specified prompts
- Resume existing sessions with new messages
- Register sessions with Agent Runtime
- Stream events to Agent Runtime during execution
- Read `AGENT_SESSION_NAME` from environment for identity

**Interactions:**
- Spawned by Agent Launcher with environment variables
- Call Agent Runtime Sessions API to register/update sessions
- Use Claude Agent SDK for actual execution
- Report session events (start, stop, result)

---

### 5. Dashboard

**Responsibility:** Web UI for monitoring and controlling agent sessions.

**Key Capabilities:**
- View all active sessions with real-time updates
- Start new sessions via Chat interface
- View session hierarchy (parent-child relationships)
- Manage agent launchers (view status, deregister)
- Real-time updates via WebSocket

**Interactions:**
- Creates jobs via `POST /jobs` endpoint
- Receives session updates via WebSocket
- Lists launchers via `GET /launchers`
- Deregisters launchers via `DELETE /launchers/{id}`

---

### 6. Callback Processor

**Responsibility:** Detects child session completion and triggers parent resume.

**Key Capabilities:**
- Listens for `session_stop` events
- Checks if completed session has a parent
- Creates resume job for parent when parent is idle
- Queues notifications when parent is busy
- Delivers aggregated callbacks when parent stops

**Callback Flow:**
```
Child completes
      │
      ▼
Check parent status
      │
  ┌───┴───┐
  ▼       ▼
IDLE    BUSY
  │       │
  │    Queue notification
  │       │
Create    └──► Parent stops
resume         │
job            ▼
  │       Flush queue
  └───────► Create resume job
               │
               ▼
         Parent resumes
         with notification
```

**Interactions:**
- Called by Sessions API on `session_stop` events
- Creates jobs in Job Queue
- Maintains in-memory notification queue for busy parents

---

## Data Flow

### Starting a Session (via Dashboard)

```
Dashboard                 Agent Runtime             Agent Launcher
    │                          │                          │
    │ POST /jobs              │                          │
    │ (start_session)         │                          │
    │─────────────────────────►│                          │
    │                          │ Job added to queue       │
    │                          │                          │
    │                          │◄─────────────────────────│
    │                          │   GET /launcher/jobs     │
    │                          │                          │
    │                          │ Return job               │
    │                          │─────────────────────────►│
    │                          │                          │
    │                          │   POST .../started       │ spawns
    │                          │◄─────────────────────────│ ao-start
    │                          │                          │
    │        WebSocket         │                          │
    │◄─ ─ ─ (session_start) ─ ─│                          │
    │                          │                          │
```

### Callback Flow (Child Completion)

```
Child Session              Agent Runtime             Parent Session
     │                          │                          │
     │ session_stop event       │                          │
     │─────────────────────────►│                          │
     │                          │                          │
     │                          │ Callback Processor       │
     │                          │ checks parent status     │
     │                          │                          │
     │                          │ Creates resume_session   │
     │                          │ job for parent           │
     │                          │                          │
     │                          │         (via Launcher)   │
     │                          │─────────────────────────►│
     │                          │                          │
     │                          │         Resumes with     │
     │                          │         notification     │
```

---

## Agent Launcher Lifecycle

### Registration

1. Launcher starts and calls `POST /launcher/register`
2. Agent Runtime returns `launcher_id` and configuration
3. Launcher begins polling, heartbeat, and supervisor threads

### Deregistration

**Self-Initiated (Graceful Shutdown):**
```
SIGINT/SIGTERM received
       │
       ▼
stop() called
       │
       ▼
DELETE /launchers/{id}?self=true
       │
       ▼
Immediate removal from registry
       │
       ▼
Launcher exits
```

**External (Dashboard):**
```
Dashboard: DELETE /launchers/{id}
       │
       ▼
Agent Runtime marks launcher for deregistration
       │
       ▼
Launcher's next poll receives {"deregistered": true}
       │
       ▼
on_deregistered callback triggered
       │
       ▼
Launcher shuts down
```

**Connection Failure (Runtime Unreachable):**
```
Poll fails (connection error)
       │
       ▼
consecutive_failures++
       │
       ▼
If failures >= 3:
       │
       ▼
on_deregistered callback triggered
       │
       ▼
Launcher exits
```

### Launcher Status

| Status | Description |
|--------|-------------|
| `online` | Heartbeat within last 2 minutes |
| `stale` | No heartbeat for 2+ minutes |
| `shutting down` | Deregistration in progress (dashboard view) |

---

## Parent-Child Session Tracking

### Context Propagation

1. **Agent Launcher** sets `AGENT_SESSION_NAME={session_name}` when spawning sessions
2. **Claude Code** replaces `${AGENT_SESSION_NAME}` placeholder in MCP config headers
3. **MCP Server** extracts `X-Agent-Session-Name` header
4. **Jobs API** receives `parent_session_name` when `callback=true`
5. **Agent Runtime** links child session to parent in database

### Callback Opt-In

Callbacks require explicit opt-in via the `callback=true` parameter:

| Mode | Callback | Behavior |
|------|----------|----------|
| `async_mode=false` | N/A | Synchronous (blocking) |
| `async_mode=true` | `false` | Fire-and-forget, manual polling |
| `async_mode=true` | `true` | Automatic callback on completion |

---

## Job Types

| Type | Command | Parameters |
|------|---------|------------|
| `start_session` | ao-start | session_name, agent_name, prompt, project_dir, parent_session_name |
| `resume_session` | ao-resume | session_name, prompt, parent_session_name |

---

## Configuration

### Agent Runtime

| Variable | Default | Description |
|----------|---------|-------------|
| `LAUNCHER_POLL_TIMEOUT` | 30s | Long-poll timeout |
| `LAUNCHER_HEARTBEAT_TIMEOUT` | 120s | Launcher marked stale after this |

### Agent Launcher

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_ORCHESTRATOR_API_URL` | `http://localhost:8765` | Runtime API URL |
| `POLL_TIMEOUT` | 30s | Long-poll timeout |
| `HEARTBEAT_INTERVAL` | 60s | Heartbeat frequency |
| `PROJECT_DIR` | cwd | Default project directory |

### MCP Server

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_ORCHESTRATOR_API_URL` | `http://127.0.0.1:8765` | Runtime API URL |
| `AGENT_SESSION_NAME` | (none) | Parent session name (stdio mode) |

---

## Key Design Decisions

1. **Callback via Job Queue**: Parent resume is implemented as a new job, ensuring the Launcher controls all Claude Code execution.

2. **In-Memory State**: Job queue and callback notification queue are in-memory (acceptable for POC; lost on restart).

3. **Long-Polling**: Agent Launcher uses long-polling (not WebSocket) for simplicity and HTTP compatibility.

4. **Opt-In Callbacks**: Callbacks require explicit `callback=true` to maintain backward compatibility with fire-and-forget async.

5. **Centralized Coordination**: Agent Runtime is the single source of truth for session state and callback orchestration.

6. **Retry with Limit**: Agent Launcher exits after 3 consecutive connection failures rather than retrying indefinitely.

---

## Constraints

- Callbacks only work when the parent agent is started via the Agent Orchestrator framework (Dashboard or Jobs API)
- Direct Claude CLI or Claude Desktop usage cannot receive callbacks
- In-memory queues are lost on Agent Runtime restart
- Single launcher per host (multi-launcher support is future work)
