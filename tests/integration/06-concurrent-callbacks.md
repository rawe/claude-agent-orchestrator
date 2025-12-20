# Test: Concurrent Callbacks (Race Condition Detection)

Verify that multiple child agents completing in rapid succession all have their callbacks properly received by the parent agent. This test is designed to detect race conditions where callbacks may be "swallowed" or overwritten.

Uses `mode=async_callback` for all child agents per ADR-003.

## Prerequisites

- Agent Coordinator running
- Agent Runner running with `claude-code` executor
- ws-monitor running
- Agent Orchestrator MCP server running on port 9500:
  ```bash
  uv run --script mcps/agent-orchestrator/agent-orchestrator-mcp.py --http-mode --port 9500
  ```
- `agent-orchestrator` blueprint copied (see `tests/README.md` → "Agent Blueprints")

## Test Design

**Wave-based timing:**
- Wave 1 (5 seconds): 3 agents complete nearly simultaneously
- Wave 2 (10 seconds): 2 agents complete nearly simultaneously

This creates stress on the callback handling system to expose potential race conditions.

## Test Steps

### Step 1: Verify setup

```bash
curl -s http://localhost:8765/agents | grep agent-orchestrator
```

### Step 2: Start parent orchestrator session

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "agent_name": "agent-orchestrator",
    "prompt": "Start 5 child agents in callback mode with these wait times:\n- Agent 1: wait 5 seconds, then respond \"callback-001\"\n- Agent 2: wait 5 seconds, then respond \"callback-002\"\n- Agent 3: wait 5 seconds, then respond \"callback-003\"\n- Agent 4: wait 10 seconds, then respond \"callback-004\"\n- Agent 5: wait 10 seconds, then respond \"callback-005\"\n\nEach agent must ONLY run: sleep N && echo \"callback-XXX\"\nDo not respond until you have received all callbacks.",
    "project_dir": "."
  }'
```

Expected response:
```json
{"run_id":"run_...","session_id":"ses_...","status":"pending"}
```

Note the parent `session_id`.

### Step 3: Wait for all agents to complete

Monitor ws-monitor for completion events. Expected timeline:
- ~5 seconds: Agents 1, 2, 3 complete (Wave 1)
- ~10 seconds: Agents 4, 5 complete (Wave 2)

Wait approximately 60-90 seconds for parent to process all callbacks.

### Step 4: Verify all child sessions completed

```bash
curl -s http://localhost:8765/sessions | python -m json.tool | grep -E "(session_id|status)" | head -20
```

All 5 child sessions should show as completed.

### Step 5: Resume parent to verify received callbacks

This is the critical verification step. Resume the parent session and ask it to check its own conversation history:

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "resume_session",
    "session_id": "<parent_session_id>",
    "prompt": "IMPORTANT: Check your conversation history ONLY. Do NOT use any tools or API calls.\n\nList ALL child agent callbacks you received in this session. For each callback, state:\n1. The agent session ID\n2. The callback message content\n\nThen confirm: Did you receive callbacks from ALL 5 agents? Answer YES or NO, and list any missing agents."
  }'
```

### Step 6: Check parent response

Wait for the parent to respond. The response will reveal which callbacks were actually recorded in its conversation history.

## Expected Behavior

### Success Case
1. All 5 child agents complete
2. Parent receives all 5 callbacks in its conversation history
3. Parent confirms: "YES, received callbacks from all 5 agents"

### Failure Case (Race Condition Detected)
1. All 5 child agents complete
2. Parent's history is missing 1 or more callbacks
3. Parent confirms: "NO, missing callbacks from: [session_id]"

## Verification Checklist

- [ ] All 5 child sessions created (each with unique `session_id` format `ses_...`)
- [ ] All 5 child sessions completed (check via API)
- [ ] Parent received callback from agent 1
- [ ] Parent received callback from agent 2
- [ ] Parent received callback from agent 3
- [ ] Parent received callback from agent 4
- [ ] Parent received callback from agent 5
- [ ] Parent confirms all 5 callbacks in history verification step

## Interpreting Results

### If callbacks are missing:
This indicates a race condition in the callback handling system. Possible causes:
- Session resume overwrites previous resume
- Callback messages not properly queued
- Locking issues in session state management

### Timing analysis:
Note which callbacks are missing. If Wave 1 agents (1-3) are affected more than Wave 2, it suggests concurrent callbacks are being overwritten.

## WebSocket Events to Monitor

```
# Wave 1 completions (~5 sec)
{"type": "event", "data": {"event_type": "session_stop", "session_id": "ses_<child1>", ...}}
{"type": "event", "data": {"event_type": "session_stop", "session_id": "ses_<child2>", ...}}
{"type": "event", "data": {"event_type": "session_stop", "session_id": "ses_<child3>", ...}}

# Wave 2 completions (~10 sec)
{"type": "event", "data": {"event_type": "session_stop", "session_id": "ses_<child4>", ...}}
{"type": "event", "data": {"event_type": "session_stop", "session_id": "ses_<child5>", ...}}

# Parent resumes (should see 5 resume events)
{"type": "event", "data": {"event_type": "session_start", "session_id": "ses_<parent>", ...}}
```

## Troubleshooting

### Parent doesn't spawn all 5 agents
- Check MCP server logs for errors
- Verify agent-orchestrator blueprint has correct MCP configuration

### Parent responds before all callbacks
- Increase wait times (e.g., 10s and 20s instead of 5s and 10s)
- Check if parent prompt is being followed correctly

### Cannot determine callback status
- Check parent session's full conversation via logs
- Look at Agent Runner logs for callback delivery attempts
