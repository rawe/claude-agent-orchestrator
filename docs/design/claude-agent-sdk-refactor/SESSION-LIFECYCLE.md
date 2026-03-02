# Session Lifecycle Reference

How sessions move through statuses, how stop and delete work end-to-end, and what each component owns.

---

## 1. Session Status Reference

Sessions have 7 statuses. Three are terminal (process exited, no further transitions).

| Status | Definition | Set By | Process Alive? | Accepts Turns? | Terminal? |
|-----------|-----------|--------|----------------|----------------|-----------|
| `pending` | Session created in coordinator, no executor bound yet | Coordinator (`create_session()`) | No | No | No |
| `running` | A turn is actively executing | Coordinator (on bind, on resume start) | Yes | No (busy) | No |
| `idle` | Turn completed, persistent process waiting for next turn | Runner (via `report_completed` with `session_status="idle"`) | Yes | **Yes** | No |
| `stopping` | Stop command issued, awaiting process termination | Coordinator (on stop request) | Yes (terminating) | No | No |
| `finished` | Session completed naturally | Runner (via `report_completed` or `report_session_status`) | No | No | **Yes** |
| `stopped` | Session force-terminated by stop command | Runner (via `report_stopped` or `report_session_status`) | No | No | **Yes** |
| `failed` | Process crashed or exited with non-zero code | Runner (via `report_failed` or `report_session_status`) | No | No | **Yes** |

### Lifecycle mode differences

| Behavior | One-Shot | Persistent |
|----------|----------|------------|
| Turn completion signal | Process exits with code 0 | `{"type": "turn_complete"}` on stdout |
| Status after turn | `finished` (terminal) | `idle` (non-terminal) |
| Resume possible? | No (process exited) | Yes (process alive, write to stdin) |
| Uses `idle` status? | No | Yes |
| Process exit while idle | N/A | `finished` (exit 0) or `failed` (non-zero) |

---

## 2. Status Transition State Machine

```
                        +----------+
                        | pending  |
                        +----+-----+
                             | executor binds (report_started)
                             v
                        +----------+
              +---------| running  |<-----------+
              |         +--+----+--+            |
              |            |    |               | resume turn dispatched
              |            |    |               | (swap_run + send_turn)
              | stop       |    |          +----+-----+
              | issued     |    |          |   idle   | (persistent only)
              |            |    |          +----+-----+
              v            |    |               |
        +----------+       |    |               | stop issued
        | stopping |       |    |               v
        +----+-----+       |    |         +----------+
             |             |    |         | stopping  | (from idle)
             | confirmed   |    |         +----+------+
             v             |    |              |
        +----------+       |    |              |
        | stopped  |<------+    |              |
        +----------+  crash     |              |
                      while     |              |
                      stopping  |              |
                                |              |
             turn_complete------+              |
             (persistent)       |              |
                   |            |              |
                   v            v              v
             +----------+ +----------+   +----------+
             |   idle   | | finished |   |  stopped |
             +----------+ +----------+   +----------+
                               ^
                               |
               process_exit----+
               (one-shot: exit 0)
               (persistent: clean shutdown from idle)

        +----------+
        |  failed  |  <-- process crash (non-zero exit) from running or idle
        +----------+
```

### Valid transitions

| From | To | Trigger | Component |
|------|----|---------|-----------|
| `pending` | `running` | `report_run_started()` (executor binds and first run starts) | Coordinator |
| `running` | `idle` | `turn_complete` on stdout (persistent executor) | Runner supervisor -> Coordinator |
| `running` | `finished` | Process exit code 0 (one-shot executor) | Runner supervisor -> Coordinator |
| `running` | `failed` | Process exit non-zero, or `report_failed()` | Runner supervisor -> Coordinator |
| `running` | `stopping` | Stop command issued (`POST /sessions/{id}/stop`) | Coordinator |
| `running` | `stopped` | Process crash while in `stopping` | Runner supervisor -> Coordinator |
| `idle` | `running` | Resume turn dispatched (`report_run_started()` detects idle) | Coordinator |
| `idle` | `stopping` | Stop command issued while idle | Coordinator |
| `idle` | `finished` | Clean shutdown (graceful NDJSON shutdown, exit 0) | Runner -> Coordinator |
| `idle` | `failed` | Process crash while idle (non-zero exit) | Runner supervisor -> Coordinator |
| `stopping` | `stopped` | Runner confirms stop (`report_stopped()` or `report_session_status()`) | Runner -> Coordinator |
| `stopping` | `finished` | Graceful shutdown succeeded (idle session, `shutdown` signal, exit 0) | Runner -> Coordinator |

### Terminal states

`finished`, `stopped`, and `failed` are terminal. No transitions out. The session can only be deleted.

---

## 3. End-to-End Request Flows

### 3.1 Starting a new session

```
Dashboard/Client                  Coordinator                      Runner
     |                                |                               |
     |-- POST /runs                   |                               |
     |   {type: "start_session",      |                               |
     |    parameters: {prompt: "..."}} |                               |
     |                                |                               |
     |                                |-- create_session() -> pending  |
     |                                |-- create Run (PENDING)         |
     |                                |-- SSE: session_created         |
     |                                |                               |
     |<-- {run_id, session_id} -------|                               |
     |                                |                               |
     |                                |<-- GET /runner/runs (poll) ----|
     |                                |-- claim run, run hooks         |
     |                                |-- return {run: ...} ---------->|
     |                                |                               |
     |                                |   executor.execute_run(run)    |
     |                                |   -> subprocess.Popen          |
     |                                |   registry.register_session()  |
     |                                |   start_stdout_reader() (if persistent)
     |                                |                               |
     |                                |<-- POST /runs/{id}/started ---|
     |                                |                               |
     |                                |-- run.status = RUNNING         |
     |                                |-- session.status = running     |
     |                                |-- SSE: run_start event         |
     |                                |                               |
```

**Result**: Session goes `pending` -> `running`. Process is alive and executing.

### 3.2 Resuming an idle session

Applies only to persistent executors where the session is `idle` (turn completed, process alive).

```
Dashboard/Client                  Coordinator                      Runner
     |                                |                               |
     |-- POST /runs                   |                               |
     |   {type: "resume_session",     |                               |
     |    session_id: "ses_xxx",      |                               |
     |    parameters: {prompt: "..."}} |                               |
     |                                |                               |
     |                                |-- create Run (PENDING)         |
     |<-- {run_id, session_id} -------|                               |
     |                                |                               |
     |                                |<-- GET /runner/runs (poll) ----|
     |                                |-- return {run: ...} ---------->|
     |                                |                               |
     |                                |   _route_resume():             |
     |                                |   registry.swap_run(ses, run)  |
     |                                |   executor.send_turn(process, run)
     |                                |   -> writes NDJSON to stdin    |
     |                                |                               |
     |                                |<-- POST /runs/{id}/started ---|
     |                                |                               |
     |                                |-- run.status = RUNNING         |
     |                                |-- session: idle -> running     |
     |                                |-- SSE: run_start event         |
     |                                |                               |
     |                                |   ... executor works ...       |
     |                                |                               |
     |                                |   stdout: {"type":"turn_complete"}
     |                                |   supervisor._report_turn_complete()
     |                                |   registry.clear_run()         |
     |                                |                               |
     |                                |<-- POST /runs/{id}/completed  |
     |                                |    {session_status: "idle"}    |
     |                                |                               |
     |                                |-- run.status = COMPLETED       |
     |                                |-- session: running -> idle     |
     |                                |-- SSE: run_completed event     |
```

**Result**: Session goes `idle` -> `running` -> `idle`. Process stays alive.

### 3.3 Stopping a running session (force-kill)

Session has an active run and a live process. Stop force-terminates.

```
Dashboard                         Coordinator                      Runner
     |                                |                               |
     |-- POST /sessions/{id}/stop --->|                               |
     |                                |                               |
     |                                |-- get_run_by_session_id()      |
     |                                |-- run.status = STOPPING        |
     |                                |-- session.status = stopping    |
     |                                |-- stop_command_queue.add_stop  |
     |                                |     (runner_id, session_id)    |
     |                                |-- SSE: session_updated         |
     |                                |                               |
     |<-- {ok, status: "stopping"} ---|                               |
     |                                |                               |
     |                                |<-- GET /runner/runs (poll) ----|
     |                                |-- {"stop_sessions":["ses_xxx"]}|
     |                                |                        ------>|
     |                                |                               |
     |                                |   _handle_stop(session_id):    |
     |                                |   registry.mark_stopping()     |
     |                                |   process.terminate() (SIGTERM)|
     |                                |   process.wait(5s)             |
     |                                |   [if timeout: process.kill()] |
     |                                |   registry.remove_session()    |
     |                                |                               |
     |                                |<-- POST /runs/{id}/stopped ---|
     |                                |    {signal: "SIGTERM"}         |
     |                                |                               |
     |                                |-- run.status = STOPPED         |
     |                                |-- session.status = stopped     |
     |                                |-- SSE: session_updated         |
```

**Result**: Session goes `running` -> `stopping` -> `stopped`. Process killed.

### 3.4 Stopping an idle session (graceful shutdown)

Session is `idle` (between turns). Stop sends NDJSON `{"type":"shutdown"}` first for graceful exit.

```
Dashboard                         Coordinator                      Runner
     |                                |                               |
     |-- POST /sessions/{id}/stop --->|                               |
     |                                |                               |
     |                                |-- session.status == "idle"     |
     |                                |-- get_run_by_session_id()      |
     |                                |     -> last run (for runner_id)|
     |                                |-- stop_command_queue.add_stop  |
     |                                |     (runner_id, session_id)    |
     |                                |-- session.status = stopping    |
     |                                |-- SSE: session_updated         |
     |                                |                               |
     |<-- {ok, status: "stopping"} ---|                               |
     |                                |                               |
     |                                |<-- GET /runner/runs (poll) ----|
     |                                |-- {"stop_sessions":["ses_xxx"]}|
     |                                |                        ------>|
     |                                |                               |
     |                                |   _handle_stop(session_id):    |
     |                                |   registry.mark_stopping()     |
     |                                |   entry.persistent == true     |
     |                                |   executor.send_shutdown()     |
     |                                |     -> stdin: {"type":"shutdown"}
     |                                |   process.wait(5s) -> exits 0  |
     |                                |   signal_used = "shutdown"     |
     |                                |   registry.remove_session()    |
     |                                |                               |
     |                                |   run_id is None (idle)        |
     |                                |   end_status = "finished"      |
     |                                |                               |
     |                                |<-- POST /runner/sessions/      |
     |                                |    {id}/status                 |
     |                                |    {status: "finished"}  ------|
     |                                |                               |
     |                                |-- session.status = finished    |
     |                                |-- SSE: session_updated         |
```

**Result**: Session goes `idle` -> `stopping` -> `finished`. Process exits cleanly.

If graceful shutdown times out, the runner falls through to SIGTERM/SIGKILL and reports `stopped` instead.

### 3.5 Deleting a session

Delete is only allowed for terminal sessions (`finished`, `stopped`, `failed`, `pending`, `stopping`). Running and idle sessions must be stopped first.

```
Dashboard                         Coordinator
     |                                |
     |-- DELETE /sessions/{id} ------>|
     |                                |
     |                                |-- get_session_by_id()
     |                                |-- status in ("running","idle")?
     |                                |     -> 409 Conflict: "Stop session first"
     |                                |
     |                                |-- delete_session() (cascade: runs, events)
     |                                |-- run_queue.remove_runs_for_session()
     |                                |-- SSE: session_deleted
     |                                |
     |<-- {ok, deleted: {counts}} ----|
```

**Dashboard safety**: The Delete button is disabled (grayed out) for `running`, `idle`, and `stopping` sessions. The tooltip shows "Stop session first" for running/idle and "Session is stopping" for stopping. This prevents accidental deletion of live sessions.

**Dashboard stop confirmation**: The stop confirmation dialog is context-aware:
- Running sessions: "Stop this running session? The agent will be force-terminated."
- Idle sessions: "End this session? The agent will shut down gracefully."

---

## 4. Component Responsibilities

### Dashboard (`apps/dashboard/`)

| Responsibility | Files |
|---------------|-------|
| Display all 7 session statuses with color-coded badges | `SessionCard.tsx` (accent colors), `StatusBadge` component |
| Show Stop button for `running` and `idle` sessions | `SessionCard.tsx:126` |
| Disable Delete button for `running`, `idle`, and `stopping` sessions | `SessionCard.tsx:139-164` |
| Context-aware stop confirmation messaging | `AgentSessions.tsx:183-186` |
| Track `isRunning` as `running` OR `idle` for event timeline auto-scroll | `AgentSessions.tsx:148` |
| Update session list via SSE (`session_created`, `session_updated`, `session_deleted`) | `SessionsContext.tsx` |

### Chat UI (`apps/chat-ui/`)

| Responsibility | Files |
|---------------|-------|
| Map session statuses to UI agent statuses | `ChatContext.tsx:320-327` |
| Enable user input when session is `idle` (ready for resume) | `ChatContext.tsx:460-461` |
| Send `stopSession()` on stop button click | `ChatContext.tsx:471-481` |
| SSE status mapping: `idle` -> `idle`, `stopping` -> `stopping`, `stopped`/`finished` -> `finished` | `ChatContext.tsx:320-327` |

### Coordinator (`servers/agent-coordinator/`)

| Responsibility | Files |
|---------------|-------|
| Create sessions with `pending` status | `database.py:create_session()` |
| Transition `pending` -> `running` on executor bind | `main.py:report_run_started()` |
| Transition `idle` -> `running` on resume turn start | `main.py:1582-1583` |
| Accept `session_status` from runner in completion report | `main.py:report_run_completed()` |
| Set session `failed` on run failure | `main.py:report_run_failed()` |
| Set session `stopped` on run stopped | `main.py:report_run_stopped()` |
| Accept session-level status updates (idle process exit) | `main.py:report_session_status()` |
| Handle stop for running sessions (queue stop command) | `main.py:_stop_run()` |
| Handle stop for idle sessions (queue stop command) | `main.py:stop_session()` lines 525-536 |
| Reject delete for running/idle sessions with 409 | `main.py:delete_session_endpoint()` |
| Broadcast all status changes via SSE | `main.py:update_session_status_and_broadcast()` |
| Route stop commands through `stop_command_queue` using `session_id` | `services/stop_command_queue.py` |

### Runner (`servers/agent-runner/`)

| Responsibility | Files |
|---------------|-------|
| Spawn executor processes and register in session registry | `executor.py`, `poller.py:_handle_run()` |
| Route resume turns to existing persistent processes | `poller.py:_route_resume()` |
| Report `session_status="idle"` on persistent turn completion | `supervisor.py:_report_turn_complete()` |
| Report `session_status="finished"` on one-shot completion | `supervisor.py:_handle_oneshot_exit()` |
| Handle idle process exit (finished/failed) | `supervisor.py:_handle_persistent_exit()` |
| Handle stop commands by session_id | `poller.py:_handle_stop()` |
| Graceful shutdown for persistent processes (NDJSON `{"type":"shutdown"}`) | `poller.py:_handle_stop()`, `executor.py:send_shutdown()` |
| Escalate to SIGTERM/SIGKILL on shutdown timeout | `poller.py:_handle_stop()` |
| Report smart stop status (finished for graceful, stopped for force) | `poller.py:_handle_stop()` lines 261-264 |
| Dedup guard between poller stop and supervisor exit detection | `registry.py:mark_stopping()/is_stopping()`, `supervisor.py:176` |
| Track run-to-session mapping with dual-indexed registry | `registry.py:ProcessRegistry` |

### Executor (`servers/agent-runner/executors/`)

| Responsibility | Files |
|---------------|-------|
| Run Claude SDK sessions | `claude-sdk-executor/lib/sdk_client.py` |
| Emit `{"type":"turn_complete"}` on stdout when turn finishes | `sdk_client.py` |
| Accept `{"type":"shutdown"}` on stdin for graceful exit | `sdk_client.py` |
| Accept `{"type":"turn", "parameters": {...}}` on stdin for resume turns | `sdk_client.py` |
| Report session events (messages, tool calls, results) to coordinator HTTP API | `sdk_client.py` |

The executor is status-unaware. It does not know about session statuses -- that is entirely a coordinator/runner concern. It only knows `session_id`.

---

## 5. Key Implementation Details

### Stop command routing uses session_id

The stop command queue and poll protocol use `session_id` (not `run_id`). This is because multi-turn sessions may be between turns (no active run_id). The poll response field is `stop_sessions`.

### Dedup guard for poller vs supervisor

When the poller handles a stop command, it calls `registry.mark_stopping(session_id)`. The supervisor's `_handle_persistent_exit()` checks `registry.is_stopping(session_id)` and skips exit handling if true. This prevents double-reporting when both the poller (stop handler) and supervisor (process poll) detect the same process exit.

### Smart stop status for idle sessions

When an idle session is stopped:
- If graceful shutdown succeeds (`signal_used == "shutdown"`): report `finished`
- If force-kill required (`SIGTERM`/`SIGKILL`): report `stopped`

This is reported via `POST /runner/sessions/{session_id}/status` since there is no active run_id.

### NDJSON protocol (runner <-> executor)

The protocol is session-pure. The executor knows only `session_id`. The runner maps `turn_complete` messages to the active `run_id` via its registry.

| Direction | Message | Purpose |
|-----------|---------|---------|
| stdin (line 1) | `{schema_version, mode, session_id, parameters}` | Initial invocation |
| stdin (subsequent) | `{"type": "turn", "parameters": {...}}` | Resume turn |
| stdin | `{"type": "shutdown"}` | Graceful shutdown request |
| stdout | `{"type": "turn_complete", "result": "..."}` | Turn finished |
