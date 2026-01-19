# Agent Run Hooks

**Status:** Design
**Date:** 2025-01-19

## Overview

Agent Run Hooks provide lifecycle integration points that execute during agent run processing. Hooks enable preprocessing of parameters before agent execution and postprocessing of results after completion. They are configured inline within agent blueprints and execute on the coordinator side.

**Key Principles:**
- **Coordinator-side execution**: Hooks run on the Agent Coordinator, providing centralized control
- **Agent-triggering**: Hooks can invoke other agents, enabling composable AI pipelines
- **Schema-defined contracts**: Each hook type has a fixed input/output schema
- **Transformation + Validation**: Hooks can modify data AND block execution

## Motivation

### Problem Statement

Current agent execution is linear: parameters go in, results come out. There's no built-in way to:

| Scenario | Current Behavior | Desired Behavior |
|----------|-----------------|------------------|
| Parameter validation | Manual checks in orchestrating agent | Automated validation hook rejects invalid inputs |
| Input enrichment | Caller must prepare all data | Hook agent enriches parameters (e.g., fetch context) |
| Result formatting | Raw AI output returned | Hook transforms result to required format |
| Audit logging | Requires external integration | Hook agent logs all executions |
| Policy enforcement | No central control point | Hook blocks unauthorized requests |

### Why Framework-Level Hooks?

1. **Composable AI Pipelines**: Chain agents together declaratively without custom orchestration code
2. **Separation of Concerns**: Validation/enrichment logic lives in dedicated agents, not mixed into main agent
3. **Reusable Patterns**: Common preprocessing (auth checks, context loading) defined once, applied to many agents
4. **Centralized Control**: Hooks execute on coordinator - single point for policy enforcement

## Design

### Hook Types

Two hook types are supported, corresponding to run lifecycle events:

| Hook Type | Trigger Point | Purpose |
|-----------|---------------|---------|
| `on_run_start` | Before agent execution begins | Validate/transform parameters, block invalid runs |
| `on_run_finish` | After agent execution completes | Logging, notifications, trigger downstream actions |

### Hook Capabilities Summary

The two hooks have different capabilities due to their timing in the execution lifecycle:

| Capability | `on_run_start` | `on_run_finish` |
|------------|----------------|-----------------|
| **Transform data** | Yes (parameters) | No (observation-only) |
| **Block execution** | Yes | No (work already done) |
| **Start other agents** | Yes | Yes |
| **Call HTTP webhooks** | Yes | Yes |
| **Receives** | Original parameters | Parameters + result + status |
| **Returns** | Transformed params or block | Empty object `{}` |

### Execution Timing

Hooks execute synchronously at specific points in the run lifecycle, triggered by runner API calls:

| Hook | Executes During | API Call | Blocks |
|------|-----------------|----------|--------|
| `on_run_start` | Runner claims run | `GET /runner/runs` (claim) | Runner's poll response |
| `on_run_finish` | Runner reports completion | `POST /runner/runs/{id}/completed` | Runner's completion report |

This design:
- **Preserves API contract**: External clients see no change to `POST /runs` behavior
- **Uses natural timing points**: No additional async processing or state management
- **Keeps complexity in coordinator**: Runners don't need hook awareness

### Hook Actions

Hooks specify a `type` field that determines how the hook is executed. The model supports extensibility, but the initial implementation focuses on agent invocation.

#### Supported Types

| Type | Status | Description |
|------|--------|-------------|
| `agent` | **Implemented** | Start another agent in the system |
| `http` | Future | Call an external HTTP endpoint (see Future Considerations) |

#### Agent Invocation (`type: "agent"`)

Start another agent in the system. The hook agent receives the hook's input schema and must return the hook's output schema.

```json
{
  "type": "agent",
  "agent_name": "parameter-validator",
  "on_error": "block",
  "timeout_seconds": 300
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"agent"` | Yes | Hook action type |
| `agent_name` | string | Yes | Name of the agent to invoke |
| `on_error` | `"block"` \| `"continue"` | Yes | Behavior when hook fails |
| `timeout_seconds` | integer | No | Timeout for agent execution (default: 300) |

### Hook Input/Output Schemas

Each hook type has a well-defined contract. The hook target (agent or webhook) must conform to these schemas.

#### `on_run_start` Hook

**Input (what the hook receives):**

```json
{
  "parameters": { ... },
  "agent_name": "my-agent",
  "session_id": "ses_abc123",
  "run_id": "run_xyz789"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `parameters` | object | Original run parameters (validated against agent's parameters_schema) |
| `agent_name` | string | Name of the agent being started |
| `session_id` | string | Session ID for this run |
| `run_id` | string | Run ID being processed |

**Output (what the hook must return):**

```json
{
  "action": "continue",
  "parameters": { ... }
}
```

Or to block execution:

```json
{
  "action": "block",
  "block_reason": "Insufficient permissions for this operation"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `action` | `"continue"` \| `"block"` | Whether to proceed or block the run |
| `parameters` | object | Transformed parameters (required if action=continue) |
| `block_reason` | string | Human-readable reason (required if action=block) |

#### `on_run_finish` Hook

The `on_run_finish` hook is **observation-only** - it receives the result but cannot transform it. This simplification avoids timing complexities with the event system (where results are sent by the executor before the runner reports completion).

**Input (what the hook receives):**

```json
{
  "parameters": { ... },
  "result_text": "...",
  "result_data": { ... },
  "status": "completed",
  "error": null,
  "session_id": "ses_abc123",
  "run_id": "run_xyz789",
  "agent_name": "my-agent"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `parameters` | object | Original parameters used for the run |
| `result_text` | string \| null | Text result (autonomous agents without output_schema) |
| `result_data` | object \| null | Structured result (procedural agents or agents with output_schema) |
| `status` | `"completed"` \| `"failed"` \| `"stopped"` | Run completion status |
| `error` | string \| null | Error message if status is "failed" |
| `session_id` | string | Session ID |
| `run_id` | string | Run ID |
| `agent_name` | string | Name of the agent that executed |

**Output (what the hook must return):**

```json
{}
```

The output is an empty object. The hook acknowledges receipt but cannot modify the result.

| Aspect | Description |
|--------|-------------|
| Output | Empty object `{}` |
| Transformation | Not supported - result is read-only |
| Primary use cases | Audit logging, notifications, triggering downstream agents |

### Hook Configuration

Hooks are configured inline within agent blueprints. Each agent can have at most one hook per type.

```json
{
  "name": "data-processor",
  "type": "autonomous",
  "description": "Processes data with validation and formatting",
  "parameters_schema": {
    "type": "object",
    "required": ["data_source"],
    "properties": {
      "data_source": { "type": "string" },
      "options": { "type": "object" }
    }
  },
  "output_schema": {
    "type": "object",
    "required": ["processed_count", "summary"],
    "properties": {
      "processed_count": { "type": "integer" },
      "summary": { "type": "string" }
    }
  },

  "hooks": {
    "on_run_start": {
      "type": "agent",
      "agent_name": "input-validator",
      "on_error": "block",
      "timeout_seconds": 60
    },
    "on_run_finish": {
      "type": "agent",
      "agent_name": "audit-logger",
      "on_error": "continue",
      "timeout_seconds": 30
    }
  }
}
```

### Hook Configuration Schema

```json
{
  "hooks": {
    "on_run_start": {
      "type": "agent",
      "agent_name": "string",
      "on_error": "block" | "continue",
      "timeout_seconds": "integer (default: 300)"
    },
    "on_run_finish": {
      // Same structure as on_run_start
    }
  }
}
```

**Note:** The `type` field is required and currently only supports `"agent"`. This enables future extension to other hook types (e.g., `"http"`) without breaking changes.

### Error Handling

Each hook configures its own error behavior via `on_error`:

| `on_error` | Hook Failure Behavior |
|------------|----------------------|
| `"block"` | Main agent run fails with hook error |
| `"continue"` | Main agent run proceeds with original (untransformed) data |

**Failure scenarios:**
- Hook agent/webhook times out
- Hook agent/webhook returns error
- Hook returns invalid output schema
- Network failure (for HTTP webhooks)

### Execution Flow

#### Run Start with `on_run_start` Hook

```
POST /runs arrives
    │
    ▼
┌─────────────────────────────────────┐
│ 1. Validate parameters against      │
│    agent's parameters_schema        │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 2. Check for on_run_start hook      │
│    in agent blueprint               │
└─────────────────────────────────────┘
    │
    ├── No hook ──► Create run with original parameters
    │
    ▼ Has hook
┌─────────────────────────────────────┐
│ 3. Execute hook (agent or HTTP)     │
│    Input: {parameters, agent_name,  │
│            session_id, run_id}      │
└─────────────────────────────────────┘
    │
    ├── Hook returns {action: "block"} ──► Fail run with block_reason
    │
    ├── Hook fails + on_error="block" ──► Fail run with hook error
    │
    ├── Hook fails + on_error="continue" ──► Create run with original parameters
    │
    ▼ Hook returns {action: "continue", parameters: {...}}
┌─────────────────────────────────────┐
│ 4. Create run with TRANSFORMED      │
│    parameters from hook output      │
└─────────────────────────────────────┘
    │
    ▼
Run queued for execution
```

#### Run Completion with `on_run_finish` Hook

The `on_run_finish` hook executes when the runner reports completion via `POST /runner/runs/{run_id}/completed`. This is observation-only - the hook cannot transform the result.

```
Executor sends result event (already stored)
    │
    ▼
Runner: POST /runner/runs/{run_id}/completed
    │
    ▼
┌─────────────────────────────────────┐
│ 1. Check for on_run_finish hook     │
│    in agent blueprint               │
└─────────────────────────────────────┘
    │
    ├── No hook ──► Mark run completed
    │
    ▼ Has hook
┌─────────────────────────────────────┐
│ 2. Execute hook (agent or HTTP)     │
│    Input: {parameters, result_text, │
│            result_data, status, ...}│
│    (Observation only - no transform)│
└─────────────────────────────────────┘
    │
    ├── Hook fails + on_error="block" ──► Log error, continue anyway*
    │
    ├── Hook fails + on_error="continue" ──► Continue normally
    │
    ▼ Hook returns {}
┌─────────────────────────────────────┐
│ 3. Mark run completed               │
│    (Result already stored via       │
│     events - no transformation)     │
└─────────────────────────────────────┘
    │
    ▼
Trigger callbacks, broadcast SSE
```

*Note: For `on_run_finish`, `on_error="block"` only affects error logging/reporting since the agent work is already complete. The run cannot be "failed" retroactively.

### Agent Hooks: Execution Details

When a hook invokes another agent:

1. **Synchronous execution**: Hook blocks until agent completes
2. **Parameter handling**: Depends on target agent's schema (see below)
3. **Result mapping**: Agent's result becomes hook output
4. **No recursion**: Hook agents should NOT have hooks themselves (enforced or documented)

#### Parameter Passing Logic

Hook agents must have a `parameters_schema` that matches the hook input schema. The hook input is passed directly as parameters:

```
Fetch target agent's blueprint
         │
         ▼
Validate hook input against
agent's parameters_schema
         │
    ┌────┴────┐
    │         │
  Valid    Invalid
    │         │
    ▼         ▼
  Start    Hook fails
  agent    → run blocked
```

**Schema Requirements:**

- For `on_run_start` hooks: schema must accept `{parameters, agent_name, session_id, run_id}`
- For `on_run_finish` hooks: schema must accept `{parameters, result_text, result_data, status, error, session_id, run_id, agent_name}`

If validation fails, the hook fails and the run is blocked.

#### Example: Hook Agent

```json
{
  "name": "input-validator",
  "type": "autonomous",
  "description": "Validates and enriches input parameters",
  "parameters_schema": {
    "type": "object",
    "description": "Matches on_run_start hook input schema",
    "required": ["parameters", "agent_name"],
    "properties": {
      "parameters": { "type": "object" },
      "agent_name": { "type": "string" },
      "session_id": { "type": "string" },
      "run_id": { "type": "string" }
    }
  },
  "output_schema": {
    "type": "object",
    "description": "Returns on_run_start hook output schema",
    "required": ["action"],
    "properties": {
      "action": { "type": "string", "enum": ["continue", "block"] },
      "parameters": { "type": "object" },
      "block_reason": { "type": "string" }
    }
  },
  "system_prompt": "You are a parameter validator. Analyze the input and either return parameters (possibly enriched) with action='continue', or block with a reason."
}
```


## Observability

### Hook Execution Events

Hook execution generates events for debugging and monitoring:

| Event Type | When | Fields |
|------------|------|--------|
| `hook_start` | Hook begins execution | `hook_type`, `target_type`, `target_name` |
| `hook_complete` | Hook succeeds | `hook_type`, `duration_ms`, `action` (for on_run_start) |
| `hook_failed` | Hook errors | `hook_type`, `error`, `on_error_behavior` |
| `hook_blocked` | Hook blocks run (on_run_start only) | `hook_type`, `block_reason` |

**Example event:**
```json
{
  "event_type": "hook_complete",
  "session_id": "ses_abc123",
  "run_id": "run_xyz789",
  "timestamp": "2025-01-19T10:30:00Z",
  "hook_type": "on_run_start",
  "target_type": "agent",
  "target_name": "parameter-validator",
  "duration_ms": 1250,
  "action": "continue"
}
```

### Dashboard Visibility

**Runs list:**
- Indicator showing hooks executed (icon or badge)
- Filter by "has hooks" or "hook blocked"

**Run detail view:**
- Hook execution timeline (when each hook ran, duration)
- For `on_run_start`: show original vs transformed parameters
- For blocked runs: show block reason prominently
- Hook errors displayed with full context

## Implementation Considerations

### Coordinator Changes

1. **Blueprint loading**: Parse and validate `hooks` configuration
2. **Run claiming**: Check for `on_run_start` hook, execute if present before returning run to runner
3. **Run completion**: Check for `on_run_finish` hook, execute if present
4. **Hook execution service**: New service to handle agent invocation and HTTP calls
5. **Event generation**: Emit hook events for observability

### Database Changes

No schema changes required. Hooks are stored in agent blueprint JSON. Transformed parameters/results are stored in existing fields.

### Dashboard Changes

1. **Agent Editor**: New "Hooks" tab to configure hooks
2. **Hook type selector**: Currently only `agent` (model supports future types)
3. **Agent picker**: Dropdown to select from available agents
4. **Error behavior**: Radio/toggle for `on_error` setting (`block` / `continue`)
5. **Timeout configuration**: Optional timeout input field

## Primary Use Cases

These are the driving use cases for the initial implementation:

### 1. Agent Chaining (`on_run_finish`)

Connect agents sequentially where one agent's completion triggers the next. The coordinator automatically starts the downstream agent based on hook configuration.

**Scenario:** Data processing pipeline where Agent A extracts data, then Agent B processes it.

```json
{
  "name": "data-extractor",
  "type": "autonomous",
  "output_schema": {
    "type": "object",
    "properties": {
      "records": { "type": "array" },
      "source": { "type": "string" }
    }
  },
  "hooks": {
    "on_run_finish": {
      "type": "agent",
      "agent_name": "data-processor",
      "on_error": "block"
    }
  }
}
```

**How it works:** The coordinator triggers the downstream agent as a fire-and-forget operation. The `data-processor` receives the hook input (including `result_data`) as its parameters.

#### Execution Model: Fire-and-Forget with Parent Linking

The `on_run_finish` hook uses a **fire-and-forget** model:

```
Agent A run completes
    │
    ▼
Run status → "completed"
Result stored, SSE broadcast
    │
    ▼
Hook triggers Agent B
    │
    ▼
Agent B starts as NEW session
  - parent_session_id = Agent A's session
  - Runs independently
  - Client can track via SSE if subscribed
```

**Key characteristics:**
- Original session completes normally - client gets that result immediately
- Downstream agent is a **child session** (linked via `parent_session_id`)
- No callback mechanism - hooks are fire-and-forget
- If the downstream agent needs to send results back, it can explicitly use `ao-resume` on the parent session (the `session_id` is available in the hook input)

**Why fire-and-forget?**

Adding a callback option creates complexity that doesn't fit the existing callback architecture:
- Callbacks expect idle parents waiting for results
- With chained hooks (A→B→C), result aggregation becomes ambiguous
- Hooks are reactive side effects, not transactional operations

For orchestration patterns requiring result flow, use the existing callback-based async mechanism (`execution_mode: async_callback`) instead of hooks.

### 2. Parameter Enrichment (`on_run_start`)

Enrich valid parameters with additional data before agent execution. The incoming parameters must already pass validation; the hook adds context, resolves references, or fetches supplementary data.

**Scenario:** A procedural agent needs a resolved file path, but callers only provide a reference ID.

```json
{
  "name": "report-generator",
  "type": "procedural",
  "parameters_schema": {
    "type": "object",
    "required": ["report_id"],
    "properties": {
      "report_id": { "type": "string" },
      "resolved_path": { "type": "string" }
    }
  },
  "hooks": {
    "on_run_start": {
      "type": "agent",
      "agent_name": "path-resolver",
      "on_error": "block"
    }
  }
}
```

The `path-resolver` agent receives `{report_id: "R123"}` and returns enriched parameters `{report_id: "R123", resolved_path: "/data/reports/R123.csv"}`.

**Limitation:** The hook cannot change the parameter structure - incoming parameters must already pass the agent's `parameters_schema` validation. The hook can only add or modify field values.

## Additional Use Cases

### 3. Parameter Validation

Block runs with invalid or dangerous inputs:

```json
{
  "hooks": {
    "on_run_start": {
      "type": "agent",
      "agent_name": "security-validator",
      "on_error": "block"
    }
  }
}
```

### 4. Audit Logging

Log all agent executions via a logging agent:

```json
{
  "hooks": {
    "on_run_finish": {
      "type": "agent",
      "agent_name": "audit-logger",
      "on_error": "continue"
    }
  }
}
```

## Future Considerations

### HTTP Webhook Type (`type: "http"`)

Add support for calling external HTTP endpoints directly, without requiring a wrapper agent:

```json
{
  "type": "http",
  "url": "https://api.example.com/validate",
  "method": "POST",
  "headers": {
    "Authorization": "Bearer ${API_TOKEN}",
    "Content-Type": "application/json"
  },
  "on_error": "continue",
  "timeout_seconds": 30
}
```

**Request format:** Hook input sent as JSON body
**Response format:** Must match hook output schema

**Use cases:**
- Direct integration with external audit/logging systems
- Webhook-based approval workflows
- Integration with third-party services without wrapper agents

The `type` field is already present in the model, so adding HTTP support is non-breaking.

### Reusable Hook Definitions

Currently hooks are inline. Future enhancement could add named hooks (similar to capabilities):

```json
// Hook definition (future)
{
  "name": "audit-logger",
  "type": "http",
  "url": "https://audit.company.com/log",
  "on_error": "continue"
}

// Agent references it (future)
{
  "hooks": {
    "on_run_finish": { "$ref": "audit-logger" }
  }
}
```

### Additional Hook Types

Potential future hooks:

| Hook | Trigger | Use Case |
|------|---------|----------|
| `on_result` | When result event arrives | **Result transformation** (before storage/broadcast) |
| `on_tool_call` | Before tool execution | Tool-level policy enforcement |
| `on_error` | Agent execution fails | Custom error handling |
| `on_timeout` | Execution times out | Timeout-specific handling |

**Note on `on_result`:** The current `on_run_finish` hook cannot transform results due to timing constraints (results are sent via events before completion is reported). If result transformation is needed, a dedicated `on_result` hook that triggers when the result event arrives would be the appropriate solution.

### Async Hooks

Fire-and-forget hooks that don't block execution:

```json
{
  "hooks": {
    "on_run_finish": {
      "type": "http",
      "url": "https://notifications.com/notify",
      "mode": "async",
      "on_error": "ignore"
    }
  }
}
```

## Out of Scope (Current Design)

- **Result transformation**: `on_run_finish` is observation-only due to event timing; future `on_result` hook could address this
- **Multiple hooks per type**: Single hook per type for simplicity
- **Hook chaining**: Use hook agent's internal logic for multi-step processing
- **Async (fire-and-forget) hooks**: Sync only for now
- **Global hooks**: No system-wide hooks; per-agent only
- **Hook on hook**: Hook agents should not have hooks themselves
- **Reusable hook definitions**: Hooks are inline only; future enhancement could add named hooks

## References

- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture overview
- [agent-types.md](../architecture/agent-types.md) - Agent types and parameter schemas
- [agent-callback-architecture.md](../features/agent-callback-architecture.md) - Callback-based orchestration
- [ADR-007: Hybrid Hook Configuration](../adr/ADR-007-hybrid-hook-configuration.md) - Claude Code executor hooks (different scope)
