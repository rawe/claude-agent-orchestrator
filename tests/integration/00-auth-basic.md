# Test: Basic Authentication

Verify that authentication works end-to-end with Runner and Executor.

## Prerequisites

- `.env` file exists with both `ADMIN_API_KEY` and `AGENT_ORCHESTRATOR_API_KEY` set
- Port 8765 is free: `lsof -i :8765` should return nothing
- Database reset: `./tests/scripts/reset-db`
- No services running (clean start)

## Test Steps

### Step 1: Start services

Start each service in a separate terminal (or background process):

```bash
# Terminal 1 - Agent Coordinator
./tests/scripts/start-coordinator
```

Expected: Server starts with authentication enabled (no "AUTH_DISABLED" warning).

```bash
# Terminal 2 - Agent Runner
./tests/scripts/start-runner test-executor
```

Expected: Runner registers successfully (no authentication errors).

```bash
# Terminal 3 - SSE Monitor
./tests/scripts/start-sse-monitor
```

Expected: SSE monitor connects (no 401/403 errors).

### Step 2: Test authenticated request

```bash
source .env
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AGENT_ORCHESTRATOR_API_KEY" \
  -d '{
    "type": "start_session",
    "prompt": "Auth test",
    "project_dir": "."
  }'
```

Expected: Run created successfully with `run_id` and `session_id`.

### Step 3: Test unauthenticated request (should fail)

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "prompt": "Should fail",
    "project_dir": "."
  }'
```

Expected: 401 Unauthorized response.

### Step 4: Verify run execution

Watch SSE monitor output for:
1. `session_created` event (status: pending)
2. `session_updated` (status: running)
3. `event` (user message)
4. `event` (assistant message)
5. `session_updated` (status: finished)

## Verification Checklist

- [ ] Coordinator starts with auth enabled
- [ ] Runner registers without authentication errors
- [ ] SSE monitor connects without 401/403
- [ ] Authenticated POST /runs succeeds
- [ ] Unauthenticated POST /runs returns 401
- [ ] Run executes and completes (events visible in SSE monitor)

## Cleanup

Stop all services with Ctrl+C.
