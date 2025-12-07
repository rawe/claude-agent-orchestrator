# ADR-002: Agent Callback Architecture

## Status

**Superseded** - This document has been superseded by the POC implementation specification.

> **Note:** The implementation specification for the POC is now located at:
> [`docs/features/agent-callback-architecture.md`](../features/agent-callback-architecture.md)
>
> This ADR is retained for reference as it contains additional design considerations
> (callback strategies, detailed state machines, database schemas) that may be relevant
> for future iterations beyond the POC. However, **do not use this document for
> implementing the current POC** - refer to the feature spec instead.

---

## Original Document (Archived)

*The content below represents the original architectural exploration and is kept for historical reference.*

### Original Status

**Draft** - Architectural Design Document

## Context

### Current Agent Execution Patterns

The Agent Orchestrator framework currently supports two patterns for spawning and managing child agents:

| Pattern | Description | Orchestrator Behavior | Result Retrieval |
|---------|-------------|----------------------|------------------|
| **Synchronous** | Blocking execution | Waits for completion | Immediate return |
| **Async (Polling)** | Fire-and-forget with status checks | Continues working, polls periodically | `ao-status` + `ao-get-result` |

**Synchronous Pattern** (`ao-start --wait`):
```
Orchestrator ──start──► Child Agent ──runs──► completes
    │                                            │
    └────────────── blocked ─────────────────────┘
                                                 │
                                          returns result
```

**Async Polling Pattern** (`ao-start --async`):
```
Orchestrator ──start──► Child Agent ──runs──► completes
    │                       │                    │
    │◄──returns immediately─┘                    │
    │                                            │
    ├──continues work──►                         │
    │                                            │
    ├──poll status────────────────────────►check─┤
    │◄──"running"─────────────────────────────────┘
    │
    ├──poll status────────────────────────►check─┤
    │◄──"finished"────────────────────────────────┘
    │
    └──get result───────────────────────────────►
```

### Problem Statement

Both patterns have limitations in orchestration scenarios:

1. **Synchronous**: Orchestrator is blocked and cannot perform other work or spawn additional agents in parallel.

2. **Polling**:
   - Orchestrator must actively poll, consuming compute time
   - Polling interval creates a tradeoff between latency and resource usage
   - Orchestrator cannot truly "idle" - it must remain active to poll
   - Complex multi-agent coordination requires tracking multiple sessions

### Proposed Solution: Callback-Based Async

A third pattern where the **spawned agent notifies the orchestrator upon completion**, rather than the orchestrator polling:

```
Orchestrator ──start (callback)──► Child Agent ──runs──► completes
    │                                  │                    │
    │◄──returns immediately────────────┘                    │
    │                                                       │
    ├──continues work──►                                    │
    │                                                       │
    └──becomes idle (session ends)                          │
                                                            │
                        ┌───────────────────────────────────┘
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

### Applicability Constraint

**Callbacks only work when the parent (orchestrator) is started and controlled by the Agent Orchestrator framework.**

| Parent Started By | Callbacks Work? | Reason |
|-------------------|-----------------|--------|
| Dashboard → Job API → Launcher | ✅ Yes | Framework can resume parent |
| User runs `claude` CLI directly | ❌ No | No external resume hook |
| Claude Desktop | ❌ No | No external resume hook |

The callback mechanism requires the ability to resume the parent session via the Agent Launcher. External agents (CLI, Desktop) have no API for resume injection.

See [ADR-003](./ADR-003-AGENT-LAUNCHER-POC.md) for implementation details.

## Motivation

### Why Callback-Based Async?

1. **Resource Efficiency**: Orchestrator can fully idle without consuming resources for polling loops.

2. **Natural Multi-Agent Coordination**: Multiple child agents can run in parallel, and the orchestrator gets notified when each (or all) complete.

3. **Transparent to Child Agents**: The callback mechanism is handled by the session management layer - child agents don't know they're being observed.

4. **Scalable Orchestration**: Enables patterns like:
   - Fork/join parallelism
   - Event-driven workflows
   - Hierarchical agent coordination

5. **Better User Experience**: The orchestrator "wakes up" naturally when work is ready, rather than busy-waiting.

### Use Cases

1. **Parallel Task Execution**: Orchestrator spawns 5 agents for independent tasks, idles, then resumes when all complete to aggregate results.

2. **Pipeline Patterns**: Agent A completes → triggers Agent B → triggers Agent C → orchestrator resumes with final result.

3. **Long-Running Tasks**: Child agent runs a 30-minute build/test cycle; orchestrator doesn't need to poll every minute.

## Challenges

### 1. Parent-Child Relationship Tracking

**Challenge**: When an agent is started, we need to know who started it (the orchestrator's session).

**Considerations**:
- The Claude SDK generates session IDs internally
- The orchestrator may spawn multiple children
- Children might spawn their own children (grandchildren)
- We need to differentiate between callback and non-callback spawns

### 2. Detecting Orchestrator "Idle" State

**Challenge**: Determining when the orchestrator has finished its current conversation turn and is ready to receive callbacks.

**Considerations**:
- An orchestrator session ending could mean:
  - Completed all work (truly idle - waiting for callback)
  - Finished the task entirely (no callback needed)
  - Errored out (callback may not be useful)
- The `session_stop` event signals end of a conversation turn
- Need to distinguish "idle and waiting" from "done forever"

### 3. Multiple Child Completion Aggregation

**Challenge**: Multiple children might complete while orchestrator is idle. Should we:
- Resume immediately on first completion?
- Wait for all children to complete?
- Aggregate notifications into a single message?

**Considerations**:
- Different orchestration patterns need different strategies
- Immediate notification enables reactive patterns
- Batched notification reduces context switches
- Could be configurable per-spawn

### 4. Agent Launcher Dependency

**Challenge**: Resuming an orchestrator session requires executing `ao-resume`, which needs the Agent Launcher infrastructure.

**Considerations**:
- Current architecture has Agent Control API as temporary solution
- Agent Launcher model (GitLab Runner-style) is planned
- Callback system requires Agent Launcher for:
  - Receiving "resume" commands from Agent Runtime
  - Executing resume on the correct host/environment

### 5. Failure Handling

**Challenge**: What happens if:
- Child agent errors/crashes
- Orchestrator session is deleted before child completes
- Agent Launcher is unavailable when callback is triggered
- Resume fails

## Architectural Design

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Agent Runtime                                  │
│  ┌────────────────┐   ┌────────────────┐   ┌────────────────────────┐│
│  │    Sessions    │   │   Callbacks    │   │   Callback Processor   ││
│  │    Store       │   │   Registry     │   │                        ││
│  │                │   │                │   │  - Monitors completions ││
│  │  session_id ───┼───┼─► parent_id    │   │  - Checks parent state  ││
│  │  status        │   │   child_ids[]  │   │  - Triggers resumption  ││
│  │  ...           │   │   strategy     │   │  - Aggregates messages  ││
│  └────────────────┘   └────────────────┘   └───────────┬────────────┘│
│                                                        │              │
└────────────────────────────────────────────────────────┼──────────────┘
                                                         │
                            Resume Request               │
                            (session_id, message)        │
                                                         ▼
                                            ┌────────────────────────┐
                                            │    Agent Launcher      │
                                            │                        │
                                            │  - Receives requests   │
                                            │  - Executes ao-resume  │
                                            │  - Reports status      │
                                            └────────────────────────┘
```

### Component Responsibilities

#### 1. Callback Registry (New)

Stores parent-child relationships and callback configuration.

**Responsibilities**:
- Track which session spawned which children
- Store callback strategy (immediate, batch, all-complete)
- Maintain pending callback state

#### 2. Callback Processor (New)

Background service that processes callback triggers.

**Responsibilities**:
- Listen for `session_stop` events on child sessions
- Evaluate callback conditions (strategy, parent state)
- Generate resume messages
- Dispatch resume requests to Agent Launcher

#### 3. Agent Launcher (Extension Required)

Executes agent sessions on registered hosts.

**New Responsibilities for Callbacks**:
- Receive `resume` commands from Agent Runtime
- Execute `ao-resume` with injected callback message
- Report resume success/failure

### Data Flow

#### Flow 1: Registering a Callback

```
┌─────────────┐          ┌───────────────┐          ┌──────────────────┐
│ Orchestrator│          │ Agent Runtime │          │ Callback Registry│
└──────┬──────┘          └───────┬───────┘          └────────┬─────────┘
       │                         │                           │
       │  ao-start --callback    │                           │
       │  child-session-name     │                           │
       │────────────────────────►│                           │
       │                         │                           │
       │                         │  Register callback        │
       │                         │  parent=orchestrator-id   │
       │                         │  child=child-session-name │
       │                         │  strategy=immediate       │
       │                         │──────────────────────────►│
       │                         │                           │
       │                         │◄──────────────────────────│
       │                         │          OK               │
       │◄────────────────────────│                           │
       │     Session started     │                           │
       │                         │                           │
```

#### Flow 2: Callback Trigger on Child Completion

```
┌────────────┐    ┌───────────────┐    ┌──────────────┐    ┌───────────┐
│Child Agent │    │ Agent Runtime │    │  Callback    │    │  Agent    │
│            │    │               │    │  Processor   │    │  Launcher │
└─────┬──────┘    └───────┬───────┘    └──────┬───────┘    └─────┬─────┘
      │                   │                   │                  │
      │ session_stop      │                   │                  │
      │ (finished)        │                   │                  │
      │──────────────────►│                   │                  │
      │                   │                   │                  │
      │                   │ Event: child      │                  │
      │                   │ session finished  │                  │
      │                   │──────────────────►│                  │
      │                   │                   │                  │
      │                   │                   │ Check: parent    │
      │                   │                   │ session idle?    │
      │                   │◄──────────────────│                  │
      │                   │                   │                  │
      │                   │ Yes, status=      │                  │
      │                   │ "finished"        │                  │
      │                   │──────────────────►│                  │
      │                   │                   │                  │
      │                   │                   │ Generate resume  │
      │                   │                   │ message          │
      │                   │                   │                  │
      │                   │                   │ Request: resume  │
      │                   │                   │ orchestrator-id  │
      │                   │                   │ with message     │
      │                   │                   │─────────────────►│
      │                   │                   │                  │
      │                   │                   │                  │ Execute
      │                   │                   │                  │ ao-resume
      │                   │                   │                  │
```

#### Flow 3: Orchestrator Resumption

```
┌────────────────┐          ┌───────────────┐          ┌─────────────────┐
│  Orchestrator  │          │ Agent Launcher│          │  Agent Runtime  │
│  (resumed)     │          │               │          │                 │
└───────┬────────┘          └───────┬───────┘          └────────┬────────┘
        │                           │                           │
        │◄──────────────────────────│                           │
        │  ao-resume with message:  │                           │
        │  "Child 'task-1' and      │                           │
        │   'task-2' completed.     │                           │
        │   Use ao-get-result to    │                           │
        │   retrieve their results."│                           │
        │                           │                           │
        │                           │                           │
        │  (Orchestrator processes  │                           │
        │   and retrieves results)  │                           │
        │                           │                           │
        │  ao-get-result task-1     │                           │
        │───────────────────────────┼──────────────────────────►│
        │                           │                           │
        │◄──────────────────────────┼───────────────────────────│
        │  Result content           │                           │
        │                           │                           │
```

### Callback Strategies

Three strategies for when to trigger the orchestrator callback:

| Strategy | Behavior | Use Case |
|----------|----------|----------|
| `immediate` | Resume on first child completion | Reactive processing, fastest response |
| `batch` | Wait N seconds after first completion, aggregate | Reduce context switches |
| `all` | Wait until all registered children complete | Fork/join parallelism |

### Resume Message Format

When the orchestrator is resumed via callback, it receives a system-generated message:

```markdown
## Agent Callback Notification

The following agent session(s) have completed:

| Session Name | Status | Completed At |
|--------------|--------|--------------|
| task-1 | finished | 2025-01-15T10:30:00Z |
| task-2 | finished | 2025-01-15T10:32:15Z |

To retrieve results, use:
- `ao-get-result task-1`
- `ao-get-result task-2`
```

For single completion (immediate strategy):
```markdown
## Agent Callback Notification

Agent session `task-1` has completed with status: finished.

To retrieve the result: `ao-get-result task-1`
```

## Database Schema Changes

### New Table: `callback_registrations`

Tracks parent-child relationships and callback state.

```sql
CREATE TABLE callback_registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Parent (orchestrator) information
    parent_session_id TEXT NOT NULL,
    parent_session_name TEXT NOT NULL,

    -- Child session information
    child_session_id TEXT,              -- NULL until child starts and gets ID
    child_session_name TEXT NOT NULL,   -- Known at registration time

    -- Callback configuration
    strategy TEXT NOT NULL DEFAULT 'immediate',  -- 'immediate', 'batch', 'all'
    batch_delay_seconds INTEGER DEFAULT 5,       -- For 'batch' strategy

    -- State tracking
    status TEXT NOT NULL DEFAULT 'pending',      -- 'pending', 'child_running',
                                                 -- 'child_completed', 'callback_sent',
                                                 -- 'callback_failed', 'cancelled'

    -- Timestamps
    registered_at TEXT NOT NULL,
    child_started_at TEXT,
    child_completed_at TEXT,
    callback_sent_at TEXT,

    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Foreign keys
    FOREIGN KEY (parent_session_id) REFERENCES sessions(session_id),
    FOREIGN KEY (child_session_id) REFERENCES sessions(session_id)
);

-- Indexes for common queries
CREATE INDEX idx_callback_parent ON callback_registrations(parent_session_id);
CREATE INDEX idx_callback_child ON callback_registrations(child_session_id);
CREATE INDEX idx_callback_status ON callback_registrations(status);
CREATE INDEX idx_callback_child_name ON callback_registrations(child_session_name);
```

### Sessions Table Extension

Add field to track callback-waiting state:

```sql
ALTER TABLE sessions ADD COLUMN awaiting_callbacks INTEGER DEFAULT 0;
-- Count of pending callbacks this session is waiting for
-- Decremented when children complete
-- When 0 and status='finished', session is truly done (not waiting)
```

### State Diagram: Callback Registration Lifecycle

```
                    ┌─────────────────┐
                    │    pending      │
                    │  (registered,   │
                    │  child not yet  │
                    │   started)      │
                    └────────┬────────┘
                             │ Child session created
                             │ (child_session_id set)
                             ▼
                    ┌─────────────────┐
                    │ child_running   │
                    │  (child agent   │
                    │   executing)    │
                    └────────┬────────┘
                             │ Child session_stop event
                             ▼
                    ┌─────────────────┐
          ┌─────────│child_completed  │─────────┐
          │         │  (waiting for   │         │
          │         │  parent idle)   │         │
          │         └─────────────────┘         │
          │                                     │
          │ Parent idle                         │ Parent deleted or
          │ Resume successful                   │ Resume failed
          ▼                                     ▼
┌─────────────────┐                   ┌─────────────────┐
│  callback_sent  │                   │ callback_failed │
│  (orchestrator  │                   │  (error state)  │
│   resumed)      │                   │                 │
└─────────────────┘                   └─────────────────┘
```

## API Changes

### New Endpoints

#### POST /callbacks/register

Register a callback for a child session.

**Request:**
```json
{
    "parent_session_id": "uuid-of-orchestrator",
    "parent_session_name": "orchestrator-main",
    "child_session_name": "task-worker-1",
    "strategy": "immediate",
    "batch_delay_seconds": 5
}
```

**Response:**
```json
{
    "callback_id": 123,
    "status": "pending"
}
```

#### GET /callbacks/{parent_session_id}

Get all callbacks registered by a parent session.

**Response:**
```json
{
    "callbacks": [
        {
            "callback_id": 123,
            "child_session_name": "task-worker-1",
            "child_session_id": "uuid-or-null",
            "status": "child_running",
            "strategy": "immediate"
        }
    ]
}
```

#### DELETE /callbacks/{callback_id}

Cancel a pending callback registration.

### Modified Endpoints

#### POST /sessions

Extended to link child sessions to callback registrations.

When creating a session, if a callback registration exists for this `session_name` as a child:
- Update `callback_registrations.child_session_id`
- Update `callback_registrations.status` to `child_running`
- Update `callback_registrations.child_started_at`

#### POST /sessions/{id}/events

Extended for `session_stop` events to trigger callback processing:
- When event_type is `session_stop`
- Check if session is a child in any callback registration
- If yes, update registration status and trigger Callback Processor

## Integration with Agent Launcher

The callback system depends on the Agent Launcher architecture (see ADR-001 or ARCHITECTURE.md).

### Required Launcher Capabilities

1. **Resume Session Command**
   ```
   POST /launcher/resume
   {
       "session_id": "uuid-of-orchestrator",
       "session_name": "orchestrator-main",
       "message": "Agent callback notification...",
       "project_dir": "/path/to/project"
   }
   ```

2. **Status Reporting**
   - Success: Resume initiated, orchestrator running
   - Failure: Session not found, launcher busy, execution error

3. **Registration with Agent Runtime**
   - Launcher registers on startup
   - Agent Runtime knows which launcher can execute which sessions
   - Callback Processor routes resume requests appropriately

### Sequence: Agent Launcher Integration

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Callback   │     │   Agent     │     │   Agent     │     │Claude Code  │
│  Processor  │     │  Runtime    │     │  Launcher   │     │ (ao-resume) │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │                   │
       │ Child completed   │                   │                   │
       │ Parent idle       │                   │                   │
       │                   │                   │                   │
       │ Find launcher for │                   │                   │
       │ parent session    │                   │                   │
       │──────────────────►│                   │                   │
       │                   │                   │                   │
       │◄──────────────────│                   │                   │
       │ launcher_id=A     │                   │                   │
       │                   │                   │                   │
       │ POST /resume      │                   │                   │
       │───────────────────┼──────────────────►│                   │
       │                   │                   │                   │
       │                   │                   │ ao-resume         │
       │                   │                   │ --session name    │
       │                   │                   │ --message "..."   │
       │                   │                   │──────────────────►│
       │                   │                   │                   │
       │                   │                   │◄──────────────────│
       │                   │                   │    (executing)    │
       │◄──────────────────┼───────────────────│                   │
       │      200 OK       │                   │                   │
       │                   │                   │                   │
       │ Update callback   │                   │                   │
       │ status: sent      │                   │                   │
       │──────────────────►│                   │                   │
       │                   │                   │                   │
```

## Implementation Phases

### Phase 1: Database & API Foundation
- Add `callback_registrations` table
- Extend `sessions` table with `awaiting_callbacks`
- Implement callback registration API endpoints
- Add callback registry queries

### Phase 2: Callback Processor
- Implement event listener for `session_stop`
- Add parent state checking logic
- Implement message generation
- Add callback status management

### Phase 3: Agent Launcher Integration
- Extend Agent Launcher with resume endpoint
- Implement launcher selection logic
- Add retry handling for failed resumes
- Implement health checking

### Phase 4: CLI Integration
- Add `--callback` flag to `ao-start`
- Add `ao-callbacks` command to list pending callbacks
- Add `ao-cancel-callback` command
- Update `ao-status` to show callback state

## Open Questions

1. **Callback Message Injection**: How does the launcher pass the callback message to `ao-resume`? Options:
   - New CLI flag: `ao-resume --inject-message "..."`
   - Environment variable
   - Temporary file

2. **Multi-Level Hierarchies**: If a child spawns grandchildren with callbacks, and the child completes, should the orchestrator be notified? How deep should callback propagation go?

3. **Callback Cancellation**: When should callbacks be automatically cancelled?
   - Parent session deleted
   - Child session deleted
   - Manual cancellation
   - Timeout

4. **Launcher Affinity**: If the original orchestrator ran on Launcher A, must the callback resume also happen on Launcher A? (Likely yes, for session state continuity)

## Related Documents

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Overall system architecture
- [DATABASE_SCHEMA.md](./agent-runtime/DATABASE_SCHEMA.md) - Current database schema
- Agent Launcher ADR (planned) - Detailed launcher architecture

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2025-01-15 | - | Initial draft |
