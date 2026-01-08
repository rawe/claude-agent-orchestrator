# Phase 1: Unified Input Model Implementation Plan

**Objective:** Migrate from `prompt: str` to `parameters: dict` across the API, MCP tools, and executor invocation.

**Approach:** Clean break - no backward compatibility. All clients are in monorepo, database gets dropped.

---

## Implementation Order

```
1. Coordinator (Models + Database + API)
        |
        v
2. Agent Runner (Invocation Schema + Executor)
        |
        v
3. MCP Tools
        |
        v
4. Frontend (Dashboard + Chat-UI)
        |
        v
5. Testing & Verification
```

---

## 1. Coordinator

### 1.1 run_queue.py - Core Models

**File:** `servers/agent-coordinator/services/run_queue.py`

**RunCreate model (lines 63-78):**
```python
# BEFORE
prompt: str

# AFTER
parameters: dict  # Required, no Optional
```

**Run model (lines 80-101):**
```python
# BEFORE
prompt: str

# AFTER
parameters: dict

@property
def prompt(self) -> Optional[str]:
    """Helper for AI agents."""
    return self.parameters.get("prompt")
```

**_dict_to_run() (line 239):**
- Parse `parameters` from JSON string

**add_run() (line 261):**
- Serialize `parameters` dict to JSON

### 1.2 database.py - Fresh Schema

**File:** `servers/agent-coordinator/database.py`

**Schema change (line 57):**
```sql
-- BEFORE
prompt TEXT NOT NULL,

-- AFTER
parameters TEXT NOT NULL,  -- JSON string
```

**Database will be dropped - no migration needed.**

**create_run() function (lines 487-520):**
- Change `prompt: str` parameter to `parameters: str` (JSON string)

### 1.3 openapi_config.py

**File:** `servers/agent-coordinator/openapi_config.py`

**RunResponse (line 225):**
```python
# BEFORE
prompt: str = Field(..., description="Work to execute")

# AFTER
parameters: dict = Field(..., description="Input parameters")
```

### 1.4 main.py - create_run Endpoint

**File:** `servers/agent-coordinator/main.py` (lines 1334-1435)

- No special handling needed - RunCreate now requires `parameters`
- Update any debug logs from `prompt` to `parameters`

### 1.5 callback_processor.py

**File:** `servers/agent-coordinator/services/callback_processor.py`

**_create_resume_run() (line 249):**
```python
# BEFORE
run = run_queue.add_run(RunCreate(
    type=RunType.RESUME_SESSION,
    session_id=parent_session_id,
    prompt=prompt,
))

# AFTER
run = run_queue.add_run(RunCreate(
    type=RunType.RESUME_SESSION,
    session_id=parent_session_id,
    parameters={"prompt": prompt},
))
```

---

## 2. Agent Runner

### 2.1 invocation.py - Schema 2.2

**File:** `servers/agent-runner/lib/invocation.py`

**Changes:**
- Bump `SCHEMA_VERSION` from "2.1" to "2.2"
- Set `SUPPORTED_VERSIONS = {"2.2"}` (no backward compat)
- Update `INVOCATION_SCHEMA`:
  - Required: `["schema_version", "mode", "session_id", "parameters"]`
  - Remove `prompt` property, add `parameters: {type: "object"}`

**ExecutorInvocation dataclass (lines 93-119):**
```python
# BEFORE
prompt: str

# AFTER
parameters: dict

@property
def prompt(self) -> Optional[str]:
    """Helper for AI agents."""
    return self.parameters.get("prompt")
```

**from_json() validation:**
- Change required field from `prompt` to `parameters`
- Remove `prompt` from known_fields, add `parameters`

### 2.2 executor.py

**File:** `servers/agent-runner/lib/executor.py`

**_build_payload() (line 217):**
```python
# BEFORE
"prompt": run.prompt,

# AFTER
"parameters": run.parameters,
```

### 2.3 api_client.py

**File:** `servers/agent-runner/lib/api_client.py`

**Run dataclass (lines 50-61):**
```python
# BEFORE
prompt: str

# AFTER
parameters: dict

@property
def prompt(self) -> Optional[str]:
    return self.parameters.get("prompt")
```

**poll_run() (line 226):**
```python
# BEFORE
prompt=run_data["prompt"],

# AFTER
parameters=run_data["parameters"],
```

### 2.4 Claude-Code Executor

**File:** `servers/agent-runner/executors/claude-code/ao-claude-code-exec`

No changes needed - uses `inv.prompt` which now works via `@property`.

---

## 3. MCP Tools

### 3.1 tools.py

**File:** `servers/agent-runner/lib/agent_orchestrator_mcp/tools.py`

**start_agent_session() (lines 112-211):**
```python
# BEFORE
async def start_agent_session(
    self,
    ctx: RequestContext,
    prompt: str,
    ...
) -> dict:

# AFTER
async def start_agent_session(
    self,
    ctx: RequestContext,
    parameters: dict,  # Required
    ...
) -> dict:
```

Update validation: check `parameters` has content, validate `len(json.dumps(parameters))` for size limit.

**resume_agent_session() (lines 213-309):**
- Same change: `prompt: str` -> `parameters: dict`

### 3.2 coordinator_client.py

**File:** `servers/agent-runner/lib/agent_orchestrator_mcp/coordinator_client.py`

**create_run() (lines 93-149):**
```python
# BEFORE
async def create_run(
    self,
    run_type: str,
    prompt: str,
    ...
) -> dict:
    data = {
        "type": run_type,
        "prompt": prompt,
    }

# AFTER
async def create_run(
    self,
    run_type: str,
    parameters: dict,
    ...
) -> dict:
    data = {
        "type": run_type,
        "parameters": parameters,
    }
```

### 3.3 server.py

**File:** `servers/agent-runner/lib/agent_orchestrator_mcp/server.py`

**Tool registrations (lines 133-182):**
- Update parameter definitions: `prompt: str` -> `parameters: dict`
- Update tool descriptions

---

## 4. Frontend

### 4.1 Dashboard - Types

**File:** `dashboard/src/types/run.ts`
```typescript
// BEFORE
prompt: string;

// AFTER
parameters: Record<string, unknown>;
```

**File:** `dashboard/src/services/unifiedViewTypes.ts` (line 180)
```typescript
// BEFORE
prompt: string;

// AFTER
parameters: Record<string, unknown>;
```

### 4.2 Dashboard - Services

**File:** `dashboard/src/services/chatService.ts`

```typescript
// BEFORE
export interface SessionStartRequest {
  prompt: string;
  ...
}

// AFTER
export interface SessionStartRequest {
  parameters: Record<string, unknown>;
  ...
}
```

Update `startSession()` and `resumeSession()` to pass `parameters`.

**File:** `dashboard/src/services/unifiedViewService.ts` (line 82)
```typescript
// BEFORE
prompt: run.prompt,

// AFTER
parameters: run.parameters,
```

### 4.3 Dashboard - Components

Update all components displaying `run.prompt`:

**File:** `dashboard/src/components/features/runs/RunDetailPanel.tsx` (lines 263-269)
```tsx
// Show parameters.prompt for AI agents, JSON for others
{run.parameters.prompt ? (
  <pre>{run.parameters.prompt}</pre>
) : (
  <pre>{JSON.stringify(run.parameters, null, 2)}</pre>
)}
```

Same pattern for:
- `dashboard/src/pages/unified-view/SwimlaneTab.tsx`
- `dashboard/src/pages/unified-view/TreeViewTab.tsx`
- `dashboard/src/pages/unified-view/ActivityFeedTab.tsx`
- `dashboard/src/pages/unified-view/DashboardCardsTab.tsx`

**File:** `dashboard/src/pages/Chat.tsx`
Update `handleSendMessage()` to create `parameters: {prompt: inputValue}`.

### 4.4 Chat-UI Interface

**File:** `interfaces/chat-ui/src/types/index.ts`
```typescript
// BEFORE
export interface RunRequest {
  ...
  prompt: string;
  ...
}

// AFTER
export interface RunRequest {
  ...
  parameters: Record<string, unknown>;
  ...
}
```

**File:** `interfaces/chat-ui/src/services/api.ts`
```typescript
// BEFORE
async startSession(prompt: string) {
  const request: RunRequest = {
    type: 'start_session',
    prompt,
    ...
  };
}

// AFTER
async startSession(prompt: string) {
  const request: RunRequest = {
    type: 'start_session',
    parameters: { prompt },
    ...
  };
}
```

---

## 5. Testing & Verification

### Update Tests

**File:** `servers/agent-runner/tests/test_invocation.py`
- Update all tests from `prompt` to `parameters`
- Update expected schema version to "2.2"

### Integration Tests

Update test cases in `tests/integration/`:
- Change all curl commands from `"prompt": "..."` to `"parameters": {"prompt": "..."}`

### Verification Steps

1. **Drop database:**
   ```bash
   rm servers/agent-coordinator/agent_coordinator.db
   ```

2. **Start coordinator:**
   ```bash
   cd servers/agent-coordinator && AUTH_ENABLED=false uv run python -m main
   ```

3. **Start agent runner:**
   ```bash
   mkdir -p .agent-orchestrator/runner-project
   PROJECT_DIR=.agent-orchestrator/runner-project ./servers/agent-runner/agent-runner
   ```

4. **Test API:**
   ```bash
   curl -X POST http://localhost:8765/runs \
     -H "Content-Type: application/json" \
     -d '{"type": "start_session", "parameters": {"prompt": "Hello"}, "agent_name": "test-agent"}'
   ```

5. **Verify executor receives parameters:**
   Check agent runner logs show `parameters` in invocation payload.

6. **Run integration tests:**
   ```bash
   /tests:run
   ```

7. **Test Dashboard:**
   ```bash
   cd dashboard && npm run dev
   ```
   Verify runs display parameters correctly.

8. **Test Chat-UI:**
   ```bash
   cd interfaces/chat-ui && npm run dev
   ```
   Verify chat sessions work.

---

## Critical Files Summary

| Component | File | Change |
|-----------|------|--------|
| Coordinator | `services/run_queue.py` | `prompt` -> `parameters` in models |
| Coordinator | `database.py` | Schema: `prompt` -> `parameters` column |
| Coordinator | `services/callback_processor.py` | Generate `parameters` dict |
| Coordinator | `openapi_config.py` | Response model |
| Agent Runner | `lib/invocation.py` | Schema 2.2, `parameters` field |
| Agent Runner | `lib/executor.py` | _build_payload() |
| Agent Runner | `lib/api_client.py` | Run dataclass |
| MCP | `lib/agent_orchestrator_mcp/tools.py` | Tool signatures |
| MCP | `lib/agent_orchestrator_mcp/coordinator_client.py` | API calls |
| Dashboard | `src/types/run.ts` | TypeScript type |
| Dashboard | `src/services/chatService.ts` | Request interface |
| Dashboard | `src/pages/Chat.tsx` | Input handling |
| Chat-UI | `src/types/index.ts` | RunRequest type |
| Chat-UI | `src/services/api.ts` | API calls |

---

## Acceptance Criteria

1. API accepts `parameters: {"prompt": "..."}` and creates run
2. API rejects requests without `parameters` field
3. Executor receives invocation with `parameters` field (schema 2.2)
4. Claude-code executor extracts prompt via `inv.prompt` property
5. Dashboard displays parameters correctly
6. Chat-UI works with new API
7. Integration tests pass
8. Callback-triggered resume runs work correctly
