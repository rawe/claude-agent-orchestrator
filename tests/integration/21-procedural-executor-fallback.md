# Test: Procedural Executor Fallback Handling

Verify that the procedural executor correctly handles non-JSON output using the fallback structure.

## Prerequisites

- Database reset: `./tests/scripts/reset-db`
- Agent Coordinator running
- Agent Runner running with `-x test-procedural` profile
- sse-monitor running

## Test Steps

### Step 1: Verify runner registration with test agent

```bash
curl http://localhost:8765/agents
```

Expected: Should include the test agent:
```json
{
  "name": "test",
  "description": "Test agent for procedural executor...",
  "type": "procedural",
  "command": "scripts/test/test",
  "runner_id": "..."
}
```

---

### Step 2: Test plain text output (fallback case)

When the script outputs plain text (not JSON), the executor should return the fallback structure.

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "agent_name": "test",
    "parameters": {"stdout": "Hello World"},
    "project_dir": "."
  }'
```

**Expected result event:**
```json
{
  "event_type": "result",
  "result_text": null,
  "result_data": {
    "return_code": 0,
    "stdout": "Hello World",
    "stderr": ""
  }
}
```

---

### Step 3: Test JSON output (pass-through case)

When the script outputs valid JSON, it should be passed through as-is.

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "agent_name": "test",
    "parameters": {"stdout": "Success", "json": true},
    "project_dir": "."
  }'
```

**Expected result event:**
```json
{
  "event_type": "result",
  "result_text": null,
  "result_data": {
    "output": "Success"
  }
}
```

---

### Step 4: Test error with stderr (fallback case)

When the script fails and writes to stderr, the fallback should capture everything.

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "agent_name": "test",
    "parameters": {"stdout": "partial output", "stderr": "Error: something failed", "exit-code": 1},
    "project_dir": "."
  }'
```

**Expected result event:**
```json
{
  "event_type": "result",
  "result_text": null,
  "result_data": {
    "return_code": 1,
    "stdout": "partial output",
    "stderr": "Error: something failed"
  }
}
```

---

### Step 5: Test empty output with error

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "agent_name": "test",
    "parameters": {"stderr": "Fatal error", "exit-code": 2},
    "project_dir": "."
  }'
```

**Expected result event:**
```json
{
  "event_type": "result",
  "result_text": null,
  "result_data": {
    "return_code": 2,
    "stdout": "",
    "stderr": "Fatal error"
  }
}
```

---

### Step 6: Test stdout and stderr together (success)

Scripts can write to stderr for logging/debug even on success.

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "agent_name": "test",
    "parameters": {"stdout": "Result data", "stderr": "Debug: processing complete"},
    "project_dir": "."
  }'
```

**Expected result event:**
```json
{
  "event_type": "result",
  "result_text": null,
  "result_data": {
    "return_code": 0,
    "stdout": "Result data",
    "stderr": "Debug: processing complete"
  }
}
```

---

## Verification Checklist

- [ ] Plain text stdout → fallback structure with `return_code`, `stdout`, `stderr`
- [ ] Valid JSON stdout → passed through as-is
- [ ] Error case (exit non-zero) → fallback captures `return_code`, `stdout`, `stderr`
- [ ] Empty stdout with stderr → fallback captures stderr
- [ ] `result_text` is always `null` for procedural agents
- [ ] Session completes with status "finished" (even if exit code non-zero)

## Verify via Database

```bash
sqlite3 servers/agent-coordinator/.agent-orchestrator/observability.db \
  "SELECT result_text, result_data FROM events WHERE event_type = 'result' ORDER BY timestamp DESC LIMIT 5"
```

All rows should have `result_text` as empty/null and `result_data` containing either:
- The script's JSON output (pass-through), or
- The fallback structure `{"return_code": N, "stdout": "...", "stderr": "..."}`

## Cleanup

Run `./tests/scripts/reset-db` before the next test.
