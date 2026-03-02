# NDJSON Protocol Reference: Runner ↔ Executor

> **Note**: The `run_id` field shown in message examples below will be removed per
> `NDJSON-PROTOCOL-SIMPLIFICATION.md`. The executor is session-pure; the runner owns
> run_id mapping via the registry. Update this document when the code changes land.

## Overview

The executor process communicates with the runner via two NDJSON (newline-delimited JSON) channels:

- **stdin** (Runner → Executor): Turn requests and lifecycle commands
- **stdout** (Executor → Runner): Turn completion signals

Session events (bind, user_message, assistant_message, result) continue to flow via HTTP to the Runner Gateway — stdout is **only** for turn lifecycle signaling.

## Channel: stdin (Runner → Executor)

Each message is a single JSON object on its own line, terminated by `\n`.

### Message 1: Initial Invocation (first line)

The first stdin line uses the existing `ExecutorInvocation` schema. This establishes the session.

```json
{
  "schema_version": "2.2",
  "mode": "start",
  "session_id": "ses_abc123",
  "parameters": {
    "prompt": "Hello, build a REST API"
  },
  "project_dir": "/path/to/project",
  "agent_blueprint": {
    "name": "coding-agent",
    "system_prompt": "You are a coding assistant.",
    "mcp_servers": { }
  },
  "executor_config": {
    "permission_mode": "bypassPermissions",
    "setting_sources": ["user", "project", "local"],
    "model": null
  },
  "metadata": {
    "run_id": "run_001"
  }
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `schema_version` | Yes | Must be `"2.0"` or `"2.2"` |
| `mode` | Yes | `"start"` for multi-turn sessions |
| `session_id` | Yes | Coordinator-generated session ID (ADR-010) |
| `parameters.prompt` | Yes | User prompt for turn 1 |
| `project_dir` | No | Working directory for Claude |
| `agent_blueprint` | No | Agent config (system_prompt, MCP servers, output_schema) |
| `executor_config` | No | Claude-specific config (permission_mode, model, etc.) |
| `metadata.run_id` | No | Run ID for turn_complete correlation |

**Processing**: The executor parses this via `ExecutorInvocation.from_json()`, builds `ClaudeAgentOptions` (system_prompt, hooks, MCP servers, permission_mode), opens `ClaudeSDKClient`, and executes turn 1.

### Subsequent Messages: Turn Request

```json
{
  "type": "turn",
  "run_id": "run_002",
  "parameters": {
    "prompt": "Now add authentication to the API"
  }
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | Must be `"turn"` |
| `run_id` | Yes | Run ID for this turn (from coordinator) |
| `parameters.prompt` | Yes | User prompt for this turn |

**Processing**: The executor reads the prompt from `parameters.prompt`, emits a `user_message` event via HTTP, calls `client.query(prompt)` on the existing `ClaudeSDKClient`, processes the response stream, and emits result events.

**Note**: `agent_blueprint` is accepted but **ignored** on subsequent turns. Session configuration (system_prompt, MCP servers, hooks) is fixed at turn 1.

### Lifecycle: Shutdown

```json
{
  "type": "shutdown"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | Must be `"shutdown"` |

**Processing**: The executor breaks out of the turn loop. The `async with ClaudeSDKClient` context manager exits, terminating the CLI subprocess. The executor process exits with code 0.

### Implicit Shutdown: EOF

If stdin is closed (EOF), the executor treats it identically to a shutdown message — breaks from the loop and exits cleanly.

## Channel: stdout (Executor → Runner)

### Turn Complete

Written after each turn (including turn 1):

```json
{
  "type": "turn_complete",
  "run_id": "run_001",
  "result": "Here is the REST API implementation..."
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"turn_complete"` |
| `run_id` | string | Echoes the run_id from the turn request (or from `metadata.run_id` for turn 1) |
| `result` | string | The assistant's response text. Empty string if no result. |

**Critical**: Each `turn_complete` line is written with `flush=True` to ensure the runner's stdout reader sees it immediately (Python buffers pipe output by default).

**Non-JSON lines**: The executor may write non-JSON output to stdout (e.g., from libraries). Consumers must skip lines that fail `json.loads()`.

## Message Flow Example

```
TIME    STDIN (runner→executor)              STDOUT (executor→runner)         HTTP (executor→gateway)
─────   ───────────────────────              ────────────────────────         ───────────────────────
t0      {"schema_version":"2.2",...}
t1                                                                            POST /bind (session binding)
t2                                                                            POST /events (user_message)
t3                                                                            POST /events (assistant_message)
t4                                                                            POST /events (result)
t5                                           {"type":"turn_complete",...}
        ─── executor idle, waiting for stdin ───
t6      {"type":"turn",...}
t7                                                                            POST /events (user_message)
t8                                                                            POST /events (assistant_message)
t9                                                                            POST /events (result)
t10                                          {"type":"turn_complete",...}
        ─── executor idle, waiting for stdin ───
t11     {"type":"shutdown"}
t12     ─── process exits (code 0) ───
```

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Invalid JSON on stdin | Logged to stderr, line skipped, executor continues waiting |
| Unknown `type` field | Logged to stderr, line skipped, executor continues waiting |
| SDK error during turn | Exception propagated, process exits with code 1 |
| Process crash | Runner supervisor detects via `process.poll()`, reports `run_failed` |

## Relationship to Session Events (HTTP)

The NDJSON protocol handles **turn lifecycle** only. All session content flows via HTTP:

| Event | Channel | When |
|-------|---------|------|
| Session bind | HTTP | Turn 1, after `SystemMessage.init` |
| user_message | HTTP | Before each `client.query()` call |
| assistant_message | HTTP | After `ResultMessage` received |
| result | HTTP | After each turn completes |
| turn_complete | stdout | After each turn (lifecycle signal to runner) |

## Implementation Files

| Component | File | Role |
|-----------|------|------|
| Executor turn loop | `executors/claude-sdk-executor/lib/sdk_client.py` | `run_multi_turn_session()` |
| Executor entry point | `executors/claude-sdk-executor/ao-claude-code-exec` | stdin readline, routing |
| Test harness | `tests/integration/infrastructure/harness.py` | `MultiTurnExecutor` class |

## Phase 2 Integration Notes (for runner-side implementation)

When the runner integrates this protocol:

1. **Spawning**: `Popen(stdin=PIPE, stdout=PIPE)` — keep both pipes open
2. **Sending turns**: Write NDJSON line to `process.stdin`, flush
3. **Detecting completion**: Read `process.stdout` lines, parse JSON, match `turn_complete`
4. **Session routing**: Map `session_id → process` to route resume_session runs to existing executors
5. **Shutdown**: Write `{"type": "shutdown"}\n` when idle timeout expires or session ends
6. **Crash detection**: Continue polling `process.poll()` alongside stdout reading
