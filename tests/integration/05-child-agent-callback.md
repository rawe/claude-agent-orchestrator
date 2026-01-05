# Test: Child Agent with Callback

Verify that an orchestrator agent can spawn a child agent in callback mode (`mode=async_callback`) with parent-child relationship.

**Note**: As of ADR-003, `parent_session_id` is always set for child sessions regardless of execution mode. The `execution_mode` field on runs controls callback behavior (execution_mode is stored on runs, not sessions).

## Prerequisites

- Agent Coordinator running
- Agent Runner running with `claude-code` executor
- sse-monitor running
- `agent-orchestrator` blueprint copied (see `tests/README.md` → "Agent Blueprints")

## Test Steps

### Step 1: Verify setup

```bash
curl -s http://localhost:8765/agents | grep agent-orchestrator
```

### Step 2: Create orchestrator session with callback mode

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "agent_name": "agent-orchestrator",
    "prompt": "Start a child agent in callback mode. The child should just say hello and exit.",
    "project_dir": "."
  }'
```

Expected response:
```json
{"run_id":"run_...","session_id":"ses_...","status":"pending"}
```

Note the `session_id` - this is the parent session.

Note: The key difference is **"in callback mode"** in the prompt.

### Step 3: Wait for completion

Both parent and child sessions should complete. The parent will be resumed after the child completes.

### Step 4: Verify parent-child relationship

```bash
curl -s http://localhost:8765/sessions | python -m json.tool | grep -B2 -A8 "parent_session_id"
```

## Expected Behavior

1. Parent session starts
2. Parent calls MCP tool with `mode=async_callback`
3. Child run created with `execution_mode=async_callback` and child session with `parent_session_id` set
4. Parent session pauses (waiting for callback)
5. Child executes and completes
6. Parent session resumes with callback message
7. Parent receives child result and completes

## Verification Checklist

- [ ] Child session has `parent_session_id` set to parent's `session_id`
- [ ] Child run has `execution_mode` set to `async_callback` (verify via runs API, see below)
- [ ] Both session IDs follow format `ses_...`
- [ ] Parent receives callback message: "The child agent session ... has completed"
- [ ] Parent session resumes after child completes
- [ ] Both sessions complete successfully

### Verifying execution_mode on runs

Since `execution_mode` is stored on runs (not sessions), verify via the runs API:

```bash
# List all runs and check execution_mode
curl -s http://localhost:8765/runs | python -m json.tool | grep -A5 '"execution_mode"'

# Or filter by session_id to find the child's run
curl -s "http://localhost:8765/runs?session_id=ses_CHILD_ID" | python -m json.tool
```

The child's run should show `"execution_mode": "async_callback"`.

## Difference from Sync Mode (04-child-agent-sync)

| Aspect | Sync Mode | Callback Mode |
|--------|-----------|---------------|
| Run's `execution_mode` | `sync` | `async_callback` |
| Session's `parent_session_id` | Set to parent | Set to parent |
| Parent waits | Blocks during call | Pauses, resumes on callback |
| Use case | Quick tasks | Long-running child tasks |

**Note**: `execution_mode` is a property of runs, not sessions. Each run can have a different execution mode, allowing callback behavior to vary per-run even for the same session.
