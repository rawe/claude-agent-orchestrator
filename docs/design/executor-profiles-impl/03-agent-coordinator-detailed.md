# Session 3: Agent Coordinator - Detailed Implementation Plan

**Status:** In Progress
**Session Overview:** [`README.md`](./README.md)
**Session Document:** [`03-agent-coordinator.md`](./03-agent-coordinator.md)
**Design Document:** [`../executor-profiles.md`](../executor-profiles.md)

> **Note:** This is a temporary working document. Delete after implementation is complete and update `03-agent-coordinator.md` and `README.md` with final status.

---

## Introduction

The **Executor Profiles** feature introduces named configuration profiles (e.g., `coding`, `research`, `supervised`) that bundle executor settings, permission modes, and behavioral configurations. This replaces the previous approach where `executor_type` directly referenced executor folder names like `claude-code`.

**What changes:**
- `executor_type` (e.g., `"claude-code"`) → `executor_profile` (e.g., `"coding"`)
- New `executor` object stores the actual executor details: `{type, command, config}`
- New `require_matching_tags` flag allows runners to only accept runs with matching tags

**This session** updates the Agent Coordinator to:
1. Accept the renamed and new fields from Agent Runner registration
2. Store and return these fields in API responses
3. Implement `require_matching_tags` filtering in demand matching

Sessions 1 (Executor) and 2 (Agent Runner) are already complete. The runner now sends the new payload format; the coordinator must be updated to handle it.

## Database Strategy

**No migration required.** Drop and recreate the database:

```bash
rm -f .agent-orchestrator/observability.db
# Coordinator will recreate on next startup
```

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Context](#architecture-context)
3. [Implementation Steps](#implementation-steps)
4. [File-by-File Changes](#file-by-file-changes)
5. [Testing Plan](#testing-plan)
6. [Cleanup Checklist](#cleanup-checklist)

---

## Overview

### Objective

Implement Session 3 of the Executor Profiles feature in the Agent Coordinator:

1. **Rename** `executor_type` → `executor_profile` across all coordinator code
2. **Add** new registration fields: `executor` (dict), `require_matching_tags` (bool)
3. **Update** demand matching to support `require_matching_tags` logic
4. **Update** API responses to include new fields

### Prerequisites

- Session 1 (Executor) - **Done**
- Session 2 (Agent Runner) - **Done**: Runner already sends `executor_profile`, `executor`, `require_matching_tags` in registration payload

---

## Architecture Context

### Registration Flow

```
Agent Runner                              Agent Coordinator
     │                                           │
     ├─── POST /runner/register ────────────────►│
     │    {                                      │
     │      hostname,                            │
     │      project_dir,                         │
     │      executor_profile,    ◄── RENAMED     │
     │      executor: {type, command, config},   │  ◄── NEW
     │      tags,                                │
     │      require_matching_tags  ◄── NEW       │
     │    }                                      │
     │                                           │
     │◄── {runner_id, poll_endpoint} ───────────┤
     │                                           │
     ├─── GET /runner/runs?runner_id=... ───────►│  (polling loop)
     │                                           │
```

### Demand Matching Flow

Located in `services/run_queue.py:125-166` (`capabilities_satisfy_demands()`):

```
Runner polls → For each pending run:
     │
     ▼
┌─────────────────────────────────────────────────┐
│  capabilities_satisfy_demands(runner, demands)  │
└─────────────────────────────────────────────────┘
     │
     ├── 1. Property checks (exact match):
     │       - hostname
     │       - project_dir
     │       - executor_profile (renamed from executor_type)
     │
     ├── 2. Tag subset check:
     │       - Runner must have ALL demanded tags
     │
     └── 3. NEW: require_matching_tags check:
             - If runner.require_matching_tags == true:
               - Run MUST have at least one tag
               - At least one run tag must match runner tags
```

### `require_matching_tags` Logic

This is a **runner-centric filter** (stored in runner registration, not in run demands):

| Runner Tags | Run Tags | `require_matching_tags` | Result | Reason |
|-------------|----------|-------------------------|--------|--------|
| `["python", "docker"]` | `["python"]` | `true` | ACCEPT | Intersection exists |
| `["python", "docker"]` | `["nodejs"]` | `true` | REJECT | No intersection |
| `["python", "docker"]` | `[]` | `true` | REJECT | Run has no tags |
| `["python", "docker"]` | `[]` | `false` | ACCEPT | Default behavior |
| `[]` | `["python"]` | `true` | REJECT | No intersection possible |

**Implementation logic:**
```python
if runner.require_matching_tags:
    run_tags = set(demands.get("tags", []))
    runner_tags = set(runner.tags or [])
    if not run_tags or not run_tags.intersection(runner_tags):
        return False
```

---

## Implementation Steps

### Step 1: Update `models.py`

**File:** `servers/agent-coordinator/models.py`

**Changes:**
| Line | Current | New |
|------|---------|-----|
| 212 | `executor_type: Optional[str] = None` | `executor_profile: Optional[str] = None` |
| 293 | `executor_type: str` | `executor_profile: str` |
| 303 | `executor_type: Optional[str] = None` | `executor_profile: Optional[str] = None` |

**Affected Models:**
- `RunnerDemands` (line 212) - Used in agent blueprints
- `SessionBind` (line 293) - Binds executor to session
- `SessionMetadataUpdate` (line 303) - Updates session metadata

---

### Step 2: Update `database.py`

**File:** `servers/agent-coordinator/database.py`

**Schema Change (line 30):**
```sql
-- Current
executor_type TEXT

-- New
executor_profile TEXT
```

**Query Updates:**
| Line | Function | Change |
|------|----------|--------|
| 147 | `update_session_metadata()` | Rename parameter and column reference |
| 172-174 | `update_session_metadata()` | Update SQL SET clause |
| 332 | `bind_session_executor()` | Rename parameter |
| 344 | `bind_session_executor()` | Rename in docstring |
| 365 | `bind_session_executor()` | Update SQL SET clause |
| 368 | `bind_session_executor()` | Update params list |
| 450 | `get_session_affinity()` | Update SELECT column |
| 463 | `get_session_affinity()` | Verify column in result |

---

### Step 3: Update `runner_registry.py`

**File:** `servers/agent-coordinator/services/runner_registry.py`

**3.1 Update `DuplicateRunnerError` (lines 16-27):**
```python
class DuplicateRunnerError(Exception):
    def __init__(self, runner_id: str, hostname: str, project_dir: str, executor_profile: str):
        self.runner_id = runner_id
        self.hostname = hostname
        self.project_dir = project_dir
        self.executor_profile = executor_profile  # RENAMED
        super().__init__(
            f"Runner with identity ({hostname}, {project_dir}, {executor_profile}) "
            f"is already registered and online as {runner_id}"
        )
```

**3.2 Update `derive_runner_id()` (lines 30-52):**
- Rename parameter `executor_type` → `executor_profile`
- Update docstring (line 40)
- Update key generation (line 46): `key = f"{hostname}:{project_dir}:{executor_profile}"`

**3.3 Update `RunnerInfo` model (lines 61-74):**
```python
class RunnerInfo(BaseModel):
    runner_id: str
    registered_at: str
    last_heartbeat: str
    hostname: str
    project_dir: str
    executor_profile: str           # RENAMED from executor_type
    executor: dict = {}             # NEW: {type, command, config}
    tags: list[str] = []
    require_matching_tags: bool = False  # NEW
    status: Literal["online", "stale"] = RunnerStatus.ONLINE
```

**3.4 Update `register_runner()` method (lines 85-150):**
- Rename parameter (line 89): `executor_type` → `executor_profile`
- Add new parameters: `executor: Optional[dict] = None`, `require_matching_tags: bool = False`
- Update docstring (line 103)
- Update `derive_runner_id()` call (line 113)
- Update `DuplicateRunnerError` call (lines 121-126)
- Update `RunnerInfo` construction (lines 139-148)

---

### Step 4: Update `run_queue.py`

**File:** `servers/agent-coordinator/services/run_queue.py`

**4.1 Rename `DemandFields` constant (line 121):**
```python
class DemandFields:
    HOSTNAME = "hostname"
    PROJECT_DIR = "project_dir"
    EXECUTOR_PROFILE = "executor_profile"  # RENAMED from EXECUTOR_TYPE
    TAGS = "tags"
```

**4.2 Update `capabilities_satisfy_demands()` (lines 125-166):**

Rename field access (lines 155-157):
```python
demanded_executor_profile = demands.get(DemandFields.EXECUTOR_PROFILE)
if demanded_executor_profile and runner.executor_profile != demanded_executor_profile:
    return False
```

Add `require_matching_tags` logic after tag subset check (after line 164):
```python
# NEW: require_matching_tags - runner only accepts runs with matching tags
if runner.require_matching_tags:
    run_tags = set(demands.get(DemandFields.TAGS, []))
    runner_tags = set(runner.tags or [])
    # Reject if run has no tags OR no intersection with runner tags
    if not run_tags or not run_tags.intersection(runner_tags):
        return False
```

Update docstring (line 137) to reference `executor_profile`.

---

### Step 5: Update `main.py`

**File:** `servers/agent-coordinator/main.py`

**5.1 Update `RunnerRegisterRequest` model (lines 904-915):**
```python
class RunnerRegisterRequest(BaseModel):
    hostname: str
    project_dir: str
    executor_profile: str                    # RENAMED from executor_type
    executor: Optional[dict] = None          # NEW
    tags: Optional[list[str]] = None
    require_matching_tags: bool = False      # NEW
```

**5.2 Update `/runner/register` endpoint (lines 949-1000):**

Update `register_runner()` call (lines 965-970):
```python
runner = runner_registry.register_runner(
    hostname=request.hostname,
    project_dir=request.project_dir,
    executor_profile=request.executor_profile,  # RENAMED
    executor=request.executor,                   # NEW
    tags=request.tags,
    require_matching_tags=request.require_matching_tags,  # NEW
)
```

Update debug logging (lines 987-993):
```python
if DEBUG:
    print(f"[DEBUG] Registered runner: {runner.runner_id}", flush=True)
    print(f"[DEBUG]   hostname: {request.hostname}", flush=True)
    print(f"[DEBUG]   project_dir: {request.project_dir}", flush=True)
    print(f"[DEBUG]   executor_profile: {request.executor_profile}", flush=True)  # RENAMED
    if request.executor:
        print(f"[DEBUG]   executor: {request.executor}", flush=True)  # NEW
    if request.tags:
        print(f"[DEBUG]   tags: {request.tags}", flush=True)
    if request.require_matching_tags:
        print(f"[DEBUG]   require_matching_tags: {request.require_matching_tags}", flush=True)  # NEW
```

Update error response (lines 971-982):
```python
except DuplicateRunnerError as e:
    raise HTTPException(
        status_code=409,
        detail={
            "error": "duplicate_runner",
            "message": str(e),
            "runner_id": e.runner_id,
            "hostname": e.hostname,
            "project_dir": e.project_dir,
            "executor_profile": e.executor_profile,  # RENAMED
        }
    )
```

**5.3 Update `RunnerWithStatus` model (lines 1232-1242):**
```python
class RunnerWithStatus(BaseModel):
    runner_id: str
    registered_at: str
    last_heartbeat: str
    hostname: str
    project_dir: str
    executor_profile: str                    # RENAMED from executor_type
    executor: dict = {}                      # NEW
    tags: list[str] = []
    require_matching_tags: bool = False      # NEW
    status: str
    seconds_since_heartbeat: float
```

**5.4 Update `/runners` endpoint response (lines 1261-1271):**
```python
result.append(RunnerWithStatus(
    runner_id=runner.runner_id,
    registered_at=runner.registered_at,
    last_heartbeat=runner.last_heartbeat,
    hostname=runner.hostname,
    project_dir=runner.project_dir,
    executor_profile=runner.executor_profile,  # RENAMED
    executor=runner.executor,                   # NEW
    tags=runner.tags,
    require_matching_tags=runner.require_matching_tags,  # NEW
    status=runner.status,
    seconds_since_heartbeat=seconds,
))
```

**5.5 Update `bind_session_endpoint` (lines 286-311):**
```python
result = bind_session_executor(
    session_id=session_id,
    executor_session_id=binding.executor_session_id,
    hostname=binding.hostname,
    executor_profile=binding.executor_profile,  # RENAMED
    project_dir=binding.project_dir,
)
```

**5.6 Update `update_metadata` endpoint (lines 568-594):**
```python
update_session_metadata(
    session_id=session_id,
    project_dir=metadata.project_dir,
    agent_name=metadata.agent_name,
    last_resumed_at=metadata.last_resumed_at,
    executor_session_id=metadata.executor_session_id,
    executor_profile=metadata.executor_profile,  # RENAMED
    hostname=metadata.hostname,
)
```

---

### Step 6: Update Agent Blueprints

**Directory:** `config/agents/*/agent.json`

**Current state:** No agent blueprints currently use `executor_type` in demands (verified via grep). They use `tags` instead.

**Action:** No changes needed for existing blueprints. The `RunnerDemands` model update in Step 1 ensures future blueprints use `executor_profile`.

---

## File-by-File Changes

### Summary Table

| File | Changes | Lines Affected |
|------|---------|----------------|
| `models.py` | Rename field in 3 models | 212, 293, 303 |
| `database.py` | Rename column + query params | 30, 147, 172-174, 332, 344, 365, 368, 450, 463 |
| `runner_registry.py` | Rename + add 2 new fields | 19-27, 30-52, 61-74, 85-150 |
| `run_queue.py` | Rename constant + add matching logic | 121, 137, 155-157, +new after 164 |
| `main.py` | Rename + add fields in models/endpoints | 298-299, 584, 904-1000, 1232-1271 |

---

## Testing Plan

```bash
# 1. Start coordinator (no auth)
cd servers/agent-coordinator && AUTH_ENABLED=false uv run python -m main

# 2. Register runner with new fields
curl -X POST http://localhost:8765/runner/register \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "test-machine",
    "project_dir": "/tmp/test",
    "executor_profile": "coding",
    "executor": {
      "type": "claude-code",
      "command": "executors/claude-code/ao-claude-code-exec",
      "config": {"permission_mode": "bypassPermissions"}
    },
    "tags": ["python", "docker"],
    "require_matching_tags": true
  }'

# 3. Verify runner list shows new fields
curl http://localhost:8765/runners | python -m json.tool

# 4. Test demand matching with require_matching_tags
# Create a run without tags (should NOT match runner with require_matching_tags=true)
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "prompt": "test",
    "agent_name": "simple-agent"
  }'
# Run should stay pending (no matching runner)

# 5. Create a run with matching tag
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "prompt": "test",
    "additional_demands": {"tags": ["python"]}
  }'
# Runner should claim this run
```

---

## Cleanup Checklist

After implementation is complete:

- [ ] All `executor_type` renamed to `executor_profile` in coordinator
- [ ] New `executor` field stored and returned in API
- [ ] New `require_matching_tags` field with filtering logic
- [ ] Database schema updated
- [ ] All SQL queries updated
- [ ] Demand matching uses `executor_profile`
- [ ] API responses include new fields
- [ ] Manual testing passed
- [ ] Update [`./03-agent-coordinator.md`](./03-agent-coordinator.md) - mark as Done
- [ ] Update [`./README.md`](./README.md) - mark Session 3 as Done
- [ ] **Delete this file** (`03-agent-coordinator-detailed.md`)
