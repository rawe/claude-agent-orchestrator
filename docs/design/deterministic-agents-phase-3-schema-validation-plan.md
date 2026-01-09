# Phase 3: Schema Discovery & Validation - Implementation Plan

**Design Reference:** `docs/design/deterministic-agents-phase-3-schema-validation.md`
**Breaking Changes:** Yes (DB drop, no backwards compatibility needed)

---

## Overview

Enable AI orchestrators to discover agent schemas and validate parameters before execution. The coordinator validates `parameters` against `parameters_schema` on run creation, returning structured errors for AI self-correction.

---

## Component Changes

### 1. Agent Coordinator - Models & Storage

**Files:**
- `servers/agent-coordinator/models.py`
- `servers/agent-coordinator/agent_storage.py`

**Changes:**
1. Add `type` field to Agent model: `Literal["autonomous", "procedural"]` (default: `"autonomous"`)
2. Add `parameters_schema` field to Agent model: `Optional[dict]` (JSON Schema)
3. Update `AgentCreate` and `AgentUpdate` models with these fields
4. Update `_read_agent_from_dir()` to read `type` and `parameters_schema` from `agent.json`
5. Update `create_agent()` and `update_agent()` to write these fields

**Type naming rationale:**
- `autonomous` - Self-directed agents that interpret intent (replaces "agent")
- `procedural` - Follow defined procedures with parameters (replaces "deterministic")

**agent.json format update:**
```json
{
  "name": "my-agent",
  "type": "autonomous",
  "description": "...",
  "parameters_schema": null
}
```

---

### 2. Agent Coordinator - Parameter Validation

**Files:**
- `servers/agent-coordinator/pyproject.toml` - Add `jsonschema` dependency
- `servers/agent-coordinator/services/run_queue.py` - Add validation logic
- `servers/agent-coordinator/main.py` - Handle validation errors

**New Exception:**
```python
class ParameterValidationError(Exception):
    def __init__(self, agent_name: str, errors: list, schema: dict):
        self.agent_name = agent_name
        self.errors = errors  # jsonschema validation errors
        self.schema = schema
```

**Validation Logic in run_queue.py:**
```python
from jsonschema import Draft7Validator

# Implicit schema for autonomous agents (no explicit parameters_schema)
IMPLICIT_AUTONOMOUS_SCHEMA = {
    "type": "object",
    "required": ["prompt"],
    "properties": {"prompt": {"type": "string", "minLength": 1}},
    "additionalProperties": False
}

def validate_parameters(parameters: dict, agent: Agent) -> None:
    schema = agent.parameters_schema or IMPLICIT_AUTONOMOUS_SCHEMA
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(parameters))
    if errors:
        raise ParameterValidationError(agent.name, errors, schema)
```

**Error Response (400) in main.py:**
```json
{
  "error": "parameter_validation_failed",
  "message": "Parameters do not match agent's parameters_schema",
  "agent_name": "researcher",
  "validation_errors": [
    {"path": "$.prompt", "message": "'prompt' is a required property", "schema_path": "required"}
  ],
  "parameters_schema": {...}
}
```

---

### 3. Agent Coordinator - API Endpoints

**File:** `servers/agent-coordinator/main.py`

**GET /agents response update:**
- Include `type` and `parameters_schema` in each agent object
- Already returns full Agent model, just needs model update

**POST /runs endpoint update:**
1. Load agent blueprint if `agent_name` provided
2. Call `validate_parameters(run_create.parameters, agent)`
3. Catch `ParameterValidationError` → return 400 with structured error
4. For runs without agent_name, use implicit autonomous schema

---

### 4. MCP Tools - Agent Runner

**File:** `servers/agent-runner/lib/agent_orchestrator_mcp/tools.py`

**list_agent_blueprints() changes (lines 53-81):**
- Return `type` and `parameters_schema` inline with each agent
- Update tool description to explain schema usage

**Remove temporary validation (lines 148-150, 258-262):**
```python
# DELETE these lines in start_agent_session:
prompt = parameters.get("prompt")
if not prompt or not isinstance(prompt, str):
    raise ToolError("Missing required parameter: 'prompt'")

# DELETE these lines in resume_agent_session:
prompt = parameters.get("prompt")
if not prompt or not isinstance(prompt, str):
    raise ToolError("Missing required parameter: 'prompt'")
```

**File:** `servers/agent-runner/lib/agent_orchestrator_mcp/coordinator_client.py`
- Update `list_agents()` response parsing to include `type` and `parameters_schema`

---

### 5. Dashboard Frontend

**Files:**
- `dashboard/src/types/agent.ts` - Add type and parameters_schema fields
- `dashboard/src/types/run.ts` - Add validation error types
- `dashboard/src/services/api.ts` - Enhanced error handling
- `dashboard/src/components/features/agents/AgentEditor.tsx` - Add type selector
- `dashboard/src/components/features/agents/AgentTable.tsx` - Display type column
- `dashboard/src/pages/Chat.tsx` - Handle validation errors

**Type updates:**
```typescript
// agent.ts
interface Agent {
  // ...existing fields
  type: 'autonomous' | 'procedural';
  parameters_schema?: Record<string, unknown>;
}

// run.ts
interface ValidationError {
  path: string;
  message: string;
  schema_path: string;
}

interface ParameterValidationErrorResponse {
  error: 'parameter_validation_failed';
  message: string;
  agent_name: string;
  validation_errors: ValidationError[];
  parameters_schema: Record<string, unknown>;
}
```

**Error handling update (api.ts):**
```typescript
function handleError(error: unknown): never {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data;
    if (data?.error === 'parameter_validation_failed') {
      // Preserve structured error
      throw data;
    }
    // ...existing handling
  }
}
```

---

### 6. Chat-UI Frontend

**Files:**
- `interfaces/chat-ui/src/types/index.ts` - Add validation error types
- `interfaces/chat-ui/src/services/api.ts` - Enhanced error handling

**Same pattern as dashboard** - detect `parameter_validation_failed` errors and preserve structured details for display.

---

### 7. Integration Tests

**New test files:**
- `tests/integration/14-parameter-validation-valid.md`
- `tests/integration/15-parameter-validation-invalid.md`
- `tests/integration/16-agent-type-listing.md`

**Test 14: Valid Parameters Accepted**
```bash
# Create run with valid prompt
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{"type":"start_session","agent_name":"researcher","parameters":{"prompt":"Test"}}'
# Expect: 201 Created
```

**Test 15: Invalid Parameters Rejected**
```bash
# Create run with missing prompt
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{"type":"start_session","agent_name":"researcher","parameters":{}}'
# Expect: 400 with error="parameter_validation_failed"
```

**Test 16: Agent Listing Includes Type**
```bash
curl http://localhost:8765/agents
# Expect: Each agent has "type" field
```

---

## Implementation Order

1. **Coordinator Models** - Add type/schema to Agent model
2. **Agent Storage** - Update file I/O for new fields
3. **Dependency** - Add jsonschema to coordinator
4. **Validation Logic** - Implement in run_queue.py
5. **API Error Handling** - Catch and format validation errors
6. **MCP Tools** - Update list_agent_blueprints, remove temp validation
7. **Dashboard Types** - Update TypeScript types
8. **Dashboard UI** - Add type display, error handling
9. **Chat-UI** - Error handling updates
10. **Integration Tests** - Add validation test cases
11. **Update Test Blueprints** - Add type field to existing agent.json files

---

## Files to Modify

| Component | File | Change |
|-----------|------|--------|
| Coordinator | `pyproject.toml` | Add jsonschema dependency |
| Coordinator | `models.py` | Add type, parameters_schema fields |
| Coordinator | `agent_storage.py` | Read/write new fields |
| Coordinator | `services/run_queue.py` | Parameter validation logic |
| Coordinator | `main.py` | Validation error handling |
| Agent Runner | `lib/agent_orchestrator_mcp/tools.py` | Return schema, remove temp validation |
| Agent Runner | `lib/agent_orchestrator_mcp/coordinator_client.py` | Parse new fields |
| Dashboard | `src/types/agent.ts` | Add type, parameters_schema |
| Dashboard | `src/types/run.ts` | Add validation error types |
| Dashboard | `src/services/api.ts` | Enhanced error handling |
| Dashboard | `src/components/features/agents/AgentEditor.tsx` | Type selector |
| Dashboard | `src/components/features/agents/AgentTable.tsx` | Type column |
| Chat-UI | `src/types/index.ts` | Validation error types |
| Chat-UI | `src/services/api.ts` | Error handling |
| Tests | `integration/14-*.md` | Valid params test |
| Tests | `integration/15-*.md` | Invalid params test |
| Tests | `integration/16-*.md` | Agent type listing test |
| Config | `config/agents/*/agent.json` | Add type field |

---

## Verification

### Unit Testing
```bash
cd servers/agent-coordinator
uv run python -m pytest tests/ -v  # If tests exist
```

### Manual API Testing
```bash
# Start coordinator
cd servers/agent-coordinator && AUTH_ENABLED=false uv run python -m main

# Test 1: Agent listing includes type
curl -s http://localhost:8765/agents | jq '.[0] | {name, type}'
# Expect: {"name": "...", "type": "autonomous"}

# Test 2: Valid parameters accepted
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{"type":"start_session","agent_name":"researcher","parameters":{"prompt":"Hello"}}'
# Expect: 201 with run_id

# Test 3: Invalid parameters rejected
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{"type":"start_session","agent_name":"researcher","parameters":{}}'
# Expect: 400 with error="parameter_validation_failed"

# Test 4: Wrong type rejected
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{"type":"start_session","agent_name":"researcher","parameters":{"prompt":123}}'
# Expect: 400 with validation error about type
```

### Integration Tests
```bash
/tests:setup
/tests:case 14-parameter-validation-valid
/tests:case 15-parameter-validation-invalid
/tests:case 16-agent-type-listing
/tests:teardown
```

### Dashboard Testing
1. Start dashboard: `cd dashboard && npm run dev`
2. Navigate to Agent Manager
3. Verify agents show type column
4. Try creating a run with empty parameters - verify error displays

---

## Notes

- **No backwards compatibility** - Database will be dropped, all clients in monorepo
- **Implicit schema** for autonomous agents ensures `{"prompt": string}` requirement
- **Error includes schema** to enable AI self-correction
- **Phase 4** will add procedural agent definitions with full schemas
