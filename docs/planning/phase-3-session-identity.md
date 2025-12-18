# Phase 3: Session Identity (ADR-010)

## Overview

Replace `session_name` with coordinator-generated `session_id` as primary identifier. Add `executor_session_id` for framework binding and session affinity tracking.

## Components Affected

### Agent Coordinator (`servers/agent-coordinator/`)

| File | Changes |
|------|---------|
| `database.py` | Add `executor_session_id`, `executor_type`, `hostname` columns; remove `session_name` |
| `models.py` | Remove `session_name`; add `executor_session_id`; change `parent_session_name` to `parent_session_id` |
| `main.py` | Generate `session_id` at run creation; add `POST /sessions/{session_id}/bind`; remove `/sessions/by-name/` |
| `services/run_queue.py` | Change `session_name` to `session_id` in `Run`; return `session_id` in response |
| `services/callback_processor.py` | Change `parent_session_name` to `parent_session_id` |

### Agent Runner (`servers/agent-runner/`)

| File | Changes |
|------|---------|
| `lib/invocation.py` | Replace `session_name` with `session_id` in schema |
| `lib/executor.py` | Pass `session_id` to executor; update env var |
| `lib/session_client.py` | Add `bind_session()` method |
| `executors/claude-code/lib/claude_client.py` | Call bind endpoint; post events using `session_id` |

### MCP Server (`mcps/agent-orchestrator/`)

| File | Changes |
|------|---------|
| `libs/api_client.py` | Update to use `session_id` |
| `libs/types_models.py` | Update SessionInfo; change parent reference |
| `libs/core_functions.py` | Change all `session_name` to `session_id` |
| `libs/schemas.py` | Update tool schemas |

### Plugins (`plugins/orchestrator/`)

| File | Changes |
|------|---------|
| `skills/orchestrator/commands/lib/run_client.py` | Use `session_id` |
| `skills/orchestrator/commands/lib/session_client.py` | Use `session_id` |

### Dashboard (`dashboard/src/`)

| File | Changes |
|------|---------|
| `types/session.ts` | Update types |
| `services/sessionService.ts` | Update API calls |
| `services/chatService.ts` | Use returned `session_id` |

## Implementation Order

1. **Database schema**
   - Add new columns (`executor_session_id`, `executor_type`, `hostname`)

2. **Coordinator: session_id generation**
   - Generate `session_id` at run creation in `run_queue.py`
   - Return `session_id` in POST /runs response
   - Create session record with status=pending

3. **Coordinator: bind endpoint**
   - Add `POST /sessions/{session_id}/bind`
   - Accept `executor_session_id`, `hostname`, `executor_type`

4. **Runner/Executor: use session_id**
   - Update invocation schema
   - Pass `session_id` to executor
   - Executor calls bind endpoint
   - Post events using `session_id`

5. **Remove session_name from API**
   - Remove from models
   - Remove `/sessions/by-name/` endpoint
   - Change `parent_session_name` to `parent_session_id`

6. **Update clients**
   - MCP server, plugins

7. **Update dashboard**
   - Types, services, components

8. **Cleanup**
   - Remove `session_name` column

## Dependencies

- **Phase 1**: Runner properties available for session affinity
- **Phase 2**: Demand matching for resume affinity routing

## Verification

1. Run creation returns `session_id` immediately
2. Bind endpoint stores executor binding
3. Resume uses `session_id` and affinity matching
4. Parent/child uses `session_id`
5. No `session_name` references in codebase
