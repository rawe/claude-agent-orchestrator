# ADR-010: Session Identity and Executor Abstraction

**Status:** Accepted
**Date:** 2025-12-18
**Decision Makers:** Architecture Review
**Supersedes:** Portions of ADR-001 (session_name as linking key)

## Context

The current architecture uses `session_name` (user-provided) as the primary identifier for correlating runs and sessions, while `session_id` (from Claude SDK) serves as the database primary key. This creates several problems:

### Problem 1: Dual Identity Confusion

```
Sessions table:
  - session_id (PK, indexed) ← From Claude SDK, UUID
  - session_name (NO INDEX)  ← User-provided, used for all lookups

The actual lookup key (session_name) has no index,
while the PK (session_id) is rarely used for lookups.
```

### Problem 2: session_name Causes Collisions

When the same orchestration pattern runs multiple times, it often generates the same `session_name`, causing:
- Collision errors requiring retry
- Wasted tokens and execution time
- Stacking failures in complex orchestration flows

### Problem 3: Identifier Not Available Immediately

The Claude SDK's `session_id` is only available AFTER execution starts. Users cannot get a session identifier immediately when creating a run.

### Problem 4: Framework Lock-in

The current design assumes Claude SDK's session handling. Future executors (Codex, custom agents) may:
- Have different session ID timing
- Not persist messages internally
- Require different resume mechanisms

### Problem 5: Missing Affinity Information

Sessions can only be resumed on the same machine and directory where they were created (Claude stores session data locally). Currently, we don't track:
- Which machine a session belongs to
- Required executor type for resume

## Decision

### 1. Generate Our Own `session_id` at Run Creation

```python
# When run is created, BEFORE execution:
session_id = f"ses_{uuid.uuid4().hex[:12]}"  # e.g., "ses_abc123def456"
```

This provides immediate session identification.

### 2. Remove `session_name` Concept Entirely

- No user-provided session names
- No collision problems
- LLMs handle session_id directly (they don't need human-readable names)

### 3. Store Framework's ID as `executor_session_id`

The Claude SDK's UUID (or any framework's session ID) becomes internal metadata:

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,          -- OUR ID, generated at run creation
    executor_session_id TEXT,             -- Framework's ID (for resume)
    executor_type TEXT,                   -- "claude-code", "codex", etc.
    ...
);
```

### 4. Track Session Affinity for Resume

```sql
    hostname TEXT,                        -- Machine where session lives
    project_dir TEXT,                     -- Directory where session lives
```

Resume operations are only dispatched to runners matching the affinity.

### 5. Executor Binds Framework ID After Start

```
POST /sessions/{session_id}/bind
{
    "executor_session_id": "uuid-from-framework",
    "hostname": "machine-a",
    "executor_type": "claude-code"
}
```

## New Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. CREATE RUN                                                              │
│                                                                             │
│  POST /runs { prompt: "..." }                                               │
│      ↓                                                                      │
│  Coordinator generates session_id = "ses_abc123"                            │
│      ↓                                                                      │
│  Creates session record (executor_session_id = NULL)                        │
│      ↓                                                                      │
│  Returns: { run_id: "run_xyz", session_id: "ses_abc123" }                   │
│                                                                             │
│  Session identifier available IMMEDIATELY                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. RUNNER CLAIMS & EXECUTES                                                │
│                                                                             │
│  Runner claims run, receives: session_id, prompt, project_dir               │
│      ↓                                                                      │
│  Runner spawns executor with session_id in environment/payload              │
│      ↓                                                                      │
│  Executor starts framework → gets executor_session_id                       │
│      ↓                                                                      │
│  Executor calls: POST /sessions/{session_id}/bind                           │
│    Body: { executor_session_id: "uuid", hostname: "machine-a" }             │
│      ↓                                                                      │
│  Coordinator stores the binding                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. EVENTS (during execution)                                               │
│                                                                             │
│  Executor receives events from framework (with executor_session_id)         │
│      ↓                                                                      │
│  Executor posts using session_id (which it received at startup)             │
│      ↓                                                                      │
│  POST /sessions/{session_id}/events { ... }                                 │
│                                                                             │
│  No ID mapping needed - executor already has session_id                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. RESUME                                                                  │
│                                                                             │
│  POST /runs { type: "resume", session_id: "ses_abc123", prompt: "..." }     │
│      ↓                                                                      │
│  Coordinator looks up session affinity:                                     │
│    - executor_session_id = "uuid-from-claude"                               │
│    - hostname = "machine-a"                                                 │
│    - project_dir = "/path/to/project"                                       │
│    - executor_type = "claude-code"                                          │
│      ↓                                                                      │
│  Run created with affinity requirements                                     │
│      ↓                                                                      │
│  Only matching runner can claim (hostname + project_dir + executor_type)    │
│      ↓                                                                      │
│  Runner receives: session_id + executor_session_id                          │
│      ↓                                                                      │
│  Executor uses executor_session_id to resume framework session              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## New Schema

```sql
CREATE TABLE sessions (
    -- Identity (ours)
    session_id TEXT PRIMARY KEY,          -- Generated at run creation

    -- Executor binding (set after execution starts)
    executor_session_id TEXT,             -- Framework's session ID
    executor_type TEXT,                   -- "claude-code", "codex", "custom"

    -- Affinity (where this session can be resumed)
    hostname TEXT,                        -- Machine where session lives
    project_dir TEXT,                     -- Directory where session lives

    -- Status
    status TEXT NOT NULL,                 -- pending, running, finished, error
    created_at TEXT NOT NULL,
    last_resumed_at TEXT,

    -- Relationships
    parent_session_id TEXT,               -- Changed from parent_session_name
    agent_name TEXT,

    FOREIGN KEY (parent_session_id) REFERENCES sessions(session_id)
);

-- Events reference by session_id
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    ...
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
```

## Rationale

### Why Remove session_name?

| Consideration | Analysis |
|---------------|----------|
| **Who uses it?** | LLMs orchestrating agents, not humans directly |
| **Do LLMs need readable names?** | No, they handle IDs fine |
| **What problems does it cause?** | Collisions, dual-identity confusion, unindexed lookups |
| **What value does it provide?** | Minimal - convenience that causes more problems than it solves |

### Why Generate Our Own session_id?

1. **Immediate availability**: User gets session_id in the run creation response
2. **Framework independence**: Our ID is the source of truth, framework IDs are internal
3. **No collisions**: UUIDs don't collide
4. **Single identifier**: One ID to rule them all

### Why Track Affinity?

Claude Code sessions can only be resumed when:
- Same machine (session files in `~/.claude/`)
- Same directory (project context)
- Same executor type

Without affinity tracking, resume requests could be dispatched to wrong runners.

### Alternatives Considered

#### A: Keep session_name, Add Index
- Fixes performance, doesn't fix architectural confusion
- Still have dual identity
- Still have collision problems

#### B: Make session_name Optional
- Backward compatible but inconsistent
- Some sessions have names, some don't
- Doesn't simplify the architecture

#### C: Use Framework's session_id Directly
- Can't - it's not available until execution starts
- Timing problem remains

## Consequences

### Positive

- **Single identifier**: `session_id` is the only session identity
- **Immediate availability**: Session ID known at run creation
- **No collisions**: Auto-generated IDs never collide
- **Framework agnostic**: Executor's ID is an internal detail
- **Proper resume routing**: Affinity ensures correct runner handles resume
- **Simpler correlation**: Link by `session_id`, not string matching on names
- **Future-proof**: Works with any executor framework

### Negative

- **Breaking API change**: `session_name` removed from API
- **Migration required**: Existing sessions need schema migration
- **Less human-readable**: `ses_abc123` instead of `my-research-agent`
- **Parent relationships change**: `parent_session_id` instead of `parent_session_name`

### Neutral

- Coordinator still stores executor's ID (can't fully abstract it)
- Executor must report binding after start
- Resume flow has additional affinity check

## Migration Path

### Phase 1: Schema Changes
1. Add `executor_session_id`, `executor_type`, `hostname` columns
2. Rename current `session_id` → `executor_session_id` for existing records
3. Generate `session_id` for existing sessions (backfill)

### Phase 2: API Changes
1. Generate `session_id` at run creation
2. Return `session_id` in run creation response
3. Add `POST /sessions/{session_id}/bind` endpoint
4. Change resume API to use `session_id`

### Phase 3: Deprecate session_name
1. Make `session_name` optional in API (deprecated)
2. Update all internal code to use `session_id`
3. Remove `session_name` from schema

### Phase 4: Affinity Enforcement
1. Runner reports `hostname` at registration
2. Resume runs include affinity requirements
3. Claim logic checks affinity match

## Component Responsibilities

| Responsibility | Component |
|----------------|-----------|
| Generate `session_id` | Coordinator (at run creation) |
| Create session record | Coordinator (at run creation, status=pending) |
| Pass `session_id` to executor | Runner (via payload/environment) |
| Get `executor_session_id` from framework | Executor |
| Report binding to coordinator | Executor → `POST /sessions/{id}/bind` |
| Store executor binding | Coordinator |
| Post events using `session_id` | Executor |
| Enforce affinity on resume | Coordinator (dispatch logic) |
| Use `executor_session_id` for framework resume | Executor |

## References

- [ADR-001](./ADR-001-run-session-separation.md) - Run and Session Separation (partially superseded)
- [ADR-002](./ADR-002-agent-runner-architecture.md) - Agent Runner Architecture
- [DATABASE_SCHEMA.md](../components/agent-coordinator/DATABASE_SCHEMA.md) - Current schema
- [DATA_MODELS.md](../components/agent-coordinator/DATA_MODELS.md) - Current data models
