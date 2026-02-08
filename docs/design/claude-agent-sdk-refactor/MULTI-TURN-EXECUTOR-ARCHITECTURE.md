# Multi-Turn Executor Architecture Reference

## Overview

The multi-turn executor keeps a single `ClaudeSDKClient` process alive across multiple conversation turns. Instead of spawning a new process per turn (and attempting `--resume`), subsequent turns are sent as NDJSON messages on stdin to the existing process.

This replaces the broken `--resume` + `--input-format stream-json` CLI combination (GitHub #16712).

## Architecture Decision

| Option | Hooks | Resume | Chosen |
|--------|-------|--------|--------|
| `ClaudeSDKClient` + new process per turn | Yes | No (`--resume` + stream-json unsupported) | - |
| `query()` (print mode) + `--resume` | No (hooks broken in print mode) | Yes | - |
| `ClaudeSDKClient` alive across turns | Yes (registered once, persist) | N/A (same process, no resume needed) | **Yes** |

**Rationale**: Hooks are non-negotiable. The SDK's `ClaudeSDKClient` supports multiple `query()` calls on the same instance — hooks registered during `initialize()` persist across all turns. No resume flag needed because the conversation context lives in the running CLI subprocess.

## SDK Internals (validated from SDK v0.1.33, CLI 2.1.37)

- `ClaudeSDKClient.__aenter__()` → spawns CLI subprocess, calls `connect()` → `initialize()` (registers hooks)
- `ClaudeSDKClient.__aexit__()` → kills CLI subprocess
- `client.query(prompt)` → writes one JSON line to CLI subprocess stdin (does NOT spawn new process)
- `client.receive_response()` → yields messages until `ResultMessage`, then returns. Client stays usable.
- `SessionEventEmitter.bind()` is guarded by `if self._bound` — safe to call on every turn (no-ops after first)
- `SystemMessage.init` is only sent on the **first** `query()` call, not subsequent ones

## Process Lifecycle

```
                    ┌──────────────────────────────────────────────────────┐
                    │           Executor Process Lifecycle                 │
                    │                                                      │
  stdin line 1      │   ┌─────────┐    ┌──────────────────────────────┐   │
  (invocation) ────►│   │ Parse   │───►│ async with ClaudeSDKClient   │   │
                    │   │ initial │    │                              │   │
                    │   │ payload │    │   ┌──────┐  ┌───────────┐   │   │  stdout
                    │   └─────────┘    │   │Turn 1│─►│turn_complete──►├───┼──────►
                    │                  │   └──────┘  └───────────┘   │   │
  stdin line 2      │                  │                              │   │
  (turn) ──────────►│                  │   ┌──────┐  ┌───────────┐   │   │  stdout
                    │                  │   │Turn 2│─►│turn_complete──►├───┼──────►
                    │                  │   └──────┘  └───────────┘   │   │
  stdin line N      │                  │                              │   │
  (shutdown) ──────►│                  │   break loop                 │   │
                    │                  │                              │   │
                    │                  └──────────────────────────────┘   │
                    │                          │                          │
                    │                     process exit                    │
                    └──────────────────────────────────────────────────────┘
```

### Process States

| State | Description | Entry Trigger | Exit Trigger |
|-------|-------------|---------------|--------------|
| **Starting** | Process spawned, reading first stdin line | `Popen` by runner | First line parsed |
| **Initializing** | `ClaudeSDKClient` connecting, hooks registering | `async with ClaudeSDKClient` entered | `SystemMessage.init` received |
| **Executing** | Running a turn (`client.query()` + `receive_response()`) | Prompt received | `ResultMessage` received |
| **Idle** | Turn complete, waiting for next stdin line | `turn_complete` emitted to stdout | Next stdin line or EOF/shutdown |
| **Shutting down** | Closing `ClaudeSDKClient`, cleaning up | `shutdown` message or stdin EOF | Context manager exits |
| **Exited** | Process terminated | Normal exit or crash | — |

## Session Configuration Lifecycle

Configuration is established **once** on turn 1 and persists:

| Config | Set When | Persists | Changeable on Turn N? |
|--------|----------|----------|-----------------------|
| `system_prompt` | Turn 1 (from `agent_blueprint`) | Yes | No (SDK sets once) |
| `permission_mode` | Turn 1 (from `executor_config`) | Yes | No |
| `hooks` (PostToolUse) | Turn 1 (`initialize()`) | Yes | No |
| `MCP servers` | Turn 1 (from `agent_blueprint`) | Yes | No |
| `model` | Turn 1 (from `executor_config`) | Yes | No |

## Session Event Emission Per Turn

### Turn 1 (Initial)
1. `SystemMessage.init` arrives → extract `executor_session_id`
2. `emitter.bind(executor_session_id, project_dir)` → HTTP POST to gateway
3. `set_hook_emitter(emitter)` → hooks can now emit events
4. `emitter.emit_user_message(prompt)` → HTTP POST (inside SystemMessage handler)
5. `ResultMessage` arrives → `emitter.emit_assistant_message(result)` → HTTP POST
6. `emitter.emit_result(result_text=result)` → HTTP POST
7. `turn_complete` → stdout NDJSON

### Turn N (Subsequent)
1. `emitter.emit_user_message(prompt)` → HTTP POST (**before** `client.query()`)
2. `ResultMessage` arrives → `emitter.emit_assistant_message(result)` → HTTP POST
3. `emitter.emit_result(result_text=result)` → HTTP POST
4. `turn_complete` → stdout NDJSON

**Key difference**: On turn 1, `emit_user_message` happens inside the `SystemMessage.init` handler (after session binding). On subsequent turns, it happens before `client.query()` because the session is already bound.

## Crash Recovery

**Policy: Accept session loss on crash** (Phase 1).

| Scenario | Detection | Action |
|----------|-----------|--------|
| Process exits mid-turn | `process.poll()` returns non-zero | Supervisor reports `run_failed` |
| Process exits while idle | `process.poll()` returns non-zero | Supervisor removes from session registry |
| stdin write fails (broken pipe) | `BrokenPipeError` on runner side | Runner reports `run_failed` |

The `executor_session_id` is stored in the coordinator. If the SDK ever supports `ClaudeSDKClient` resume, recovery becomes possible without architectural changes.

## Resource Footprint

Per idle executor process:
- Python interpreter: ~30-50 MB RSS
- Claude CLI subprocess: ~20-30 MB RSS (bundled binary)
- `ClaudeSDKClient` with open stdin/stdout pipes
- **Total estimated**: ~50-80 MB per idle session

### Planned Controls (Phase 3)
- **Idle timeout**: Supervisor sends shutdown after N minutes of no turns (default: 30 min)
- **Max concurrent sessions**: Runner rejects `start_session` runs above limit

## Component Map

### Executor-Side (Phase 1 — implemented)

| File | Component | Responsibility |
|------|-----------|----------------|
| `ao-claude-code-exec` | Entry point | Read first stdin line, route to `run_multi_turn()` |
| `lib/executor.py` | `run_multi_turn()` | Load config, delegate to `run_multi_turn_session_sync()` |
| `lib/sdk_client.py` | `run_multi_turn_session()` | Core multi-turn loop: SDK client, turn processing, stdin/stdout protocol |
| `lib/sdk_client.py` | `_read_stdin_line()` | Async stdin reading via `run_in_executor` |
| `lib/session_events.py` | `SessionEventEmitter` | HTTP event emission (unchanged) |
| `lib/executor_config.py` | `load_config()` | Config resolution (unchanged) |

### Runner-Side (Phase 2 — not yet implemented)

| File | Component | Change Needed |
|------|-----------|---------------|
| `lib/registry.py` | `RunningRunsRegistry` | Add `session_id → process` index |
| `lib/executor.py` | `_execute_with_payload()` | Keep stdin open (don't close after first write) |
| `lib/poller.py` | `_handle_run()` | Route `resume_session` to existing process |
| `lib/supervisor.py` | Process monitoring | Add stdout reader thread for `turn_complete` |

## What Is Preserved (No Changes from Pre-Multi-Turn)

- Session ID scheme and format
- Agent Run concept (one run = one turn)
- Run lifecycle (PENDING → CLAIMED → RUNNING → COMPLETED)
- Blueprint resolution (coordinator resolves before dispatch)
- Session binding (first turn, via Gateway HTTP)
- Session event emission (via Gateway HTTP)
- Affinity-based routing (hostname + executor_profile)
- Long-poll dispatch (coordinator → runner)
- Callback processor (async parent/child orchestration)
- Stop command handling (SIGTERM kills session)
- Hook execution on coordinator side
- Runner registration and heartbeat
- Agent Coordinator (zero changes across all phases)
