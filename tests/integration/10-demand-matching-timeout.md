# Test: Run Times Out When No Matching Runner

Verify that a run with demands times out when no runner can satisfy the demands (ADR-011).

## Prerequisites

- Agent Coordinator running
- Agent Runner running with `-x test-executor` (NO special tags)

## Test Steps

### Step 1: Verify Runner Has No Special Tags

```bash
curl -s http://localhost:8765/runners | python3 -m json.tool
```

**Expected:** Runner shows `"tags": []` (empty array)

### Step 2: Create Agent Blueprint with Unsatisfiable Demands

```bash
curl -X POST http://localhost:8765/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "special-agent",
    "description": "Test agent requiring special tag no runner has",
    "demands": {
      "tags": ["nonexistent-capability"]
    }
  }'
```

**Expected:** 201 Created

### Step 3: Set Short Timeout for Testing

The default timeout is 5 minutes. For faster testing, restart coordinator with:

```bash
RUN_NO_MATCH_TIMEOUT=10 uv run python -m main
```

This sets timeout to 10 seconds.

### Step 4: Create Run with Blueprint

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "session_name": "demand-test-timeout",
    "agent_name": "special-agent",
    "prompt": "Hello"
  }'
```

Record the `run_id` from response.

### Step 5: Verify Run Stays Pending

Immediately check status:

```bash
curl -s http://localhost:8765/runs/<run_id> | python3 -m json.tool
```

**Expected:** Status is `pending` (no runner can claim)

### Step 6: Wait for Timeout and Verify Failure

Wait for timeout period (10 seconds if using short timeout), then check:

```bash
curl -s http://localhost:8765/runs/<run_id> | python3 -m json.tool
```

**Expected:**
- Status: `failed`
- Error: `"No matching runner available within timeout"`

## Cleanup

```bash
# Delete test agent
curl -X DELETE http://localhost:8765/agents/special-agent
```

## Verification

- [ ] Agent blueprint created with unsatisfiable demands
- [ ] Run stayed in pending status (not claimed)
- [ ] Run eventually failed with "No matching runner" error
- [ ] ws-monitor shows `run_failed` event with timeout error
