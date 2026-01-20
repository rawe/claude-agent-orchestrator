# Agent Run Hooks

**Status:** Implemented
**Version:** 1.0

## Overview

Agent Run Hooks provide lifecycle integration points that execute during agent run processing. Hooks enable preprocessing of parameters before agent execution and observation of results after completion. They are configured inline within agent blueprints and execute on the coordinator side.

**Key Characteristics:**
- **Coordinator-side execution**: Hooks run on the Agent Coordinator, providing centralized control
- **Agent-triggering**: Hooks invoke other agents, enabling composable AI pipelines
- **Lifecycle-based**: Two hook points corresponding to run start and finish

## Hook Types

Two hook types are supported, corresponding to run lifecycle events:

| Hook Type | Trigger Point | Execution Model | Purpose |
|-----------|---------------|-----------------|---------|
| `on_run_start` | Runner claims run | Synchronous (blocking) | Validate/transform parameters, block invalid runs |
| `on_run_finish` | Run completes | Fire-and-forget | Logging, notifications, trigger downstream actions |

### Capability Comparison

| Capability | `on_run_start` | `on_run_finish` |
|------------|----------------|-----------------|
| Transform data | Yes (parameters) | No (observation-only) |
| Block execution | Yes | No (work already done) |
| Start other agents | Yes | Yes |
| Execution | Synchronous | Fire-and-forget |

## Hook Configuration

Hooks are configured inline within agent blueprints using the `hooks` field:

```json
{
  "name": "data-processor",
  "type": "autonomous",
  "description": "Processes data with validation",
  "hooks": {
    "on_run_start": {
      "type": "agent",
      "agent_name": "input-validator",
      "on_error": "block",
      "timeout_seconds": 60
    },
    "on_run_finish": {
      "type": "agent",
      "agent_name": "audit-logger"
    }
  }
}
```

### Configuration Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"agent"` | Yes | Hook action type (currently only `agent` supported) |
| `agent_name` | string | Yes | Name of the agent to invoke |
| `on_error` | `"block"` \| `"continue"` | No | Behavior when hook fails (default: `continue`) |
| `timeout_seconds` | integer | No | Timeout for agent execution (default: 300) |

**Note:** For `on_run_finish`, `on_error` and `timeout_seconds` are stored but not used since the hook is fire-and-forget.

## Hook Data Flow

### `on_run_start` Hook

**What the hook agent receives:** The raw input parameters of the original run.

```json
// If original run has parameters:
{"prompt": "analyze this data"}

// Hook agent receives exactly:
{"prompt": "analyze this data"}
```

**What the hook agent must return:**

To continue execution (optionally with transformed parameters):
```json
{
  "action": "continue",
  "parameters": {"prompt": "analyze this data with extra context"}
}
```

To block execution:
```json
{
  "action": "block",
  "block_reason": "Invalid input: missing required field"
}
```

### `on_run_finish` Hook

**What the hook agent receives:** The result of the completed run.

Priority order:
1. If `result_data` exists (structured output) → passed directly as parameters
2. If only `result_text` exists → wrapped as `{"prompt": result_text}`

```json
// If main agent produced result_data:
{"summary": "found 5 issues", "count": 5}

// If main agent produced only result_text:
{"prompt": "Analysis complete: found 5 issues..."}
```

**What the hook agent returns:** Nothing required (fire-and-forget). The hook is for observation only.

## Execution Flow

### Run Start with `on_run_start` Hook

The hook executes **after** the run is claimed from the queue but **before** it's returned to the runner. This means the hook blocks the runner's poll response.

```
Runner: GET /runner/runs (poll for runs)
           │
           ▼
┌─────────────────────────────────────┐
│ 1. Claim run from queue             │
│    (run is now assigned to runner)  │
└─────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 2. Check: does agent have           │
│    on_run_start hook configured?    │
└─────────────────────────────────────┘
           │
           ├── No hook → Return run to runner
           │
           ▼ Has hook
┌─────────────────────────────────────┐
│ 3. Execute hook agent synchronously │
│    Input: run.parameters            │
│    Wait for completion (with timeout)│
└─────────────────────────────────────┘
           │
           ├── Hook returns {action: "block"} → Fail run (status=failed), continue polling
           │
           ├── Hook fails + on_error="block" → Fail run (status=failed), continue polling
           │
           ├── Hook fails + on_error="continue" → Return run with original params
           │
           ▼ Hook returns {action: "continue", parameters: {...}}
┌─────────────────────────────────────┐
│ 4. Update run with transformed params│
│    Return run to runner             │
└─────────────────────────────────────┘
```

### Run Completion with `on_run_finish` Hook

```
Runner: POST /runner/runs/{id}/completed
           │
           ▼
┌─────────────────────────────────────┐
│ Mark run as completed               │
│ Checks: does agent have on_run_finish│
│ hook configured?                    │
└─────────────────────────────────────┘
           │
           ├── No hook → Process callbacks, broadcast SSE
           │
           ▼ Has hook
┌─────────────────────────────────────┐
│ Start hook agent (fire-and-forget)  │
│ Input: result_data or result_text   │
│ Don't wait for completion           │
└─────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ Continue with normal completion:    │
│ Process callbacks, broadcast SSE    │
└─────────────────────────────────────┘
```

## Hook Events

Hook execution generates events for observability via SSE:

| Event Type | When | Key Fields |
|------------|------|------------|
| `hook_start` | Hook begins execution | `hook_session_id`, `hook_agent` |
| `hook_complete` | Hook succeeds (on_run_start only) | `action`, `parameters_transformed` |
| `hook_failed` | Hook errors | `error` |
| `hook_blocked` | Hook blocks run (on_run_start only) | `block_reason` |
| `hook_timeout` | Hook times out (on_run_start only) | `error` |

**Note:** `on_run_finish` hooks only emit `hook_start` (and `hook_failed` on setup error) since they are fire-and-forget.

### Event Example

```json
{
  "event_type": "hook_start",
  "session_id": "ses_abc123",
  "timestamp": "2026-01-20T10:30:00Z",
  "tool_name": "hook:on_run_start:input-validator",
  "tool_input": {
    "hook_session_id": "hook_def456",
    "hook_agent": "input-validator"
  }
}
```

## Dashboard Configuration

1. Navigate to **Agents** and select an agent to edit
2. Click the **Hooks** tab
3. Configure hooks:
   - Toggle **Enable on_run_start** or **Enable on_run_finish**
   - Select the hook agent from the dropdown
   - For `on_run_start` only: configure error behavior (`block` or `continue`) and timeout
   - For `on_run_finish`: only agent selection is available (fire-and-forget, no error/timeout config)
4. Click **Save**

## Error Handling

### `on_run_start` Error Behavior

| Scenario | `on_error: "block"` | `on_error: "continue"` |
|----------|---------------------|------------------------|
| Hook agent fails | Run fails with error | Run proceeds with original parameters |
| Hook times out | Run fails with timeout error | Run proceeds with original parameters |
| Hook returns invalid output | Run proceeds (defaults to continue) | Run proceeds |

### `on_run_finish` Error Handling

Since `on_run_finish` is fire-and-forget:
- Setup errors emit `hook_failed` event
- The main run's completion is not affected
- Hook failures are logged but don't block anything

## Use Cases

### 1. Parameter Validation

Block runs with invalid inputs before agent execution:

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

### 2. Parameter Enrichment

Add context or resolve references before execution:

```json
{
  "hooks": {
    "on_run_start": {
      "type": "agent",
      "agent_name": "context-enricher",
      "on_error": "continue"
    }
  }
}
```

### 3. Audit Logging

Log all agent executions for compliance:

```json
{
  "hooks": {
    "on_run_finish": {
      "type": "agent",
      "agent_name": "audit-logger"
    }
  }
}
```

### 4. Agent Chaining

Trigger downstream agents when one completes:

```json
{
  "hooks": {
    "on_run_finish": {
      "type": "agent",
      "agent_name": "data-processor"
    }
  }
}
```

## Known Issues

### Long-Running `on_run_start` Hooks

**Problem:** If an `on_run_start` hook takes longer than the runner's HTTP poll timeout (~35 seconds), the run becomes stuck.

**What happens:**
1. Runner polls for runs, coordinator claims a run and starts the hook
2. Hook executes for longer than 35 seconds
3. Runner's HTTP connection times out, runner starts a new poll
4. Hook eventually completes, but the HTTP response has nowhere to go
5. The run remains in `CLAIMED` status indefinitely — no runner will process it

**Impact:** The run is orphaned. It will only recover on coordinator restart (via stale run recovery after 5 minutes).

**Workaround:** Keep `on_run_start` hooks fast (< 30 seconds). Hooks are intended for validation and light transformation, not heavy processing. If you need long-running preprocessing, consider a separate agent in a pipeline instead of a hook.

## Limitations

- **Single hook per type**: Each agent can have at most one `on_run_start` and one `on_run_finish` hook
- **No recursive hooks**: Hook agents should not have hooks themselves (not enforced, but recommended)
- **Agent-type only**: HTTP webhook hooks are not yet supported
- **Inline configuration**: No reusable/shared hook definitions
- **No result transformation**: `on_run_finish` cannot modify results (observation-only)
- **Hook timeout vs poll timeout**: See "Known Issues" above — long hooks can orphan runs

## Future Considerations

- HTTP webhook type (`type: "http"`) for direct external integrations
- Reusable hook definitions (named hooks that can be referenced)
- Additional hook types (`on_result` for result transformation)

## References

- [Agent Callback Architecture](./agent-callback-architecture.md) - Parent-child orchestration
- [Autonomous Agent Input Schema](./autonomous-agent-input-schema.md) - Parameter validation
- [Autonomous Agent Output Schema](./autonomous-agent-output-schema.md) - Structured output
