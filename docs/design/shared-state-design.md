# Design Document: Shared State Across Root and Child Sessions

**Status:** Draft
**Date:** 2025-12-20
**Author:** Claude (Design Proposal)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Repo Grounding](#repo-grounding)
3. [Problem Statement](#problem-statement)
4. [Proposed Designs](#proposed-designs)
   - [Design A: Root-State as Single JSON Blob](#design-a-root-state-as-single-json-blob)
   - [Design B: Root-State as Key-Value Table](#design-b-root-state-as-key-value-table)
   - [Design C: Event-Sourced State Mutations](#design-c-event-sourced-state-mutations)
5. [State Handoff to Child Agent](#state-handoff-to-child-agent)
6. [Recommended Plan](#recommended-plan)
7. [Appendices](#appendices)

---

## Executive Summary

This document proposes designs for introducing **persistent shared state** accessible across a root session and all child sessions it spawns. The state is:

- Owned by a "root session" (the session initiating orchestration)
- Accessible to root AND all descendant child sessions (read + update)
- Persisted independently of LLM context windows
- Generic: supports key/value pairs and JSON primitives (strings, numbers, booleans, null, arrays, objects)

**Key challenge:** Children may run in parallel and attempt concurrent updates. This document proposes and compares concurrency control strategies.

---

## Repo Grounding

### Relevant Files and Modules

| Path | Description |
|------|-------------|
| `servers/agent-coordinator/database.py` | SQLite schema initialization, CRUD for sessions/events. Contains `init_db()`, `create_session()`, `update_session_status()`. |
| `servers/agent-coordinator/models.py` | Pydantic models for Session, Event, Agent, Run. Defines all API data structures. |
| `servers/agent-coordinator/main.py` | FastAPI router with all REST/WebSocket endpoints. Core entry point (~900 lines). |
| `servers/agent-coordinator/services/callback_processor.py` | In-memory notification queue for parent-child callbacks. Tracks `_pending_notifications` and `_resume_in_flight`. |
| `servers/agent-coordinator/services/run_queue.py` | Thread-safe in-memory run queue. Maps runs to sessions with status lifecycle. |
| `servers/agent-coordinator/services/runner_registry.py` | Thread-safe runner tracking with heartbeat management. |
| `servers/agent-coordinator/services/stop_command_queue.py` | Thread-safe queue for stop signals with asyncio event wake-up. |
| `servers/agent-coordinator/agent_storage.py` | File-based JSON storage for agent blueprints (CRUD). |
| `servers/agent-runner/lib/executor.py` | Subprocess executor. Sets `AGENT_SESSION_NAME` environment variable for child context propagation. |
| `docs/agent-coordinator/DATABASE_SCHEMA.md` | Documents `sessions` and `events` SQLite tables. |
| `docs/features/agent-callback-architecture.md` | Comprehensive callback mechanism documentation. |
| `docs/adr/ADR-005-parent-session-context-propagation.md` | ADR for parent context propagation via env vars and HTTP headers. |

### Current Parent-Child Tracking

The existing `sessions` table has:

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    session_name TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    project_dir TEXT,
    agent_name TEXT,
    last_resumed_at TEXT,
    parent_session_name TEXT  -- Immediate parent only!
);
```

**Critical finding:** Only the **immediate parent** (`parent_session_name`) is tracked. There is **no `root_session_id`** field. This means:
- A chain like `Root → Child A → Child B` does not preserve that `Root` is the "origin"
- To support shared state across a tree, we need to either:
  1. Add `root_session_id` column and propagate it, OR
  2. Compute root dynamically by walking the parent chain, OR
  3. Store root as explicit parameter on state operations

### Propagation Mechanism

Parent session context is propagated via:

1. **Environment Variable:** `AGENT_SESSION_NAME` set by Agent Runner
2. **HTTP Header:** `X-Agent-Session-Name` for HTTP MCP servers
3. **Placeholder:** `${AGENT_SESSION_NAME}` in MCP config, replaced at runtime

This pattern can be extended to propagate `AGENT_ROOT_SESSION_NAME`.

---

## Problem Statement

### Goals

1. **Shared State:** A root session creates state; all children (direct and transitive) can read and update it.
2. **Persistence:** State survives across run boundaries (start/resume/stop cycles).
3. **Generic Data:** Key-value pairs with JSON values (not just strings).
4. **Concurrency Safety:** Parallel children updating state must not cause data loss or corruption.
5. **Dashboard Visibility:** State readable via API; optionally viewable in Dashboard with history.

### Non-Goals (for initial design)

- Credentials/secrets management (design should not encourage storing them)
- Cross-root-session state sharing
- Complex query patterns (filtering, aggregation)
- Real-time state synchronization to LLM context (state is pulled on-demand)

### Hard Problem: Concurrent Updates

Consider this scenario:
```
Root Session starts 3 children in parallel:
  Child A: state.patch({progress: 10})
  Child B: state.patch({progress: 20})
  Child C: state.patch({progress: 30})
```

Without concurrency control:
- Last write wins (data loss)
- Race conditions corrupt state
- Children overwrite each other's unrelated keys

---

## Proposed Designs

### Design A: Root-State as Single JSON Blob

Store the entire shared state as a single JSON document with optimistic concurrency control via ETags.

#### Data Model

**New table: `session_state`**

```sql
CREATE TABLE session_state (
    root_session_id TEXT PRIMARY KEY,      -- References sessions.session_id
    state_data TEXT NOT NULL DEFAULT '{}', -- JSON blob
    version INTEGER NOT NULL DEFAULT 1,     -- Monotonic version (ETag)
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (root_session_id) REFERENCES sessions(session_id)
);

CREATE INDEX idx_session_state_updated ON session_state(updated_at DESC);
```

**Extended sessions table:**

```sql
ALTER TABLE sessions ADD COLUMN root_session_id TEXT;
CREATE INDEX idx_sessions_root ON sessions(root_session_id);
```

#### Root Session ID Propagation

1. When a session starts with no parent, it becomes its own root: `root_session_id = session_id`
2. When a child starts, inherit root from parent:
   ```python
   # In ao-start or session creation
   if parent_session_name:
       parent = get_session_by_name(parent_session_name)
       root_session_id = parent.root_session_id or parent.session_id
   else:
       root_session_id = session_id
   ```
3. Propagate via new environment variable: `AGENT_ROOT_SESSION_ID`
4. Store in sessions table for all descendants

#### API Shape

**Initialize state (called automatically on first access or explicitly)**

```
POST /sessions/{session_id}/state
Content-Type: application/json

{
  "initial_state": {
    "tasks_completed": 0,
    "findings": [],
    "config": {"mode": "parallel"}
  }
}

Response: 201 Created
{
  "root_session_id": "sess_abc123",
  "state": {...},
  "version": 1,
  "created_at": "2025-12-20T10:00:00Z"
}
```

**Get current state**

```
GET /sessions/{session_id}/state
If-None-Match: "3"  // Optional: return 304 if version matches

Response: 200 OK
ETag: "5"
{
  "root_session_id": "sess_abc123",
  "state": {
    "tasks_completed": 3,
    "findings": ["finding1", "finding2"],
    "config": {"mode": "parallel"}
  },
  "version": 5,
  "updated_at": "2025-12-20T10:05:00Z"
}
```

**Update state (full replacement)**

```
PUT /sessions/{session_id}/state
If-Match: "5"  // Required: optimistic concurrency
Content-Type: application/json

{
  "state": {
    "tasks_completed": 4,
    "findings": ["finding1", "finding2", "finding3"],
    "config": {"mode": "parallel"}
  }
}

Response: 200 OK
ETag: "6"
{...updated state...}

Error: 409 Conflict (if version mismatch)
{
  "error": "version_conflict",
  "current_version": 7,
  "your_version": 5,
  "current_state": {...}
}
```

**Patch state (partial update with merge)**

```
PATCH /sessions/{session_id}/state
If-Match: "5"
Content-Type: application/merge-patch+json

{
  "tasks_completed": 4,
  "new_key": "new_value"
}

Response: 200 OK
ETag: "6"
{...merged state...}
```

#### Concurrency Strategy A1: Optimistic Concurrency + Client Retry

1. Client reads state, gets version (ETag)
2. Client computes new state
3. Client PUTs/PATCHes with `If-Match: <version>`
4. If 409 Conflict: client re-reads, re-merges, retries
5. Max retries: 3 with exponential backoff (100ms, 200ms, 400ms)

**Retry policy for MCP tools:**

```python
async def state_patch(session_id: str, patch: dict, max_retries: int = 3):
    for attempt in range(max_retries):
        current = await get_state(session_id)
        merged = deep_merge(current.state, patch)
        try:
            return await put_state(session_id, merged, if_match=current.version)
        except ConflictError as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(0.1 * (2 ** attempt))
```

#### Concurrency Strategy A2: Server-Side JSON Merge

Server applies merge semantics without requiring version match for additive operations:

```
PATCH /sessions/{session_id}/state
Content-Type: application/merge-patch+json
X-Merge-Strategy: deep  // or "shallow"

{
  "findings": {"$append": ["new_finding"]},
  "counters.processed": {"$increment": 1}
}
```

Special operators:
- `$append`: Append to array
- `$increment`: Atomic increment
- `$set`: Explicit set (no merge)
- `$delete`: Remove key

**Trade-off:** More complex server logic, but reduces client retry burden.

#### Dashboard Integration

1. **State Viewer:** New tab or panel in session detail view
2. **Read via:** `GET /sessions/{session_id}/state`
3. **History:** Optional `state_history` table for audit trail

```sql
CREATE TABLE session_state_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    root_session_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    state_data TEXT NOT NULL,
    changed_by_session TEXT,  -- Which session made the change
    changed_at TEXT NOT NULL,
    FOREIGN KEY (root_session_id) REFERENCES session_state(root_session_id)
);
```

4. **WebSocket events:** Broadcast state changes

```json
{
  "type": "state_updated",
  "root_session_id": "sess_abc123",
  "version": 6,
  "changed_by": "child_session_xyz",
  "patch": {"tasks_completed": 4}
}
```

#### Pros and Cons

| Pros | Cons |
|------|------|
| Simple mental model (one blob) | Entire state locked on update |
| Easy to reason about | Client retry complexity |
| Standard ETag pattern | Large states = large payloads |
| History is straightforward | No per-key granularity |
| Dashboard shows complete state | Merge conflicts hard to auto-resolve |

#### Failure Modes

- **Version explosion under high concurrency:** Many retries if 10+ children update simultaneously
- **State size growth:** No built-in limits; could grow unbounded
- **Stale reads:** Children might operate on outdated state between read and update

---

### Design B: Root-State as Key-Value Table

Store state as individual key-value pairs with per-key versioning, allowing finer-grained concurrency.

#### Data Model

**New table: `session_state_kv`**

```sql
CREATE TABLE session_state_kv (
    root_session_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,              -- JSON-encoded value
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    updated_by_session TEXT,          -- Which session last updated
    PRIMARY KEY (root_session_id, key),
    FOREIGN KEY (root_session_id) REFERENCES sessions(session_id)
);

CREATE INDEX idx_state_kv_root ON session_state_kv(root_session_id);
CREATE INDEX idx_state_kv_updated ON session_state_kv(root_session_id, updated_at DESC);
```

**Metadata table (optional):**

```sql
CREATE TABLE session_state_meta (
    root_session_id TEXT PRIMARY KEY,
    global_version INTEGER NOT NULL DEFAULT 0, -- Incremented on any key change
    created_at TEXT NOT NULL,
    FOREIGN KEY (root_session_id) REFERENCES sessions(session_id)
);
```

#### Root Session ID Propagation

Same as Design A - propagate `root_session_id` through session creation and environment variables.

#### API Shape

**Get all keys**

```
GET /sessions/{session_id}/state
ETag: "global_version_15"

Response: 200 OK
{
  "root_session_id": "sess_abc123",
  "keys": {
    "tasks_completed": {"value": 3, "version": 2},
    "findings": {"value": ["f1", "f2"], "version": 5},
    "config": {"value": {"mode": "parallel"}, "version": 1}
  },
  "global_version": 15
}
```

**Get single key**

```
GET /sessions/{session_id}/state/keys/{key}
ETag: "2"

Response: 200 OK
{
  "key": "tasks_completed",
  "value": 3,
  "version": 2,
  "updated_at": "2025-12-20T10:05:00Z",
  "updated_by": "child_session_xyz"
}
```

**Set single key (CAS - Compare-And-Swap)**

```
PUT /sessions/{session_id}/state/keys/{key}
If-Match: "2"  // Per-key version
Content-Type: application/json

{
  "value": 4
}

Response: 200 OK
ETag: "3"
{
  "key": "tasks_completed",
  "value": 4,
  "version": 3
}

Error: 409 Conflict (if version mismatch)
{
  "error": "version_conflict",
  "key": "tasks_completed",
  "current_version": 5,
  "your_version": 2,
  "current_value": 10
}
```

**Set key (unconditional - last writer wins)**

```
PUT /sessions/{session_id}/state/keys/{key}
X-If-Match: skip  // Explicit opt-out of CAS

{
  "value": "new_value"
}
```

**Delete key**

```
DELETE /sessions/{session_id}/state/keys/{key}
If-Match: "3"  // Optional: conditional delete

Response: 204 No Content
```

**Batch update (transactional)**

```
POST /sessions/{session_id}/state/batch
Content-Type: application/json

{
  "operations": [
    {"op": "set", "key": "tasks_completed", "value": 5, "if_match": 3},
    {"op": "set", "key": "new_key", "value": "hello"},
    {"op": "delete", "key": "temp_key", "if_match": 1}
  ]
}

Response: 200 OK (all succeeded) or 409 Conflict (partial failure - none applied)
{
  "results": [
    {"key": "tasks_completed", "status": "success", "version": 4},
    {"key": "new_key", "status": "success", "version": 1},
    {"key": "temp_key", "status": "conflict", "current_version": 3}
  ],
  "applied": false  // Atomic: all-or-nothing
}
```

#### Concurrency Strategy B1: Per-Key CAS

- Each key has independent version
- Only conflicts if same key updated concurrently
- Different children updating different keys: no conflict

**Advantage:** Parallel children often update disjoint keys, reducing contention.

#### Concurrency Strategy B2: Atomic Operators Per Key

```
POST /sessions/{session_id}/state/keys/{key}/ops
Content-Type: application/json

{
  "operation": "increment",
  "delta": 1
}

-- or --

{
  "operation": "append",
  "items": ["new_item"]
}

-- or --

{
  "operation": "merge",  // Deep merge for objects
  "patch": {"nested.field": "value"}
}
```

Server executes atomically without version check.

#### Dashboard Integration

1. **Key-Value Table View:** Show all keys with values, versions, last updated
2. **Per-Key History:** Click key to see version history
3. **Real-time updates:** WebSocket broadcasts per-key changes

```json
{
  "type": "state_key_updated",
  "root_session_id": "sess_abc123",
  "key": "tasks_completed",
  "value": 4,
  "version": 3,
  "changed_by": "child_xyz"
}
```

#### Pros and Cons

| Pros | Cons |
|------|------|
| Fine-grained concurrency | More complex API surface |
| Disjoint keys = no conflicts | Harder to get "complete state snapshot" |
| Per-key history/audit | Batch operations need transactional semantics |
| Smaller update payloads | More database rows/queries |
| Natural for counter/flag patterns | Nested objects awkward (flatten or serialize) |

#### Failure Modes

- **Key explosion:** No limit on number of keys; could grow unbounded
- **Orphaned keys:** No automatic cleanup when children fail
- **Batch rollback complexity:** Partial failures in non-atomic mode

---

### Design C: Event-Sourced State Mutations

Store state changes as an append-only event log. Materialize current state by replaying events.

#### Data Model

**Event log table:**

```sql
CREATE TABLE session_state_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    root_session_id TEXT NOT NULL,
    session_id TEXT NOT NULL,         -- Which session produced the event
    event_type TEXT NOT NULL,         -- 'set', 'delete', 'patch', 'increment', etc.
    key TEXT,                         -- NULL for whole-state operations
    payload TEXT NOT NULL,            -- JSON: the mutation details
    timestamp TEXT NOT NULL,
    sequence_number INTEGER NOT NULL, -- Per-root monotonic sequence
    FOREIGN KEY (root_session_id) REFERENCES sessions(session_id)
);

CREATE INDEX idx_state_events_root_seq ON session_state_events(root_session_id, sequence_number);
CREATE INDEX idx_state_events_timestamp ON session_state_events(root_session_id, timestamp);
```

**Materialized view (cache):**

```sql
CREATE TABLE session_state_materialized (
    root_session_id TEXT PRIMARY KEY,
    state_data TEXT NOT NULL,           -- Current state (JSON)
    last_sequence INTEGER NOT NULL,     -- Last applied event
    materialized_at TEXT NOT NULL,
    FOREIGN KEY (root_session_id) REFERENCES sessions(session_id)
);
```

#### Event Types

```typescript
type StateEvent =
  | { type: "init", payload: object }
  | { type: "set", key: string, value: any }
  | { type: "delete", key: string }
  | { type: "patch", key: string, patch: object }  // Deep merge
  | { type: "increment", key: string, delta: number }
  | { type: "append", key: string, items: any[] }
  | { type: "full_replace", payload: object };
```

#### Concurrency Strategy C1: Append-Only + Deterministic Merge

All mutations are appends; conflicts are resolved by replay order:

1. Child A appends: `{type: "set", key: "x", value: 1, seq: 10}`
2. Child B appends: `{type: "set", key: "x", value: 2, seq: 11}`
3. Replay: seq 10 sets x=1, seq 11 sets x=2. Final: x=2

**No conflicts, no retries.** Last-write-wins by sequence number.

**Sequence number assignment:**
```sql
-- Atomic sequence increment
UPDATE session_state_materialized
SET last_sequence = last_sequence + 1
WHERE root_session_id = ?
RETURNING last_sequence;
```

#### Concurrency Strategy C2: Conflict-Free Replicated Data Types (CRDTs)

Use CRDT-inspired structures for automatic merge:

- **G-Counter:** Only increments, sum across all children
- **LWW-Register:** Last-Writer-Wins by timestamp
- **OR-Set:** Add/remove with unique tags

Example: Distributed counter
```json
// Event from Child A
{"type": "counter_add", "key": "processed", "value": 5, "actor": "child_a"}

// Event from Child B
{"type": "counter_add", "key": "processed", "value": 3, "actor": "child_b"}

// Materialized: processed = 8 (sum of all actor contributions)
```

#### API Shape

**Append mutation event**

```
POST /sessions/{session_id}/state/events
Content-Type: application/json

{
  "type": "set",
  "key": "tasks_completed",
  "value": 5
}

Response: 201 Created
{
  "event_id": 42,
  "sequence_number": 15,
  "timestamp": "2025-12-20T10:05:00Z"
}
```

**Get current state (materialized)**

```
GET /sessions/{session_id}/state

Response: 200 OK
{
  "root_session_id": "sess_abc123",
  "state": {
    "tasks_completed": 5,
    "findings": ["f1", "f2"]
  },
  "last_sequence": 15,
  "materialized_at": "2025-12-20T10:05:00Z"
}
```

**Get event history**

```
GET /sessions/{session_id}/state/events?since=10&limit=50

Response: 200 OK
{
  "events": [
    {"event_id": 11, "type": "set", "key": "x", "value": 1, "session_id": "child_a", "seq": 11},
    {"event_id": 12, "type": "increment", "key": "counter", "delta": 1, "session_id": "child_b", "seq": 12},
    ...
  ],
  "has_more": true
}
```

**Replay state at point in time**

```
GET /sessions/{session_id}/state?at_sequence=10

Response: 200 OK
{
  "state": {...},  // State as of sequence 10
  "sequence": 10
}
```

#### Materialization Strategy

**On-demand (lazy):**
```python
def get_current_state(root_session_id):
    cached = get_materialized(root_session_id)
    new_events = get_events_since(root_session_id, cached.last_sequence)
    if not new_events:
        return cached.state_data

    state = json.loads(cached.state_data)
    for event in new_events:
        state = apply_event(state, event)

    update_materialized(root_session_id, state, new_events[-1].sequence_number)
    return state
```

**Write-through (eager):**
- Apply to materialized view synchronously on each event append
- Higher write latency, instant read

#### Dashboard Integration

1. **State Timeline:** Visual timeline of all mutations
2. **Playback:** Scrub through state history
3. **Diff View:** Compare state at two points
4. **Per-Session Attribution:** See which session made each change

```json
// WebSocket
{
  "type": "state_event",
  "root_session_id": "sess_abc123",
  "event": {"type": "set", "key": "x", "value": 5},
  "sequence": 15,
  "session_id": "child_xyz"
}
```

#### Pros and Cons

| Pros | Cons |
|------|------|
| Full history/audit trail | More complex implementation |
| Time-travel debugging | Storage grows with history |
| No update conflicts (append-only) | Materialization overhead |
| Natural conflict resolution | CRDT concepts add complexity |
| Easy to understand "what happened" | Compaction needed for long-lived roots |

#### Failure Modes

- **Unbounded log growth:** Need compaction/snapshotting strategy
- **Materialization lag:** Stale reads if materialization delayed
- **Replay performance:** Large history = slow replay (mitigate with snapshots)
- **Ordering ambiguity:** Concurrent events may have arbitrary sequence order

---

## State Handoff to Child Agent

### Challenge

When a child session starts, how does it access the shared state? Options:

1. **On-demand pull via MCP tools**
2. **Coordinator-injected summary in resume message**
3. **Mirror to Context Store**

### Option 1: On-Demand Pull via MCP Tools (Recommended)

Child agents use MCP tools to read/update state explicitly:

```python
# MCP tools exposed by Agent Orchestrator MCP server
@mcp.tool()
def state_get(key: Optional[str] = None) -> str:
    """Get shared state for current session's root.

    Args:
        key: Optional specific key. If None, returns all state.

    Returns:
        JSON string of state value(s)
    """
    root_id = get_root_session_id()  # From AGENT_ROOT_SESSION_ID env
    if key:
        return api.get_state_key(root_id, key)
    return api.get_state(root_id)

@mcp.tool()
def state_set(key: str, value: str) -> str:
    """Set a key in shared state.

    Args:
        key: State key
        value: JSON-encoded value

    Returns:
        Confirmation with new version
    """
    root_id = get_root_session_id()
    return api.set_state_key(root_id, key, json.loads(value))

@mcp.tool()
def state_patch(patch: str) -> str:
    """Merge patch into shared state.

    Args:
        patch: JSON object to merge
    """
    root_id = get_root_session_id()
    return api.patch_state(root_id, json.loads(patch))
```

**Propagation of root_session_id:**

1. Add `AGENT_ROOT_SESSION_ID` environment variable
2. Runner sets it when spawning subprocess (alongside `AGENT_SESSION_NAME`)
3. MCP server reads it to identify which root's state to access

**Advantages:**
- Explicit control over when state is read/updated
- No context bloat from unwanted state
- Children only pull what they need
- Works with all designs (A, B, C)

**Disadvantages:**
- Agent must know to use the tools
- Additional tool calls = latency
- Agent might forget to check state

### Option 2: Coordinator-Injected Summary

On session start/resume, inject bounded state summary into the prompt:

```python
# In callback_processor or run creation
def build_resume_prompt(parent_session, child_results):
    state_summary = get_state_summary(parent_session.root_session_id)
    return f"""
## Session State Summary
{format_state_summary(state_summary)}

## Child Results
{format_child_results(child_results)}
"""

def get_state_summary(root_session_id, max_keys=10, max_bytes=2000):
    state = get_state(root_session_id)
    if len(json.dumps(state)) <= max_bytes:
        return state

    # Truncate: prioritize recently updated keys
    keys = sorted(state.keys(), key=lambda k: state[k].updated_at, reverse=True)
    summary = {}
    total_size = 0
    for key in keys[:max_keys]:
        val = state[key]
        val_size = len(json.dumps(val))
        if total_size + val_size > max_bytes:
            summary["_truncated"] = True
            break
        summary[key] = val
        total_size += val_size
    return summary
```

**Size limits:**
- Max keys: 10-20
- Max bytes: 2000-4000 characters
- Truncation indicator: `_truncated: true, _full_key_count: N`

**Advantages:**
- Agent automatically aware of state
- No extra tool calls needed
- Works well for small states

**Disadvantages:**
- Context bloat for large states
- Injection on every resume (redundant)
- Complex summarization logic
- Hard to select "relevant" subset

### Option 3: Mirror to Context Store

Store state as a document in Context Store; children use `doc-read`:

```python
# On state update, also update Context Store
async def sync_state_to_context_store(root_session_id, state):
    doc_id = f"state:{root_session_id}"
    await context_store.doc_write(doc_id, json.dumps(state, indent=2))
    await context_store.doc_tag(doc_id, [f"root:{root_session_id}", "shared-state"])
```

Children pull via:
```
doc-read state:sess_abc123
```

**Advantages:**
- Reuses existing Context Store infrastructure
- Document semantics familiar to agents
- Semantic search possible (find states by content)

**Disadvantages:**
- Dual storage (Agent Coordinator + Context Store)
- Sync lag between systems
- Context Store not designed for high-frequency updates
- Adds dependency on Context Store

### Recommended Approach: On-Demand Pull (Option 1)

**Rationale:**
1. Explicit is better than implicit
2. Avoids context bloat
3. Works with any state design
4. Children have full control over what they read
5. No summarization complexity

**Enhancement:** For frequently-needed state, agents can use MCP tool at session start:
```
Agent prompt: "First, check shared state with state_get() to see current progress."
```

---

## Recommended Plan

### Recommended Design: Design B (Key-Value Table) with CAS

**Rationale:**

1. **Fits existing patterns:** Similar to how `session_state_kv` mirrors the pattern used in `callback_processor` (key-value tracking of pending notifications)

2. **Fine-grained concurrency:** Parallel children updating different keys never conflict - ideal for orchestration where each child handles distinct subtasks

3. **Simpler than event-sourcing:** Design C's full audit trail adds complexity that may not be needed for MVP

4. **Familiar API:** RESTful CRUD on keys with optional CAS matches common patterns

5. **Incremental history (optional):** Can add per-key history later without changing core design

### Minimal API Surface

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/sessions/{id}/state` | Get all keys for session's root |
| `GET` | `/sessions/{id}/state/keys/{key}` | Get single key |
| `PUT` | `/sessions/{id}/state/keys/{key}` | Set key (CAS with If-Match) |
| `DELETE` | `/sessions/{id}/state/keys/{key}` | Delete key |
| `POST` | `/sessions/{id}/state/keys/{key}/ops` | Atomic operation (increment, append) |

#### MCP Tools

| Tool | Description |
|------|-------------|
| `state_get` | Get all or single key |
| `state_set` | Set key with optional CAS |
| `state_delete` | Delete key |
| `state_increment` | Atomic increment |
| `state_append` | Atomic array append |

### Database Changes

```sql
-- Add root_session_id to sessions
ALTER TABLE sessions ADD COLUMN root_session_id TEXT;
CREATE INDEX idx_sessions_root ON sessions(root_session_id);

-- Create state storage
CREATE TABLE session_state_kv (
    root_session_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    updated_by_session TEXT,
    PRIMARY KEY (root_session_id, key)
);
```

### Dashboard Updates

1. **State Tab:** Add "State" tab in session detail view (for root sessions)
2. **Key-Value Table:** Display all keys with values, versions, last updated
3. **Real-time:** Subscribe to `state_key_updated` WebSocket events
4. **Read-only initially:** Dashboard views state but doesn't edit (future: add edit capability)

### WebSocket Events

```json
{
  "type": "state_key_updated",
  "root_session_id": "sess_abc123",
  "key": "progress",
  "value": 42,
  "version": 3,
  "updated_by": "child_xyz",
  "timestamp": "2025-12-20T10:05:00Z"
}

{
  "type": "state_key_deleted",
  "root_session_id": "sess_abc123",
  "key": "temp_data",
  "version": 5,
  "deleted_by": "child_xyz"
}
```

### Migration Plan

1. **Phase 1:** Add `root_session_id` column to sessions table
   - Nullable initially
   - Backfill existing sessions: `root_session_id = session_id` where `parent_session_name IS NULL`

2. **Phase 2:** Propagate root_session_id
   - Update `executor.py` to set `AGENT_ROOT_SESSION_ID` env var
   - Update session creation to inherit root from parent

3. **Phase 3:** Add state storage
   - Create `session_state_kv` table
   - Add REST endpoints
   - Add MCP tools

4. **Phase 4:** Dashboard integration
   - Add State tab
   - Wire up WebSocket events

### Backwards Compatibility

- Sessions without `root_session_id` are treated as their own root
- State API returns 404 if no state exists (agents can initialize)
- Existing sessions continue to work unchanged
- New MCP tools are additive (existing tools unchanged)

### Testing Plan

#### Unit Tests

1. **State CRUD:** Create, read, update, delete keys
2. **CAS enforcement:** Verify 409 on version mismatch
3. **Atomic operations:** Increment, append work correctly
4. **Root propagation:** Child inherits root from parent

#### Integration Tests

1. **Single session state:** Root creates state, reads it back
2. **Parent-child sharing:** Root creates state, child reads and updates
3. **Multi-level hierarchy:** Root → Child A → Child B all share state

#### Concurrency Tests

```python
def test_parallel_updates_different_keys():
    """Parallel children updating different keys should never conflict."""
    # Start root
    # Spawn 5 children in parallel
    # Each child sets a unique key: child_{i}_result
    # Wait for all completions
    # Verify all 5 keys present in state

def test_parallel_updates_same_key_cas():
    """Parallel updates to same key with CAS should eventually succeed."""
    # Start root with key: counter = 0
    # Spawn 3 children, each tries to increment counter
    # Some will get 409, should retry
    # Eventually counter = 3

def test_atomic_increment_no_conflicts():
    """Atomic increment should never conflict."""
    # Start root with key: counter = 0
    # Spawn 10 children, each calls state_increment("counter", 1)
    # No retries needed
    # Final counter = 10
```

---

## Appendices

### Appendix A: Full API Reference (Design B)

#### GET /sessions/{session_id}/state

Get all state keys for the session's root.

**Response:**
```json
{
  "root_session_id": "sess_abc123",
  "keys": {
    "progress": {"value": 50, "version": 3, "updated_at": "...", "updated_by": "child_a"},
    "config": {"value": {"mode": "parallel"}, "version": 1, "updated_at": "...", "updated_by": "sess_abc123"}
  }
}
```

#### GET /sessions/{session_id}/state/keys/{key}

Get single key.

**Response:**
```json
{
  "key": "progress",
  "value": 50,
  "version": 3,
  "updated_at": "2025-12-20T10:00:00Z",
  "updated_by": "child_a"
}
```

**Error:** 404 if key not found

#### PUT /sessions/{session_id}/state/keys/{key}

Set key value.

**Headers:**
- `If-Match: "3"` - Required for CAS; use `*` to skip CAS

**Request:**
```json
{
  "value": 60
}
```

**Response:** 200 OK with updated key

**Error:** 409 Conflict if version mismatch

#### DELETE /sessions/{session_id}/state/keys/{key}

Delete key.

**Headers:**
- `If-Match: "3"` - Optional for CAS

**Response:** 204 No Content

#### POST /sessions/{session_id}/state/keys/{key}/ops

Atomic operation on key.

**Request (increment):**
```json
{
  "operation": "increment",
  "delta": 1
}
```

**Request (append):**
```json
{
  "operation": "append",
  "items": ["new_item"]
}
```

**Response:** 200 OK with new value and version

### Appendix B: Environment Variables

| Variable | Description | Set By |
|----------|-------------|--------|
| `AGENT_SESSION_NAME` | Current session name (existing) | Agent Runner |
| `AGENT_ROOT_SESSION_ID` | Root session ID for state access (new) | Agent Runner |

### Appendix C: MCP Tool Signatures

```python
@mcp.tool()
def state_get(key: Optional[str] = None) -> str:
    """Get shared state value(s).

    If key is provided, returns that key's value.
    If key is None, returns all keys and values.

    Examples:
        state_get()  # Returns all state
        state_get(key="progress")  # Returns {"value": 50, "version": 3}
    """

@mcp.tool()
def state_set(key: str, value: str, version: Optional[int] = None) -> str:
    """Set a key in shared state.

    Args:
        key: The key to set
        value: JSON-encoded value
        version: Optional version for CAS (conflict if mismatch)

    Returns:
        JSON with new version number
    """

@mcp.tool()
def state_delete(key: str, version: Optional[int] = None) -> str:
    """Delete a key from shared state.

    Args:
        key: The key to delete
        version: Optional version for CAS
    """

@mcp.tool()
def state_increment(key: str, delta: int = 1) -> str:
    """Atomically increment a numeric key.

    Creates key with value=delta if not exists.

    Args:
        key: The key to increment
        delta: Amount to add (can be negative)

    Returns:
        JSON with new value
    """

@mcp.tool()
def state_append(key: str, items: str) -> str:
    """Atomically append items to an array key.

    Creates key with items as initial array if not exists.

    Args:
        key: The key (must be array or not exist)
        items: JSON-encoded array of items to append

    Returns:
        JSON with new array length
    """
```

---

## Decision Summary

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **Storage Model** | Key-Value Table (Design B) | Fine-grained concurrency, familiar pattern |
| **Concurrency** | Per-key CAS + Atomic ops | Reduces conflicts, simple mental model |
| **Root Tracking** | `root_session_id` column + env var | Explicit propagation, queryable |
| **State Access** | On-demand MCP tools | Avoids context bloat, explicit control |
| **Dashboard** | Read-only state viewer | Start simple, add editing later |
| **History** | Optional per-key history table | Add if auditing needed |

---

*End of Design Document*
