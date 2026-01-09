# Test: Procedural Executor

Verify that the procedural executor runs CLI commands and returns structured results.

## Prerequisites

- Database reset: `./tests/scripts/reset-db`
- Agent Coordinator running
- Agent Runner running with `-x echo` profile
- sse-monitor running

## Test Steps

### Step 1: Verify runner registration with agents

When the runner starts with the procedural profile, it should register the echo agent.

Check the coordinator logs for:
```
[DEBUG]   agents: ['echo']
```

Or query the agents endpoint:

```bash
curl http://localhost:8765/agents
```

Expected: Should include the echo agent with type "procedural":
```json
{
  "name": "echo",
  "description": "Simple echo agent that returns the input message",
  "type": "procedural",
  "command": "scripts/echo/echo",
  "runner_id": "..."
}
```

### Step 2: Create a start_session run for procedural agent

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "agent_name": "echo",
    "parameters": {"message": "Hello from procedural test!"},
    "project_dir": "."
  }'
```

Expected response:
```json
{"run_id":"run_...","session_id":"ses_...","status":"pending"}
```

Note the `session_id` for verification.

### Step 3: Wait for execution

The runner should pick up the run within a few seconds and execute the echo script.

### Step 4: Observe WebSocket events

Watch the sse-monitor output for the `result` event.

## Expected Events (in order)

1. **session_created** (status: pending)
2. **run_start**
3. **session_updated** (status: running)
4. **result** (structured output from procedural agent)
   ```json
   {
     "type": "event",
     "data": {
       "event_type": "result",
       "session_id": "ses_...",
       "timestamp": "...",
       "result_text": null,
       "result_data": {
         "message": "Hello from procedural test!"
       }
     }
   }
   ```
   Note: Procedural agents only use `result_data` (never `result_text`).
   If the script outputs valid JSON, it's passed through as-is.
   If not valid JSON, a fallback structure with `return_code`, `stdout`, `stderr` is returned.

5. **session_updated** (status: finished)
6. **run_completed**

## Verification Checklist

- [ ] Runner registers with echo agent on startup
- [ ] Echo agent appears in /agents endpoint with type "procedural"
- [ ] Echo agent has runner_id set (not null)
- [ ] Run is created successfully with agent_name "echo"
- [ ] Run is routed to the correct runner (echo profile)
- [ ] `result` event is received with structured data
- [ ] `result_data` contains JSON output from echo script
- [ ] Session completes with status "finished"

## Test: Resume should be rejected

Procedural agents are stateless and cannot be resumed:

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "resume_session",
    "session_id": "ses_...",
    "agent_name": "echo",
    "parameters": {"message": "This should fail"}
  }'
```

Expected: 400 error
```json
{
  "detail": {
    "error": "procedural_agent_no_resume",
    "message": "Procedural agents are stateless and cannot be resumed",
    "agent_name": "echo"
  }
}
```

## Test: Parameter validation

Missing required parameter:

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "agent_name": "echo",
    "parameters": {},
    "project_dir": "."
  }'
```

Expected: 400 error with validation details
```json
{
  "detail": {
    "error": "parameter_validation_failed",
    "message": "Parameters do not match agent's parameters_schema",
    "agent_name": "echo",
    "validation_errors": [
      {
        "path": "$",
        "message": "'message' is a required property"
      }
    ]
  }
}
```

## Verify via Database

Check the events table for structured result:

```bash
sqlite3 servers/agent-coordinator/.agent-orchestrator/observability.db \
  "SELECT event_type, result_text, result_data FROM events WHERE session_id = 'ses_...' AND event_type = 'result'"
```

Expected output (result_text is null for procedural agents):
```
result||{"message": "Hello from procedural test!"}
```

## Verify runner_agents table

```bash
sqlite3 servers/agent-coordinator/.agent-orchestrator/observability.db \
  "SELECT name, runner_id, command FROM runner_agents"
```

Expected:
```
echo|runner_...|scripts/echo/echo
```

## Cleanup

Run `./tests/scripts/reset-db` before the next test.
