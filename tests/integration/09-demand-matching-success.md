# Test: Runner with Matching Tags Claims Run

Verify that a runner with matching capability tags can claim a run with demands (ADR-011).

## Prerequisites

- Agent Coordinator running
- Agent Runner NOT running (will start with specific tags)

## Test Steps

### Step 1: Create Agent Blueprint with Demands

```bash
curl -X POST http://localhost:8765/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "python-agent",
    "description": "Test agent requiring python tag",
    "demands": {
      "tags": ["python"]
    }
  }'
```

**Expected:** 201 Created

### Step 2: Verify Blueprint Has Demands

```bash
curl -s http://localhost:8765/agents/python-agent | python3 -m json.tool
```

**Expected:** Response includes `"demands": {"tags": ["python"]}`

### Step 3: Start Runner WITH Matching Tags

```bash
RUNNER_TAGS=python ./servers/agent-runner/agent-runner -x test-executor  # -x is --profile
```

### Step 4: Verify Runner Registered with Tags

```bash
curl -s http://localhost:8765/runners | python3 -m json.tool
```

**Expected:** Runner shows `"tags": ["python"]`

### Step 5: Create Run with Blueprint

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "agent_name": "python-agent",
    "parameters": {"prompt": "Hello"}
  }'
```

Record the `run_id` and `session_id` from response.

**Expected response:**
```json
{"run_id":"run_...","session_id":"ses_...","status":"pending"}
```

### Step 6: Verify Run Claimed and Completed

```bash
curl -s http://localhost:8765/runs/<run_id> | python3 -m json.tool
```

**Expected:** Status progresses from `pending` → `claimed` → `running` → `completed`

## Cleanup

```bash
# Delete test agent
curl -X DELETE http://localhost:8765/agents/python-agent

# Delete test session (use session_id from step 5)
curl -X DELETE http://localhost:8765/sessions/<session_id>
```

## Verification

- [ ] Agent blueprint created with demands
- [ ] Runner registered with tags: ["python"]
- [ ] Run was claimed by matching runner
- [ ] Run completed successfully
- [ ] `session_id` in response follows format `ses_...`
