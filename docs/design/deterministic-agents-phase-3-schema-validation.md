# Phase 3: Schema Discovery & Validation

**Status:** Implementation Ready
**Depends on:** Phase 1 (Unified Input Model)
**Design Reference:** [deterministic-agents-implementation.md](./deterministic-agents-implementation.md) - Sections 5, 6, 7

---

## Objective

Enable AI orchestrators to discover agent schemas and validate parameters before execution. The coordinator validates `parameters` against `parameters_schema` on run creation, returning structured errors that enable AI self-correction.

**End state:** Agent listings include `type` and `parameters_schema`. Invalid parameters are rejected with actionable error details.

---

## Key Changes

### 1. Agent Listing Response

**File:** `servers/agent-coordinator/main.py`
- Agent list endpoint: Include `type` and `parameters_schema` in response
- AI agents: `type: "agent"`, no `parameters_schema` (implicit schema applies)
- Deterministic agents (Phase 4): `type: "deterministic"`, full `parameters_schema`

**Response format:**
```json
{
  "agents": [
    {
      "name": "researcher",
      "type": "agent",
      "description": "Research assistant"
    },
    {
      "name": "web-crawler",
      "type": "deterministic",
      "description": "Crawls websites",
      "parameters_schema": { ... }
    }
  ]
}
```

### 2. MCP Tool: list_agent_blueprints

**File:** `servers/agent-runner/lib/agent_orchestrator_mcp/tools.py`
- `list_agent_blueprints()` (lines 53-81): Return `type` and `parameters_schema` inline
- Update tool description to explain schema usage

### 3. Parameter Validation

**File:** `servers/agent-coordinator/services/run_queue.py`
- Add `jsonschema` dependency for validation
- Before creating run: Validate `parameters` against agent's `parameters_schema`
- For AI agents without schema: Use implicit schema `{prompt: string, required: ["prompt"]}`
- On validation failure: Raise structured error

**Validation logic:**
```python
from jsonschema import Draft7Validator, ValidationError

def validate_parameters(parameters: dict, schema: dict, agent_name: str):
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(parameters))
    if errors:
        raise ParameterValidationError(agent_name, errors, schema)
```

### 4. Validation Error Response

**File:** `servers/agent-coordinator/main.py`
- `create_run()` endpoint: Catch `ParameterValidationError`, return 400 with structured error

**Error response format:**
```json
{
  "error": "parameter_validation_failed",
  "message": "Parameters do not match agent's parameters_schema",
  "agent_name": "web-crawler",
  "validation_errors": [
    {
      "path": "$.url",
      "message": "'not-a-url' is not a valid URI",
      "schema_path": "properties.url.format"
    }
  ],
  "parameters_schema": { ... }
}
```

Including `parameters_schema` in the error enables AI self-correction.

### 5. Agent Blueprint Storage

**File:** `servers/agent-coordinator/database.py`
- Agents/blueprints table: Add `type` column (`"agent"` or `"deterministic"`)
- Add `parameters_schema` column (JSON, nullable for AI agents)

---

## Implicit Schema for AI Agents

AI agents without explicit `parameters_schema` are validated against:

```json
{
  "type": "object",
  "required": ["prompt"],
  "properties": {
    "prompt": { "type": "string", "minLength": 1 }
  },
  "additionalProperties": false
}
```

This ensures AI agents are invoked with `parameters={"prompt": "..."}`.

---

## Dependency Addition

Add `jsonschema` to coordinator dependencies:

```bash
cd servers/agent-coordinator && uv add jsonschema
```

Use JSON Schema Draft 7 for validation (widely supported, stable).

---

## Files to Modify

| File | Change |
|------|--------|
| `servers/agent-coordinator/pyproject.toml` | Add `jsonschema` dependency |
| `servers/agent-coordinator/database.py` | Add `type`, `parameters_schema` columns |
| `servers/agent-coordinator/main.py` | Agent list includes schema; create_run validates |
| `servers/agent-coordinator/services/run_queue.py` | Parameter validation logic |
| `servers/agent-runner/lib/agent_orchestrator_mcp/tools.py` | list_agent_blueprints returns schema |

---

## Acceptance Criteria

1. **Agent listing includes type:**
   ```bash
   curl /agents
   # Returns: [{"name": "researcher", "type": "agent", ...}]
   ```

2. **Valid parameters accepted:**
   ```bash
   curl -X POST /runs -d '{"agent_name": "researcher", "parameters": {"prompt": "Test"}}'
   # Returns: 201 Created
   ```

3. **Invalid parameters rejected:**
   ```bash
   curl -X POST /runs -d '{"agent_name": "researcher", "parameters": {}}'
   # Returns: 400 Bad Request
   # Body: {"error": "parameter_validation_failed", "validation_errors": [...]}
   ```

4. **Missing prompt rejected:**
   ```bash
   curl -X POST /runs -d '{"agent_name": "researcher", "parameters": {"wrong": "field"}}'
   # Returns: 400 with error about missing "prompt"
   ```

5. **Error includes schema:** Validation error response contains `parameters_schema` for self-correction

6. **MCP tool returns schema:**
   ```python
   agents = list_agent_blueprints()
   # Each agent has "type" field
   ```

---

## AI Self-Correction Flow

When an AI orchestrator sends invalid parameters:

1. Coordinator validates against schema
2. Returns 400 with `validation_errors` and `parameters_schema`
3. AI reads error, understands what's wrong
4. AI constructs corrected parameters
5. AI retries with valid parameters

This loop happens at the API level - no framework magic required.

---

## Testing Strategy

1. Unit test parameter validation:
   - Valid parameters → passes
   - Missing required field → error with path
   - Wrong type → error with type info
   - Invalid format (URI, email) → error with format info

2. Unit test implicit schema application for AI agents

3. Integration test validation error response format

4. Integration test MCP list_agent_blueprints returns type

5. End-to-end test: AI receives error, self-corrects, retries successfully

---

## References

- [JSON Schema Draft 7](https://json-schema.org/draft-07/json-schema-release-notes.html)
- [deterministic-agents-implementation.md](./deterministic-agents-implementation.md) - Sections 5, 6, 7
- [ADR-011](../adr/ADR-011-runner-capabilities-and-run-demands.md) - Run demands (related validation patterns)
