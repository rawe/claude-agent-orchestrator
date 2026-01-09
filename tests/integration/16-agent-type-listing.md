# Test: Agent Type Listing

Verify that agent listings include the `type` field.

## Prerequisites

- Database reset: `./tests/scripts/reset-db`
- Agent Coordinator running
- At least one agent configured in the agents directory

## Test Steps

### Step 1: List all agents

```bash
curl -s http://localhost:8765/agents | jq '.'
```

Expected response:
```json
[
  {
    "name": "test-agent",
    "description": "Test agent for integration tests",
    "type": "autonomous",
    "parameters_schema": null,
    "system_prompt": "...",
    "mcp_servers": null,
    "skills": null,
    "tags": [...],
    "capabilities": [],
    "demands": null,
    "status": "active",
    "created_at": "...",
    "modified_at": "..."
  }
]
```

### Step 2: Verify type field for each agent

```bash
curl -s http://localhost:8765/agents | jq '.[].type'
```

Expected output:
```
"autonomous"
```

All agents should have a `type` field with value either `"autonomous"` or `"procedural"`.

### Step 3: Get single agent and verify type

```bash
curl -s http://localhost:8765/agents/test-agent | jq '{name, type, parameters_schema}'
```

Expected response:
```json
{
  "name": "test-agent",
  "type": "autonomous",
  "parameters_schema": null
}
```

## Verification Checklist

- [ ] GET /agents returns array of agents
- [ ] Each agent has `type` field (value: "autonomous" or "procedural")
- [ ] Each agent has `parameters_schema` field (null for autonomous agents)
- [ ] GET /agents/{name} returns single agent with type field
- [ ] Type defaults to "autonomous" for agents without explicit type

## Notes

- Autonomous agents (type: "autonomous") use the implicit schema: `{"prompt": string, required: ["prompt"]}`
- Procedural agents (type: "procedural") use their explicit `parameters_schema`
- The `parameters_schema` field is `null` for autonomous agents without custom schema

## Cleanup

No cleanup needed - read-only test.
