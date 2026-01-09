# Test: Structured Result API

Verify that the `GET /sessions/{id}/result` endpoint returns structured result format with `result_text` and `result_data`.

## Prerequisites

- Database reset: `./tests/scripts/reset-db`
- Agent Coordinator running
- Agent Runner running with `-x test-executor` profile

## Test Steps

### Step 1: Create and complete a session

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "parameters": {"prompt": "Hello, testing structured result"},
    "project_dir": "."
  }'
```

Note the `session_id` from response.

### Step 2: Wait for completion

Wait for the session to complete (status: finished). Check via:

```bash
curl -s http://localhost:8765/sessions/ses_... | python -m json.tool
```

Expected: `"status": "finished"`

### Step 3: Get structured result

```bash
curl -s http://localhost:8765/sessions/ses_.../result | python -m json.tool
```

Expected response:
```json
{
  "result_text": "[TEST-EXECUTOR] Received: Hello, testing structured result",
  "result_data": null
}
```

## API Contract

### Endpoint: `GET /sessions/{session_id}/result`

**Response Schema:**
```json
{
  "result_text": "string | null",
  "result_data": "object | null"
}
```

**Field Definitions:**
- `result_text`: Human-readable text output (always present for completed sessions)
- `result_data`: Structured JSON output (null for AI agents, object for deterministic agents)

**Error Cases:**
- 404: Session not found
- 400: Session not finished

### Step 4: Test error cases

**Session not found:**
```bash
curl -s http://localhost:8765/sessions/ses_nonexistent/result
```
Expected: `{"detail": "Session not found"}`

**Session not finished (create but don't wait):**
```bash
# Start a session
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "parameters": {"prompt": "Quick test"},
    "project_dir": "."
  }'

# Immediately try to get result (while still running)
curl -s http://localhost:8765/sessions/ses_.../result
```
Expected: `{"detail": "Session not finished"}` (if caught while running)

## Verification Checklist

- [ ] Response contains `result_text` field
- [ ] Response contains `result_data` field
- [ ] `result_text` contains the assistant's output
- [ ] `result_data` is `null` for test-executor (AI agent pattern)
- [ ] 404 returned for non-existent session
- [ ] 400 returned for non-finished session (if testable)

## Cleanup

Run `./tests/scripts/reset-db` before the next test.
