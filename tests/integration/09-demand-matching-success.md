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
RUNNER_TAGS=python ./servers/agent-runner/agent-runner -x test-executor
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
    "session_name": "demand-test-success",
    "agent_name": "python-agent",
    "prompt": "Hello"
  }'
```

Record the `run_id` from response.

### Step 6: Verify Run Claimed and Completed

```bash
curl -s http://localhost:8765/runs/<run_id> | python3 -m json.tool
```

**Expected:** Status progresses from `pending` → `claimed` → `running` → `completed`

## Cleanup

```bash
# Delete test agent
curl -X DELETE http://localhost:8765/agents/python-agent

# Delete test session
curl -X DELETE http://localhost:8765/sessions/by-name/demand-test-success
```

## Verification

- [ ] Agent blueprint created with demands
- [ ] Runner registered with tags: ["python"]
- [ ] Run was claimed by matching runner
- [ ] Run completed successfully
