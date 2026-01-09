# Test: Parameter Validation - Invalid Parameters

Verify that invalid parameters are rejected with a structured validation error.

## Prerequisites

- Database reset: `./tests/scripts/reset-db`
- Agent Coordinator running

## Test Steps

### Step 1: Create run with missing prompt

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "parameters": {},
    "project_dir": "."
  }'
```

Expected response (400 Bad Request):
```json
{
  "detail": {
    "error": "parameter_validation_failed",
    "message": "Parameters do not match agent's parameters_schema",
    "agent_name": "(no agent)",
    "validation_errors": [
      {
        "path": "$",
        "message": "'prompt' is a required property",
        "schema_path": "required"
      }
    ],
    "parameters_schema": {
      "type": "object",
      "required": ["prompt"],
      "properties": {
        "prompt": {"type": "string", "minLength": 1}
      },
      "additionalProperties": false
    }
  }
}
```

### Step 2: Create run with wrong prompt type

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "parameters": {"prompt": 123},
    "project_dir": "."
  }'
```

Expected response (400 Bad Request):
```json
{
  "detail": {
    "error": "parameter_validation_failed",
    "message": "Parameters do not match agent's parameters_schema",
    "agent_name": "(no agent)",
    "validation_errors": [
      {
        "path": "$.prompt",
        "message": "123 is not of type 'string'",
        "schema_path": "properties/prompt/type"
      }
    ],
    "parameters_schema": {...}
  }
}
```

### Step 3: Create run with empty prompt

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "parameters": {"prompt": ""},
    "project_dir": "."
  }'
```

Expected response (400 Bad Request):
```json
{
  "detail": {
    "error": "parameter_validation_failed",
    "message": "Parameters do not match agent's parameters_schema",
    "agent_name": "(no agent)",
    "validation_errors": [
      {
        "path": "$.prompt",
        "message": "'' is too short",
        "schema_path": "properties/prompt/minLength"
      }
    ],
    "parameters_schema": {...}
  }
}
```

### Step 4: Create run with additional properties

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "parameters": {"prompt": "Hello", "extra_field": "should fail"},
    "project_dir": "."
  }'
```

Expected response (400 Bad Request):
```json
{
  "detail": {
    "error": "parameter_validation_failed",
    "message": "Parameters do not match agent's parameters_schema",
    "agent_name": "(no agent)",
    "validation_errors": [
      {
        "path": "$",
        "message": "Additional properties are not allowed ('extra_field' was unexpected)",
        "schema_path": "additionalProperties"
      }
    ],
    "parameters_schema": {...}
  }
}
```

## Verification Checklist

- [ ] Missing prompt returns 400 with validation error
- [ ] Wrong type (number instead of string) returns 400 with type error
- [ ] Empty prompt returns 400 with minLength error
- [ ] Additional properties return 400 with additionalProperties error
- [ ] All error responses include:
  - [ ] `error: "parameter_validation_failed"`
  - [ ] `validation_errors` array with path and message
  - [ ] `parameters_schema` for AI self-correction
- [ ] No runs are created in the database for invalid requests

## Cleanup

No cleanup needed - no runs were created.
