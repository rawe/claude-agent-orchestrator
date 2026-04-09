# Root Workflow State Architecture

## Status

**Draft** - Architectural Design Document

## Executive Summary

This document describes the architecture for introducing a **Root Workflow State** mechanism into the Agent Orchestrator framework. The Root Workflow State is a persistent, schema-bound JSON state that is:

- **Created and owned by a root session** (the initiating orchestrator)
- **Shared across all child sessions** spawned by that root session
- **Persisted in the Agent Coordinator** (SQLite-backed) and independent of LLM context windows
- **Schema-enforced** to guarantee structure for external systems
- **Accessible via HTTP API** for external applications and dashboard visibility
- **Concurrency-safe** with coordinator-side serialization for parallel child updates

The key challenge addressed is that child agents cannot be relied upon to return structured JSON in their normal output. This design introduces a **two-phase child completion model** where the Agent Coordinator enforces a follow-up run requiring the child to explicitly update state via a dedicated State MCP tool.

---

## 1. Core Concept

### 1.1 What is Root Workflow State?

Root Workflow State is a structured JSON document that represents the current state of a multi-agent workflow. Unlike the Context Store (which stores loose documents) or session events (which capture conversation history), the workflow state:

1. **Has a predefined schema** - External systems can rely on specific fields existing
2. **Is owned by a root session** - One session creates and controls the state
3. **Is shared across a session tree** - All descendants can read/update the same state
4. **Is canonical** - The Agent Coordinator is the single source of truth
5. **Is versioned** - Each update increments a version number for conflict detection

### 1.2 Session Tree and State Ownership

```
Root Session (orchestrator)
├── Creates workflow_state with schema
├── Owns workflow_state_id
│
├── Child Session A
│   ├── Receives workflow_state_id via run metadata
│   ├── Can read state via State MCP
│   └── Must update state after work completion (enforced)
│
├── Child Session B
│   ├── Inherits workflow_state_id
│   ├── Can read state via State MCP
│   └── Must update state after work completion (enforced)
│   │
│   └── Grandchild Session B1
│       ├── Inherits workflow_state_id (same as root)
│       └── Same read/update capabilities
│
└── Child Session C
    └── ... (same pattern)
```

**Key Principle:** The `workflow_state_id` is inherited down the session tree. Every session in the tree references the same workflow state created by the root session.

### 1.3 Why Schema-Bound State?

External systems (dashboards, automation tools, CI/CD pipelines) need to:

1. **Display workflow progress** without parsing unstructured text
2. **Trigger actions** based on state transitions (e.g., "when status=ready, deploy")
3. **Integrate reliably** with guaranteed data structure

Without schema enforcement, agents might:
- Return partial or malformed state
- Use inconsistent field names
- Omit required fields
- Return conversational text instead of JSON

The schema guarantees that if a state update succeeds, it conforms to the expected structure.

---

## 2. Data Model

### 2.1 High-Level Entities

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        WORKFLOW STATE ENTITIES                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────┐     ┌──────────────────────┐                      │
│  │    WorkflowSchema    │     │    WorkflowState     │                      │
│  ├──────────────────────┤     ├──────────────────────┤                      │
│  │ schema_id (PK)       │     │ state_id (PK)        │                      │
│  │ name                 │◄────┤ schema_id (FK)       │                      │
│  │ version              │     │ root_session_id (FK) │                      │
│  │ json_schema (TEXT)   │     │ current_data (JSON)  │                      │
│  │ description          │     │ version (INT)        │                      │
│  │ created_at           │     │ created_at           │                      │
│  │ updated_at           │     │ updated_at           │                      │
│  └──────────────────────┘     └──────────────────────┘                      │
│                                        │                                     │
│                                        │ 1:1                                 │
│                                        ▼                                     │
│                               ┌──────────────────────┐                      │
│                               │      Session         │                      │
│                               ├──────────────────────┤                      │
│                               │ session_id (PK)      │                      │
│                               │ session_name         │                      │
│                               │ workflow_state_id    │◄──── NEW COLUMN      │
│                               │ parent_session_name  │                      │
│                               │ status               │                      │
│                               │ ...                  │                      │
│                               └──────────────────────┘                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 WorkflowSchema Table

Stores registered JSON schemas that workflow states must conform to.

```sql
CREATE TABLE workflow_schemas (
    schema_id TEXT PRIMARY KEY,         -- e.g., "schema_abc123"
    name TEXT NOT NULL,                 -- e.g., "code-review-workflow"
    version INTEGER NOT NULL DEFAULT 1, -- Schema version
    json_schema TEXT NOT NULL,          -- JSON Schema (draft-07 or later)
    description TEXT,                   -- Human-readable description
    created_at TEXT NOT NULL,           -- ISO 8601 timestamp
    updated_at TEXT NOT NULL,           -- ISO 8601 timestamp
    UNIQUE(name, version)               -- Name+version must be unique
);
```

**Example JSON Schema:**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["status", "tasks"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["pending", "in_progress", "review", "completed", "failed"]
    },
    "tasks": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "status"],
        "properties": {
          "name": { "type": "string" },
          "status": { "type": "string", "enum": ["pending", "running", "done", "failed"] },
          "result": { "type": "string" },
          "assigned_to": { "type": "string" }
        }
      }
    },
    "summary": { "type": "string" },
    "metadata": { "type": "object" }
  }
}
```

### 2.3 WorkflowState Table

Stores the actual workflow state instances.

```sql
CREATE TABLE workflow_states (
    state_id TEXT PRIMARY KEY,          -- e.g., "wfstate_xyz789"
    schema_id TEXT NOT NULL,            -- FK to workflow_schemas
    root_session_id TEXT NOT NULL,      -- Session that created this state
    current_data TEXT NOT NULL,         -- Current state JSON
    version INTEGER NOT NULL DEFAULT 1, -- Incremented on each update
    created_at TEXT NOT NULL,           -- ISO 8601 timestamp
    updated_at TEXT NOT NULL,           -- ISO 8601 timestamp
    FOREIGN KEY (schema_id) REFERENCES workflow_schemas(schema_id),
    FOREIGN KEY (root_session_id) REFERENCES sessions(session_id)
);
```

**State Versioning:**
- `version` starts at 1 when state is created
- Each successful update increments `version` by 1
- Version is returned in all state responses for optimistic concurrency
- History is NOT stored (current snapshot only) - see Section 6.4 for optional history

### 2.4 Session Table Extension

Add `workflow_state_id` to link sessions to their workflow state:

```sql
ALTER TABLE sessions ADD COLUMN workflow_state_id TEXT
    REFERENCES workflow_states(state_id);
```

This column is:
- **SET** on root session when it creates the workflow state
- **INHERITED** by child sessions when they are spawned
- **NULL** for sessions without workflow state

### 2.5 Identifier Format

All IDs follow the existing pattern in the codebase:

| Entity | Prefix | Example |
|--------|--------|---------|
| Workflow Schema | `schema_` | `schema_abc123def456` |
| Workflow State | `wfstate_` | `wfstate_xyz789abc012` |

---

## 3. Reading and Writing State

### 3.1 Easy Case: Root/Orchestrator Agent

The root (orchestrator) agent can directly read and write state using the State MCP tools:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ROOT SESSION STATE ACCESS                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Root Session                                                        │
│      │                                                               │
│      │ 1. Create state with schema                                   │
│      │    state_create(schema_name="task-workflow",                  │
│      │                 initial_data={...})                           │
│      │                                                               │
│      ▼                                                               │
│  State MCP ─────────────────────────► Agent Coordinator              │
│      │                                     │                         │
│      │ 2. Read current state               │ Validate against schema │
│      │    state_read()                     │ Store in SQLite         │
│      │                                     │ Return state_id         │
│      ▼                                     │                         │
│  State MCP ◄───────────────────────────────┘                         │
│      │                                                               │
│      │ 3. Update state                                               │
│      │    state_update(data={...})                                   │
│      │                                                               │
│      ▼                                                               │
│  State MCP ─────────────────────────► Agent Coordinator              │
│                                            │                         │
│                                            │ Validate against schema │
│                                            │ Increment version       │
│                                            │ Store in SQLite         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Operations available to root:**
- `state_create(schema_name, initial_data)` - Create new workflow state
- `state_read()` - Read current state and version
- `state_update(data)` - Replace state with new data (validated)
- `state_patch(operations)` - Apply JSON Patch operations (RFC 6902)

### 3.2 Complex Case: Child Agent State Updates

Child agents receive the `workflow_state_id` via run metadata (see Section 5). They can read state freely, but writing is coordinated through the Agent Coordinator:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CHILD SESSION STATE ACCESS                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Child Session                                                       │
│      │                                                               │
│      │ Has: workflow_state_id (inherited from parent)                │
│      │                                                               │
│      │ 1. Read state (always allowed)                                │
│      │    state_read()                                               │
│      │                                                               │
│      ▼                                                               │
│  State MCP ─────────────────────────► Agent Coordinator              │
│      │                                     │                         │
│      │                                     │ Lookup by state_id      │
│      │◄────────────────────────────────────┘ Return current_data     │
│      │                                                               │
│      │ 2. Update state (coordinator-mediated)                        │
│      │    state_update(data={...}, expected_version=N)               │
│      │                                                               │
│      ▼                                                               │
│  State MCP ─────────────────────────► Agent Coordinator              │
│                                            │                         │
│                                            │ Acquire lock            │
│                                            │ Check version           │
│                                            │ Validate schema         │
│                                            │ Apply update            │
│                                            │ Increment version       │
│                                            │ Release lock            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 Why the Agent Coordinator Must Be the Canonical Writer

The Agent Coordinator is the single source of truth for workflow state because:

1. **Schema Enforcement:** The coordinator validates all updates against the schema
2. **Concurrency Control:** The coordinator serializes concurrent updates
3. **Version Management:** The coordinator tracks and increments versions
4. **Persistence:** The coordinator owns the SQLite database
5. **Audit Trail:** The coordinator can log all state changes

Child agents CANNOT:
- Write directly to the database (no access)
- Bypass schema validation
- Update without coordinator mediation

### 3.4 State MCP Server Design

A dedicated MCP server provides state operations to agents:

**Tools:**

| Tool | Description | Parameters |
|------|-------------|------------|
| `state_create` | Create new workflow state | `schema_name`, `initial_data` |
| `state_read` | Read current state | (none - uses session's state_id) |
| `state_update` | Replace entire state | `data`, `expected_version` (optional) |
| `state_patch` | Apply JSON Patch | `operations`, `expected_version` (optional) |
| `state_schema` | Get schema definition | (none - uses session's schema_id) |

**Session Context:**
The State MCP reads `WORKFLOW_STATE_ID` from environment (set by Runner) to identify which state the agent should access.

**HTTP API Backend:**
The State MCP calls Agent Coordinator HTTP endpoints:

```
POST   /workflow-state                    # Create state (root only)
GET    /workflow-state/{state_id}         # Read state
PUT    /workflow-state/{state_id}         # Update state (full replace)
PATCH  /workflow-state/{state_id}         # Partial update (JSON Patch)
GET    /workflow-schemas/{name}           # Get schema definition
```

---

## 4. Child Agent State Updates (Enforced Two-Phase Model)

### 4.1 The Problem

Child agents cannot be relied upon to return structured JSON in their normal output because:

1. **LLM output is conversational** - Agents explain, summarize, and discuss
2. **Tool output varies** - Different tools return different formats
3. **Context window limits** - Full state may not fit in final response
4. **No enforcement mechanism** - Agents can ignore state update requests

### 4.2 The Solution: Two-Phase Child Completion

The Agent Coordinator enforces a two-phase completion model:

**Phase 1: Work Completion**
- Child executes its task normally
- Output can be unstructured (prose, code, analysis, etc.)
- Child finishes its work and session stops

**Phase 2: State Update (Enforced)**
- Agent Coordinator detects child completion (session_stop event)
- Before triggering parent callback, coordinator resumes child with state update prompt
- Child MUST call `state_update` or `state_patch` tool
- Coordinator verifies state was updated before proceeding

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    TWO-PHASE CHILD COMPLETION                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐                    ┌───────────────────┐               │
│  │ Child Agent  │                    │ Agent Coordinator │               │
│  └──────┬───────┘                    └─────────┬─────────┘               │
│         │                                      │                         │
│         │ PHASE 1: Work                        │                         │
│         │ ═══════════                          │                         │
│         │                                      │                         │
│         │  1. Execute task                     │                         │
│         │     (research, code, analyze)        │                         │
│         │                                      │                         │
│         │  2. Session stops (work complete)    │                         │
│         │ ─────────────────────────────────────►                         │
│         │     event: session_stop              │                         │
│         │                                      │                         │
│         │                                      │ 3. Detect completion    │
│         │                                      │    Check: has workflow   │
│         │                                      │    state? YES            │
│         │                                      │                         │
│         │ PHASE 2: State Update                │                         │
│         │ ══════════════════════               │                         │
│         │                                      │                         │
│         │  4. Resume with state prompt         │                         │
│         │ ◄─────────────────────────────────────                         │
│         │     "Update workflow state with      │                         │
│         │      your task results..."           │                         │
│         │                                      │                         │
│         │  5. Child calls state_update()       │                         │
│         │ ─────────────────────────────────────►                         │
│         │                                      │ 6. Validate & store     │
│         │                                      │                         │
│         │  7. Session stops (state updated)    │                         │
│         │ ─────────────────────────────────────►                         │
│         │                                      │                         │
│         │                                      │ 8. Mark state_updated   │
│         │                                      │                         │
│         │                                      │ 9. Trigger parent       │
│         │                                      │    callback             │
│         │                                      │                         │
│         ▼                                      ▼                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.3 How the Coordinator Differentiates Phases

The Agent Coordinator tracks completion state using a new field on the session:

```sql
ALTER TABLE sessions ADD COLUMN state_update_status TEXT
    CHECK (state_update_status IN ('pending', 'completed', 'failed', 'skipped'));
```

**State Machine:**

```
Session Created
      │
      ▼
  [status: running]
  [state_update_status: NULL]
      │
      │ session_stop event (Phase 1 complete)
      ▼
  [status: finished]
  [state_update_status: pending]  ◄── Coordinator sees: needs state update
      │
      │ Coordinator resumes with state prompt
      ▼
  [status: running]
  [state_update_status: pending]
      │
      │ state_update() tool called successfully
      ▼
  [status: running]
  [state_update_status: completed]
      │
      │ session_stop event (Phase 2 complete)
      ▼
  [status: finished]
  [state_update_status: completed]  ◄── Coordinator sees: ready for callback
      │
      │ Parent callback triggered
      ▼
```

**Decision Logic in Callback Processor:**

```python
def on_child_completed(child_session_name, ...):
    session = get_session_by_name(child_session_name)

    # Check if child has workflow state
    if session.workflow_state_id is None:
        # No workflow state - proceed with normal callback
        self._deliver_callback_to_parent(session)
        return

    # Check state update status
    if session.state_update_status == 'pending':
        # Phase 1 just completed - need to trigger state update
        self._create_state_update_run(session)
        return

    if session.state_update_status == 'completed':
        # Phase 2 completed - safe to trigger parent callback
        self._deliver_callback_to_parent(session)
        return

    if session.state_update_status == 'failed':
        # State update failed after retries - notify parent of failure
        self._deliver_callback_to_parent(session, child_failed=True,
            error="Child failed to update workflow state")
        return
```

### 4.4 State Update Prompt (Phase 2)

When resuming the child for state update, the coordinator uses a structured prompt:

```markdown
## Required: Update Workflow State

Your task is complete. You must now update the workflow state to record your results.

**Current State:**
```json
{current_state}
```

**Schema:**
```json
{schema}
```

**Instructions:**
1. Review your work results from this session
2. Call the `state_update` or `state_patch` tool to record:
   - Task status (completed/failed)
   - Results or outputs
   - Any relevant metadata
3. The state must conform to the schema above

**IMPORTANT:** You MUST call `state_update` or `state_patch` before completing.
Failure to update state will be treated as a task failure.
```

### 4.5 Retry and Timeout Handling

**Retry Logic:**

| Attempt | Action |
|---------|--------|
| 1 | Resume with state update prompt |
| 2 | Resume with stronger prompt + warning |
| 3 | Resume with minimal prompt + explicit tool requirement |
| 4+ | Mark as failed, notify parent |

**Configuration:**

```python
STATE_UPDATE_MAX_RETRIES = 3        # Max resume attempts for state update
STATE_UPDATE_TIMEOUT = 120          # Seconds to wait for state update run
STATE_UPDATE_RETRY_DELAY = 5        # Seconds between retries
```

**Timeout Handling:**

If the state update run takes too long (e.g., agent is stuck):
1. Runner reports run timeout
2. Coordinator increments retry counter
3. If retries exhausted → mark `state_update_status='failed'`
4. Trigger parent callback with failure notification

### 4.6 When the Parent Callback is Delivered

The parent callback is ONLY delivered when:

1. **Child has no workflow state** - Normal callback (immediate)
2. **Child has workflow state AND state_update_status='completed'** - Callback after state update
3. **Child has workflow state AND state_update_status='failed'** - Callback with failure

The parent callback message includes:

```markdown
## Child Session Completed

Session `{child_name}` has completed.

**Workflow State Updated:** {yes/no}
**State Version:** {version}
**State Update Status:** {completed/failed}

{If failed: "Warning: Child failed to update workflow state. Error: {error}"}

To retrieve detailed results: `ao-get-result {child_name}`
To read current workflow state: Use the `state_read` tool
```

---

## 5. Parent ↔ Child Handover

### 5.1 Passing workflow_state_id to Child Sessions

The `workflow_state_id` is propagated through the session hierarchy using the same mechanism as `parent_session_name`:

**Option A: Environment Variable (Recommended)**

```
┌─────────────────────────────────────────────────────────────────────┐
│                  WORKFLOW STATE ID PROPAGATION                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. Runner starts root session:                                      │
│     WORKFLOW_STATE_ID={state_id} ao-start root-orchestrator ...      │
│                                                                      │
│  2. Root session calls MCP to start child (callback=true):           │
│     start_agent_session(name="child", ...)                           │
│                                                                      │
│  3. MCP server propagates env var:                                   │
│     - Reads WORKFLOW_STATE_ID from own environment                   │
│     - Sets WORKFLOW_STATE_ID={same_id} in child subprocess           │
│                                                                      │
│  4. ao-start reads env var:                                          │
│     - Reads WORKFLOW_STATE_ID                                        │
│     - Passes to POST /sessions API                                   │
│     - Stored in sessions.workflow_state_id                           │
│                                                                      │
│  5. Child's State MCP reads env var:                                 │
│     - Uses WORKFLOW_STATE_ID for all state operations                │
│     - No need to pass state_id in tool parameters                    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Option B: Run Metadata**

Alternative approach using explicit run metadata:

```json
{
  "run_id": "run_abc123",
  "type": "start_session",
  "session_name": "child-task",
  "prompt": "...",
  "metadata": {
    "workflow_state_id": "wfstate_xyz789",
    "parent_session_name": "orchestrator"
  }
}
```

**Recommendation:** Use Environment Variable (Option A) for consistency with existing `AGENT_SESSION_NAME` pattern.

### 5.2 Session Creation with Workflow State

When creating a child session, the API accepts `workflow_state_id`:

```json
POST /sessions
{
  "session_id": "uuid-child",
  "session_name": "child-task",
  "parent_session_name": "orchestrator",
  "workflow_state_id": "wfstate_xyz789"
}
```

The session is created with:
- `workflow_state_id` linked to root's state
- `state_update_status` = NULL (will be set to 'pending' after Phase 1)

### 5.3 Parent Callback Metadata

When the parent is resumed via callback, the callback message includes state-related metadata:

**Current Callback (Existing):**
```
Child session 'child-task' has completed.
```

**Enhanced Callback (With State):**
```
## Child Session Completed

Session: `child-task`
Status: finished
Workflow State Version: 7
State Update: completed

The workflow state has been updated. Use `state_read` to see current state.
```

**Run Metadata for Parent Resume:**

```json
{
  "run_id": "run_callback_001",
  "type": "resume_session",
  "session_name": "orchestrator",
  "prompt": "Child completed...",
  "metadata": {
    "callback_source": "child-task",
    "workflow_state_version": 7,
    "state_update_status": "completed"
  }
}
```

### 5.4 Integration with Existing Callback Processor

The callback processor (`callback_processor.py`) is extended:

```python
class CallbackProcessor:
    def on_child_completed(
        self,
        child_session_name: str,
        child_result: Optional[str] = None,
        child_failed: bool = False,
        error: Optional[str] = None
    ):
        session = get_session_by_name(child_session_name)

        # NEW: Check for workflow state handling
        if session.workflow_state_id:
            if session.state_update_status is None:
                # First completion - set to pending and trigger state update
                update_session_state_update_status(session.session_id, 'pending')
                self._create_state_update_run(session)
                return  # Don't callback parent yet

            if session.state_update_status == 'pending':
                # This shouldn't happen - log warning
                logger.warning(f"Child {child_session_name} completed but state_update_status is still pending")
                return

        # Proceed with normal callback (existing logic)
        # ... existing callback code ...

    def _create_state_update_run(self, session):
        """Create a resume run for state update phase."""
        current_state = get_workflow_state(session.workflow_state_id)
        schema = get_workflow_schema(current_state.schema_id)

        prompt = self._build_state_update_prompt(current_state, schema)

        run_queue.add_run(RunCreate(
            type=RunType.RESUME_SESSION,
            session_name=session.session_name,
            prompt=prompt,
            # Mark this as a state-update run
            metadata={"state_update_run": True}
        ))
```

---

## 6. Concurrency Model

### 6.1 Parallel Children Updating Shared State

When multiple child sessions run in parallel and attempt to update the same workflow state:

```
┌─────────────────────────────────────────────────────────────────────┐
│                 CONCURRENT STATE UPDATE SCENARIO                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Time ──────────────────────────────────────────────────────────►    │
│                                                                      │
│  Child A  ════════════════════╗                                      │
│           Phase 1 (work)      ║ completes                            │
│                               ╠═══════════════════╗                  │
│                               ║ Phase 2 (state)   ║ completes        │
│                               ║                   ║                  │
│  Child B  ════════════════════════════════╗       ║                  │
│           Phase 1 (work)                  ║ completes                │
│                                           ╠═══════════════╗          │
│                                           ║ Phase 2       ║ completes│
│                                           ║               ║          │
│  Child C  ════════════════════════════════════════════════╗          │
│           Phase 1 (work)                                  ║ completes│
│                                                           ╠════════╗ │
│                                                           ║ Phase 2║ │
│                                                                    ║ │
│                                                                      │
│  STATE UPDATES:                                                      │
│  ─────────────                                                       │
│         v1 ──────► A updates ──► v2                                  │
│                                  │                                   │
│                                  ▼                                   │
│                               v2 ──────► B updates ──► v3            │
│                                                        │             │
│                                                        ▼             │
│                                                     v3 ──► C ──► v4  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 Coordinator-Side Serialization

The Agent Coordinator uses a mutex to serialize state updates:

```python
# In Agent Coordinator
state_locks: Dict[str, threading.Lock] = {}  # state_id → Lock

def update_workflow_state(state_id: str, new_data: dict, expected_version: Optional[int] = None):
    # Get or create lock for this state
    if state_id not in state_locks:
        state_locks[state_id] = threading.Lock()

    with state_locks[state_id]:
        # Read current state
        current = get_workflow_state(state_id)

        # Optimistic concurrency check
        if expected_version is not None and current.version != expected_version:
            raise VersionConflictError(
                f"Expected version {expected_version}, but current is {current.version}"
            )

        # Validate against schema
        schema = get_workflow_schema(current.schema_id)
        validate_json(new_data, schema.json_schema)

        # Apply update
        new_version = current.version + 1
        save_workflow_state(state_id, new_data, new_version)

        return new_version
```

### 6.3 Optimistic Versioning (Optional)

For advanced use cases, clients can use optimistic concurrency:

**Without Version Check (Default):**
```json
PUT /workflow-state/{state_id}
{
  "data": { ... }
}
```
- Update always succeeds (if valid)
- Last write wins

**With Version Check:**
```json
PUT /workflow-state/{state_id}
{
  "data": { ... },
  "expected_version": 5
}
```
- Update only succeeds if current version == 5
- Returns 409 Conflict if version mismatch
- Client must re-read state and retry

**Recommendation for Child State Updates:**
- Don't require version check for child state updates
- Use "last write wins" for simplicity
- Each child updates independent portions of state
- Root orchestrator can use version checks for critical updates

### 6.4 State Merging Strategy

When multiple children update different portions of state, use JSON Patch or merge strategies:

**Option A: Full Replace (Simple)**
- Each child sends complete state
- Last update overwrites previous
- Risk: One child may overwrite another's changes

**Option B: JSON Patch (Recommended)**
- Children send targeted patches
- Patches applied sequentially
- Each child only modifies its own section

**Example JSON Patch:**
```json
PATCH /workflow-state/{state_id}
{
  "operations": [
    { "op": "replace", "path": "/tasks/0/status", "value": "done" },
    { "op": "add", "path": "/tasks/0/result", "value": "Analysis complete" }
  ]
}
```

**Option C: State Sections (Advanced)**
- State divided into sections by task/agent
- Each child owns its section
- Coordinator merges sections

**Recommendation:** Start with JSON Patch (Option B) for targeted updates.

### 6.5 Why Snapshot + Controlled Updates

The design uses snapshot-based state (current JSON only) rather than event sourcing because:

1. **Simplicity:** Single source of truth, no event replay
2. **Performance:** Direct read without reconstruction
3. **External Access:** External systems see current state immediately
4. **Schema Enforcement:** Validate entire state on each update

**Optional History Table (Future):**
```sql
CREATE TABLE workflow_state_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    state_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    data TEXT NOT NULL,
    changed_by_session TEXT,
    changed_at TEXT NOT NULL,
    FOREIGN KEY (state_id) REFERENCES workflow_states(state_id)
);
```

---

## 7. External & Dashboard Access

### 7.1 HTTP API Endpoints

**Schema Management:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/workflow-schemas` | Register new schema |
| `GET` | `/workflow-schemas` | List all schemas |
| `GET` | `/workflow-schemas/{name}` | Get schema by name |
| `GET` | `/workflow-schemas/{name}/versions` | List schema versions |

**State Management:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/workflow-states` | Create new state (root session) |
| `GET` | `/workflow-states` | List all states |
| `GET` | `/workflow-states/{state_id}` | Get state by ID |
| `PUT` | `/workflow-states/{state_id}` | Update state (full replace) |
| `PATCH` | `/workflow-states/{state_id}` | Partial update (JSON Patch) |
| `DELETE` | `/workflow-states/{state_id}` | Delete state |

**Query Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/sessions/{id}/workflow-state` | Get state for session |
| `GET` | `/workflow-states?root_session={name}` | Filter by root session |

### 7.2 API Response Format

**Get Workflow State:**
```json
GET /workflow-states/wfstate_xyz789

{
  "state_id": "wfstate_xyz789",
  "schema_id": "schema_abc123",
  "schema_name": "code-review-workflow",
  "root_session_id": "session-orchestrator-001",
  "root_session_name": "orchestrator",
  "version": 7,
  "current_data": {
    "status": "in_progress",
    "tasks": [
      { "name": "lint", "status": "done", "result": "No issues" },
      { "name": "test", "status": "running", "assigned_to": "test-runner" },
      { "name": "review", "status": "pending" }
    ],
    "summary": "2/3 tasks complete"
  },
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:35:00Z"
}
```

### 7.3 Dashboard Integration

The dashboard can observe workflow state in real-time:

**Session Detail View:**
- Show workflow state if session has `workflow_state_id`
- Display current state JSON with syntax highlighting
- Show schema name and version
- Show state version and last updated

**Workflow State View (New):**
- List all active workflow states
- Filter by root session or schema
- Show state timeline (if history enabled)
- Real-time updates via WebSocket

### 7.4 WebSocket Events (High-Level)

Extend existing WebSocket to broadcast state changes:

```json
{
  "event_type": "workflow_state_updated",
  "state_id": "wfstate_xyz789",
  "version": 8,
  "updated_by_session": "child-task-1",
  "timestamp": "2025-01-15T10:40:00Z"
}
```

**Subscription Model:**
- Dashboard subscribes to state updates by `state_id`
- Broadcast on each successful state update
- Include version for client-side diffing

---

## 8. Integration Points in This Repository

### 8.1 Agent Coordinator Extensions

**Files to modify:**

| File | Changes |
|------|---------|
| `servers/agent-coordinator/database.py` | Add workflow_schemas, workflow_states tables; extend sessions table |
| `servers/agent-coordinator/models.py` | Add WorkflowSchema, WorkflowState models; extend Session model |
| `servers/agent-coordinator/main.py` | Add workflow state HTTP endpoints |
| `servers/agent-coordinator/services/callback_processor.py` | Add two-phase completion logic |
| `servers/agent-coordinator/services/run_queue.py` | Add state_update_run metadata field |

**New files:**

| File | Purpose |
|------|---------|
| `servers/agent-coordinator/services/workflow_state.py` | State management service |
| `servers/agent-coordinator/routers/workflow_state.py` | HTTP endpoints for state |
| `servers/agent-coordinator/routers/workflow_schema.py` | HTTP endpoints for schemas |

### 8.2 State MCP Server (New)

**Location:** `mcps/workflow-state/`

**Structure:**
```
mcps/workflow-state/
├── pyproject.toml
├── src/
│   ├── __init__.py
│   ├── server.py           # FastMCP server
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── state_read.py   # state_read tool
│   │   ├── state_update.py # state_update tool
│   │   ├── state_patch.py  # state_patch tool
│   │   └── state_create.py # state_create tool
│   └── api_client.py       # HTTP client for Agent Coordinator
└── docs/
    └── TOOLS_REFERENCE.md
```

**MCP Server Configuration:**
```json
{
  "mcpServers": {
    "workflow-state": {
      "type": "http",
      "url": "http://localhost:9501/mcp",
      "headers": {
        "X-Workflow-State-Id": "${WORKFLOW_STATE_ID}"
      }
    }
  }
}
```

### 8.3 Agent Runner Extensions

**Files to modify:**

| File | Changes |
|------|---------|
| `servers/agent-runner/lib/executor.py` | Pass WORKFLOW_STATE_ID env var to subprocess |
| `servers/agent-runner/lib/api_client.py` | Handle state_update_run responses |

### 8.4 CLI Commands Extensions

**Files to modify:**

| File | Changes |
|------|---------|
| `plugins/orchestrator/skills/orchestrator/commands/ao-start` | Read/pass WORKFLOW_STATE_ID |
| `plugins/orchestrator/skills/orchestrator/commands/ao-resume` | Read/pass WORKFLOW_STATE_ID |
| `plugins/orchestrator/skills/orchestrator/commands/lib/session_api.py` | Include workflow_state_id in session creation |

### 8.5 Dashboard Extensions

**Files to modify:**

| File | Changes |
|------|---------|
| `dashboard/src/types/` | Add WorkflowState, WorkflowSchema types |
| `dashboard/src/services/` | Add workflowStateService.ts |
| `dashboard/src/pages/` | Add WorkflowStates page |
| `dashboard/src/components/` | Add WorkflowStateViewer component |

---

## 9. Sequence Diagrams

### 9.1 Root Session Creates Workflow State

```
┌──────────────┐    ┌─────────────┐    ┌──────────────────┐
│ Root Session │    │  State MCP  │    │ Agent Coordinator│
└──────┬───────┘    └──────┬──────┘    └────────┬─────────┘
       │                   │                    │
       │ state_create      │                    │
       │ (schema_name,     │                    │
       │  initial_data)    │                    │
       │──────────────────►│                    │
       │                   │                    │
       │                   │ POST /workflow-    │
       │                   │ states             │
       │                   │───────────────────►│
       │                   │                    │
       │                   │                    │ Lookup schema
       │                   │                    │ Validate data
       │                   │                    │ Create state
       │                   │                    │ Link to session
       │                   │                    │
       │                   │    201 Created     │
       │                   │◄───────────────────│
       │                   │                    │
       │  {state_id,       │                    │
       │   version: 1}     │                    │
       │◄──────────────────│                    │
       │                   │                    │
```

### 9.2 Child State Update (Two-Phase)

```
┌─────────────┐   ┌──────────────────┐   ┌─────────────┐   ┌───────────┐
│Child Session│   │Agent Coordinator │   │Agent Runner │   │ State MCP │
└──────┬──────┘   └────────┬─────────┘   └──────┬──────┘   └─────┬─────┘
       │                   │                    │                │
       │ PHASE 1: Work completes               │                │
       │ ═══════════════════════               │                │
       │                   │                    │                │
       │ session_stop      │                    │                │
       │──────────────────►│                    │                │
       │                   │                    │                │
       │                   │ Has workflow_state? YES             │
       │                   │ state_update_status = pending       │
       │                   │                    │                │
       │ PHASE 2: State Update                 │                │
       │ ═════════════════════                 │                │
       │                   │                    │                │
       │                   │ Create resume run  │                │
       │                   │───────────────────►│                │
       │                   │                    │                │
       │◄───────────────────────────────────────│                │
       │      Resume with state prompt          │                │
       │                   │                    │                │
       │ state_update(data)│                    │                │
       │──────────────────────────────────────────────────────────►
       │                   │                    │                │
       │                   │◄───────────────────────────────────────
       │                   │  PUT /workflow-states/{id}          │
       │                   │                    │                │
       │                   │  Validate & store  │                │
       │                   │  state_update_status = completed    │
       │                   │                    │                │
       │ session_stop      │                    │                │
       │──────────────────►│                    │                │
       │                   │                    │                │
       │                   │ state_update_status == completed    │
       │                   │ Trigger parent callback             │
       │                   │                    │                │
```

### 9.3 Concurrent Child Updates

```
┌─────────┐  ┌─────────┐  ┌──────────────────┐  ┌────────────────┐
│ Child A │  │ Child B │  │Agent Coordinator │  │ Workflow State │
└────┬────┘  └────┬────┘  └────────┬─────────┘  └───────┬────────┘
     │            │               │                    │
     │            │               │         state v=5  │
     │            │               │◄───────────────────│
     │            │               │                    │
     │ state_update(dataA)        │                    │
     │───────────────────────────►│                    │
     │            │               │ Acquire lock       │
     │            │               │ Validate dataA     │
     │            │               │ Update state       │
     │            │               │───────────────────►│ v=6
     │            │               │ Release lock       │
     │◄───────────────────────────│                    │
     │   {version: 6}             │                    │
     │            │               │                    │
     │            │ state_update(dataB)                │
     │            │──────────────►│                    │
     │            │               │ Acquire lock       │
     │            │               │ Validate dataB     │
     │            │               │ Update state       │
     │            │               │───────────────────►│ v=7
     │            │               │ Release lock       │
     │            │◄──────────────│                    │
     │            │ {version: 7}  │                    │
     │            │               │                    │
```

---

## 10. Assumptions and Open Questions

### 10.1 Assumptions

1. **Schema Registration:** Schemas are registered before workflows start (not created by agents at runtime)
2. **State Size:** Workflow state is reasonably small (< 1MB JSON)
3. **Session Hierarchy:** Session tree depth is limited (practical limit ~10 levels)
4. **Network Reliability:** Agent Coordinator is available for all state operations
5. **Agent Cooperation:** Agents will attempt to follow state update prompts (enforcement handles failures)

### 10.2 Open Questions

1. **Schema Versioning:** How to handle schema migrations when schema changes?
   - Option A: Force new state for new schema version
   - Option B: Support migration scripts
   - Option C: Allow backward-compatible changes only

2. **State Cleanup:** When should workflow states be deleted?
   - When root session is deleted?
   - After configurable retention period?
   - Manual deletion only?

3. **State Size Limits:** Should there be a maximum state size?
   - Risk: Large states slow down updates
   - Option: Configurable limit with warning

4. **Cross-Workflow State:** Can agents access states from other workflows?
   - Current design: No (session-scoped)
   - Future consideration: Read-only access with explicit permission

5. **Partial State Reads:** Should agents be able to read only portions of state?
   - Reduces context window usage
   - Adds API complexity
   - Could use JSON Pointer for targeted reads

6. **State Locking Timeout:** How long should the state lock be held?
   - Risk: Long validation blocks other updates
   - Option: Configurable timeout with automatic release

---

## 11. Success Criteria

A developer implementing this system should be able to:

1. **Register a workflow schema** via HTTP API
2. **Create a workflow state** from a root session using State MCP
3. **Spawn child sessions** that inherit the workflow_state_id
4. **Have children automatically prompted** for state updates after work completion
5. **Validate state updates** against the registered schema
6. **Handle concurrent updates** from parallel children
7. **Query workflow state** from external applications via HTTP API
8. **View workflow state** in the dashboard
9. **Receive parent callbacks** only after state updates complete
10. **Handle failures** when children don't update state

The design works with:
- Unstructured child output (enforced Phase 2 handles state updates)
- Parallel child execution (coordinator serialization)
- External system integration (schema-guaranteed structure)
- Existing callback mechanism (extended, not replaced)

---

## 12. Related Documents

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Overall system architecture
- [agent-callback-architecture.md](./agent-callback-architecture.md) - Callback mechanism design
- [DATABASE_SCHEMA.md](../agent-coordinator/DATABASE_SCHEMA.md) - Current database schema
- [DATA_MODELS.md](../agent-coordinator/DATA_MODELS.md) - Existing data models
- [ADR-003-callback-based-async.md](../adr/ADR-003-callback-based-async.md) - Callback decision record
