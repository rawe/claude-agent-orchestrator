# Test: Session with Agent Blueprint

Verify that starting a session with a specific agent blueprint works correctly.

## Prerequisites

- Agent Coordinator running
- Agent Runner running
- sse-monitor running
- At least one agent blueprint registered (for `claude-code` executor)

## Test Steps

### Step 1: List available agent blueprints

```bash
curl -s http://localhost:8765/agents | python -m json.tool
```

Expected response (example):
```json
[
  {
    "name": "researcher",
    "description": "Research agent with web search",
    "system_prompt": "...",
    ...
  }
]
```

**Note**: If no agents are registered, create one first:
```bash
curl -X POST http://localhost:8765/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-agent",
    "description": "A test agent for integration testing",
    "system_prompt": "You are a helpful test assistant. Keep responses brief."
  }'
```

### Step 2: Create a start_session run with agent_name

Use an agent name from Step 1:

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "agent_name": "<agent-name-from-step-1>",
    "parameters": {"prompt": "Hello, what can you do?"},
    "project_dir": "."
  }'
```

Expected response:
```json
{"run_id":"run_...","session_id":"ses_...","status":"pending"}
```

### Step 3: Wait for execution

Watch the runner terminal for:
```
[INFO] executor: Starting session: ses_... (agent=<agent-name>)
```

### Step 4: Observe WebSocket events

Watch the sse-monitor output.

## Expected Events (in order)

1. **session_created** (status: pending)
   ```json
   {"type": "session_created", "session": {"session_id": "ses_...", "status": "pending", "agent_name": "<agent-name>", ...}}
   ```

2. **session_updated** (status: running)
   ```json
   {"type": "session_updated", "session": {"session_id": "ses_...", "status": "running", "agent_name": "<agent-name>", ...}}
   ```

3. **message (user)**
   ```json
   {"type": "event", "data": {"event_type": "message", "session_id": "ses_...", "role": "user", "content": [{"type": "text", "text": "Hello, what can you do?"}], ...}}
   ```

4. **message (assistant)**
   ```json
   {"type": "event", "data": {"event_type": "message", "session_id": "ses_...", "role": "assistant", "content": [{"type": "text", "text": "<response from executor>"}], ...}}
   ```

5. **session_updated** (status: finished)
   ```json
   {"type": "session_updated", "session": {"session_id": "ses_...", "status": "finished", "agent_name": "<agent-name>", ...}}
   ```

6. **run_completed**
   ```json
   {"type": "event", "data": {"event_type": "run_completed", "session_id": "ses_...", "exit_code": 0, "reason": "completed", ...}}
   ```

## Verification Checklist

- [ ] GET /agents returns at least one agent blueprint
- [ ] All events received in correct order
- [ ] `session_id` is consistent across all events (format: `ses_...`)
- [ ] `agent_name` in session_created matches the requested agent
- [ ] `agent_name` in session_updated matches the requested agent
- [ ] With `claude-code`: Response reflects the agent's system_prompt/capabilities
- [ ] run_completed has exit_code 0 and reason "completed"

## Executor-Specific Behavior

### test-executor
- Currently ignores `agent_name` (echo behavior unchanged)
- Future: Could validate agent exists or echo agent info

### claude-code
- Requires agent blueprint to exist (404 error if not found)
- Agent's `system_prompt` is applied to Claude
- Agent's `mcp_servers` are available to Claude

## Error Cases

### Agent not found (claude-code only)

If the agent doesn't exist:
```
[ERROR] supervisor: Run run_... failed: Process exited with code 1
```

Coordinator logs will show:
```
GET /agents/<agent-name> HTTP/1.1" 404 Not Found
```
