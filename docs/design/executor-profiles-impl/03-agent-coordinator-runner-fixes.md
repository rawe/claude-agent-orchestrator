# Session 3b: Agent Runner Client-Side Fixes

**Status:** Done (Superseded by Session 4)
**Parent Session:** [03-agent-coordinator.md](./03-agent-coordinator.md) (Done)
**Design Document:** [`../executor-profiles.md`](../executor-profiles.md)
**Implemented By:** [04-executor-runner-communication-refactor.md](./04-executor-runner-communication-refactor.md) (Done)

---

## Current State

**All requirements have been fulfilled by Session 4's architectural refactor.**

Session 4 implemented the Runner Gateway, which provides a superior solution:
- Executors now use a simplified `bind()` API that only sends data they own (`executor_session_id`, `project_dir`)
- The Runner Gateway enriches requests with runner-owned data (`hostname`, `executor_profile`)
- No hardcoded profile names in executors - clean separation of concerns

**Original Issue:** Executors were providing information they don't own (hostname, executor_profile). This has been properly resolved.

---

## Context

Session 3 updated the **Agent Coordinator** to use `executor_profile` instead of `executor_type`. However, the **client-side code in Agent Runner** that communicates with the coordinator still uses the old `executor_type` naming.

This causes a **critical bug**: when executors call the `/sessions/{id}/bind` endpoint, the coordinator's `SessionBind` Pydantic model expects `executor_profile` but receives `executor_type`, causing validation failure.

### What Was Changed in Session 3

**Agent Coordinator files (already updated):**
- `servers/agent-coordinator/models.py` - `SessionBind.executor_profile`
- `servers/agent-coordinator/database.py` - column renamed
- `servers/agent-coordinator/main.py` - API endpoints expect `executor_profile`

**Agent Runner registration (already updated):**
- `servers/agent-runner/lib/api_client.py` - uses `executor_profile`
- `servers/agent-runner/agent-runner` - uses `executor_profile`

### What Still Needs Updating

The executor-side code that binds sessions and updates metadata still uses `executor_type`.

---

## Files to Modify

| File | Component | Priority |
|------|-----------|----------|
| `servers/agent-runner/lib/session_client.py` | Session Client | Critical |
| `servers/agent-runner/executors/claude-code/lib/claude_client.py` | Claude Code Executor | Critical |
| `servers/agent-runner/executors/test-executor/ao-test-exec` | Test Executor | Medium |
| `servers/agent-runner/lib/agent_orchestrator_mcp/schemas.py` | MCP Schemas | Medium |

> **Note:** The deprecated MCP server at `mcps/agent-orchestrator/` should NOT be updated.

---

## Section 1: Session Client

**File:** `servers/agent-runner/lib/session_client.py`

This is the HTTP client that executors use to communicate with the Agent Coordinator.

### Changes Required

#### 1.1 `bind_session_executor()` function (around line 90)

**Current:**
```python
def bind_session_executor(
    session_id: str,
    executor_session_id: str,
    hostname: str,
    executor_type: str,  # <-- RENAME
    project_dir: Optional[str] = None,
    ...
):
```

**Change to:**
```python
def bind_session_executor(
    session_id: str,
    executor_session_id: str,
    hostname: str,
    executor_profile: str,  # <-- RENAMED
    project_dir: Optional[str] = None,
    ...
):
```

#### 1.2 JSON payload in `bind_session_executor()` (around line 113)

**Current:**
```python
data = {
    "executor_session_id": executor_session_id,
    "hostname": hostname,
    "executor_type": executor_type,  # <-- RENAME KEY
}
```

**Change to:**
```python
data = {
    "executor_session_id": executor_session_id,
    "hostname": hostname,
    "executor_profile": executor_profile,  # <-- RENAMED
}
```

#### 1.3 `update_session()` function (around lines 161, 170-171)

**Current:**
```python
def update_session(
    session_id: str,
    ...
    executor_type: Optional[str] = None,  # <-- RENAME
    ...
):
    ...
    if executor_type is not None:
        data["executor_type"] = executor_type  # <-- RENAME KEY
```

**Change to:**
```python
def update_session(
    session_id: str,
    ...
    executor_profile: Optional[str] = None,  # <-- RENAMED
    ...
):
    ...
    if executor_profile is not None:
        data["executor_profile"] = executor_profile  # <-- RENAMED
```

---

## Section 2: Claude Code Executor

**File:** `servers/agent-runner/executors/claude-code/lib/claude_client.py`

This executor calls `session_client.bind_session_executor()` with the `executor_type` parameter.

### Changes Required

#### 2.1 All calls to `bind_session_executor()` and `update_session()`

Search for all occurrences of `executor_type` in this file (approximately lines 177, 196, 301, 404, 423, 451).

**Example current:**
```python
bind_session_executor(
    session_id=session_id,
    executor_session_id=executor_session_id,
    hostname=hostname,
    executor_type="claude-code",  # <-- RENAME
    ...
)
```

**Change to:**
```python
bind_session_executor(
    session_id=session_id,
    executor_session_id=executor_session_id,
    hostname=hostname,
    executor_profile=self.executor_profile,  # <-- Use profile from config
    ...
)
```

#### 2.2 Consider: Should the executor know its profile?

Currently the executor hardcodes `"claude-code"` as the type. With the new profile system, the executor should receive its profile name from the invocation payload or config.

**Check the invocation schema** - the `executor_config` in the invocation payload may contain the profile name. If so, use it instead of hardcoding.

---

## Section 3: Test Executor

**File:** `servers/agent-runner/executors/test-executor/ao-test-exec`

### Changes Required

#### 3.1 Call to `bind_session_executor()` (around line 98)

**Current:**
```python
bind_session_executor(
    ...
    executor_type="test-executor",  # <-- RENAME
    ...
)
```

**Change to:**
```python
bind_session_executor(
    ...
    executor_profile="test",  # <-- Use appropriate profile name
    ...
)
```

---

## Section 4: Agent Orchestrator MCP Schemas

**File:** `servers/agent-runner/lib/agent_orchestrator_mcp/schemas.py`

This file defines the input schemas for MCP tools that spawn/resume agent sessions.

### Changes Required

#### 4.1 Docstring in `SpawnAgentInput` (around line 42)

**Current:**
```python
"""
...
May contain: hostname, project_dir, executor_type, tags
"""
```

**Change to:**
```python
"""
...
May contain: hostname, project_dir, executor_profile, tags
"""
```

#### 4.2 `get_executor_type()` method (around lines 53-55)

**Current:**
```python
def get_executor_type(self) -> Optional[str]:
    """Get executor_type from additional demands."""
    return self.additional_demands.get("executor_type")
```

**Change to:**
```python
def get_executor_profile(self) -> Optional[str]:
    """Get executor_profile from additional demands."""
    return self.additional_demands.get("executor_profile")
```

#### 4.3 Update any callers of `get_executor_type()`

Search the codebase for any code calling `get_executor_type()` and update to `get_executor_profile()`.

---

## Testing Plan

After making changes:

```bash
# 1. Delete old database (schema changed)
rm -f .agent-orchestrator/observability.db

# 2. Start coordinator
cd servers/agent-coordinator && AUTH_ENABLED=false uv run python -m main

# 3. Start runner with a profile
mkdir -p .agent-orchestrator/runner-test
PROJECT_DIR=.agent-orchestrator/runner-test ./servers/agent-runner/agent-runner --profile coding

# 4. Create a run and verify session binding works
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{"type":"start_session","prompt":"test binding"}'

# 5. Check session has executor_profile set
curl http://localhost:8765/sessions | python -m json.tool
```

---

## Definition of Done

- [x] `session_client.py`: API simplified - uses `bind()` without executor_profile (gateway enriches)
- [x] `claude_client.py`: Uses simplified `bind()` API
- [x] `ao-test-exec`: Uses simplified `bind()` API
- [x] `schemas.py`: Docstring and `get_executor_type()` → `get_executor_profile()`
- [x] Session binding works end-to-end (via Runner Gateway)
- [x] Update this file status to Done

### Resolution

Session 4 implemented a proper architectural solution via the Runner Gateway:
- Executors only send `executor_session_id` and `project_dir` (data they own)
- Runner Gateway enriches with `hostname` and `executor_profile` (data the runner owns)
- No hardcoded values in executors

See [04-executor-runner-communication-refactor.md](./04-executor-runner-communication-refactor.md) for implementation details.
