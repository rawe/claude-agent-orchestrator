# Test: Runner Reconnection Recognition

Verify that a restarted runner gets the same deterministic ID (ADR-012).

## Prerequisites

- Agent Coordinator running
- Agent Runner running with `-x test-executor` profile

## Test Steps

### Step 1: Record Current Runner ID

```bash
curl -s http://localhost:8765/runners | grep -o '"runner_id":"[^"]*"'
```

Record the `runner_id` (format: `lnch_` + 12 hex chars).

### Step 2: Restart Runner

Stop the Agent Runner (Ctrl+C), then restart with same profile:

```bash
./servers/agent-runner/agent-runner -x test-executor
```

### Step 3: Verify Same ID

```bash
curl -s http://localhost:8765/runners | grep -o '"runner_id":"[^"]*"'
```

**Expected:** Same `runner_id` as Step 1.

## Verification

- [ ] Runner ID unchanged after restart (same hostname + project_dir + executor_profile = same ID)
