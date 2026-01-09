# Test: Parameter Validation - Valid Parameters

Verify that valid parameters are accepted by the coordinator.

## Prerequisites

- Database reset: `./tests/scripts/reset-db`
- Agent Coordinator running
- Agent Runner running with `-x test-executor` profile (optional - only needed if testing execution)

## Test Steps

### Step 1: Create run with valid prompt parameter

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "parameters": {"prompt": "Hello, this is a test message"},
    "project_dir": "."
  }'
```

Expected response (201 Created):
```json
{"run_id":"run_...","session_id":"ses_...","status":"pending"}
```

### Step 2: Verify run was created

```bash
curl http://localhost:8765/runs | jq '.runs[0]'
```

Expected: Run exists with status "pending" and parameters containing the prompt.

## Verification Checklist

- [ ] HTTP 201 response received
- [ ] Response contains run_id (format: `run_...`)
- [ ] Response contains session_id (format: `ses_...`)
- [ ] Response status is "pending"
- [ ] Run appears in GET /runs list

## Cleanup

Run `./tests/scripts/reset-db` before the next test.
