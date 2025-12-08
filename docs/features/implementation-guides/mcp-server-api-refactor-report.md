# MCP Server API Refactor - Implementation Report

## Status Overview

| Phase | Name | Status |
|-------|------|--------|
| 1 | Add Parent Session Field to Jobs API | DONE |
| 2 | Link Jobs to Sessions | DONE |
| 3 | Simplify ao-start/ao-resume | DONE |
| 4 | Refactor MCP Server | DONE |
| 5 | Remove Unused Code | DONE |

---

## Phase 1: Add Parent Session Field to Jobs API - DONE

**Date:** 2025-12-08

**Files modified:**
- `servers/agent-runtime/services/job_queue.py`

**Changes:**
1. Added `parent_session_name: Optional[str] = None` to `JobCreate` model
2. Added `parent_session_name: Optional[str] = None` to `Job` model
3. Updated `add_job()` to copy `parent_session_name` from request to job

**Verification:**
- [x] `POST /jobs` accepts `parent_session_name`
- [x] `GET /jobs/{job_id}` returns `parent_session_name`
- [x] Python syntax check passed

---

## Phase 2: Link Jobs to Sessions - DONE

**Date:** 2025-12-08

**Files modified:**
- `servers/agent-runtime/services/job_queue.py`
- `servers/agent-runtime/database.py`
- `servers/agent-runtime/main.py`
- `servers/agent-launcher/lib/executor.py`

**Changes:**

1. **job_queue.py**: Added `get_job_by_session_name()` helper
   - Finds running/claimed job by session_name
   - Used by `POST /sessions` to inherit parent from job

2. **database.py**: Added `update_session_parent()` helper
   - Updates `parent_session_name` for existing sessions
   - Used for resume case where parent may differ

3. **main.py**: Updated `POST /launcher/jobs/{job_id}/started`
   - Gets job's `parent_session_name` when job starts
   - Updates existing session's parent (resume case)

4. **main.py**: Updated `POST /sessions`
   - Looks up running job by `session_name`
   - Inherits `parent_session_name` from job (start case)

5. **executor.py**: Set `AGENT_SESSION_NAME` in subprocess environment
   - Agent Launcher now sets `AGENT_SESSION_NAME={session_name}` when spawning ao-start/ao-resume
   - This enables sessions to identify themselves for MCP HTTP callback flow
   - Flow: Launcher → env var → ao-start → MCP config placeholder → HTTP header

**Verification:**
- [x] `get_job_by_session_name()` finds claimed/running jobs
- [x] `update_session_parent()` updates session parent
- [x] New session gets `parent_session_name` from job automatically
- [x] Resumed session updates `parent_session_name` from job
- [x] ao-start/ao-resume receive `AGENT_SESSION_NAME` in environment
- [x] Python syntax check passed

---

## Phase 3: Simplify ao-start/ao-resume - DONE

**Date:** 2025-12-08

**Files modified:**
- `servers/agent-launcher/claude-code/ao-start`
- `servers/agent-launcher/claude-code/lib/claude_client.py`
- `servers/agent-launcher/claude-code/lib/session_client.py`

**Changes:**

1. **ao-start**: Removed `parent_session_name` handling
   - Removed reading `AGENT_SESSION_NAME` env var (line 119)
   - Removed passing `parent_session_name` to `run_session_sync()` (line 129)
   - Removed unused `os` import
   - Added comment explaining that parent session is now handled by Agent Runtime

2. **claude_client.py**: Removed `parent_session_name` parameter
   - Removed from `run_claude_session()` function signature and docstring
   - Removed from `run_session_sync()` wrapper function
   - Removed from `create_session()` call inside `run_claude_session()`
   - Added docstring notes explaining the new flow via Jobs API

3. **session_client.py**: Removed `parent_session_name` parameter
   - Removed from `create_session()` method
   - Added docstring note explaining the new flow

**Note:** ao-resume was already not passing `parent_session_name`, so no changes were needed there.

**Verification:**
- [x] ao-start no longer reads `AGENT_SESSION_NAME` env var
- [x] claude_client.py functions no longer accept `parent_session_name`
- [x] session_client.py `create_session()` no longer accepts `parent_session_name`
- [x] Python syntax check passed for all files

---

## Phase 4: Refactor MCP Server - DONE

**Date:** 2025-12-08

**Files created:**
- `interfaces/agent-orchestrator-mcp-server/libs/api_client.py`

**Files modified:**
- `interfaces/agent-orchestrator-mcp-server/agent-orchestrator-mcp.py`
- `interfaces/agent-orchestrator-mcp-server/libs/constants.py`
- `interfaces/agent-orchestrator-mcp-server/libs/types_models.py`
- `interfaces/agent-orchestrator-mcp-server/libs/core_functions.py`
- `interfaces/agent-orchestrator-mcp-server/libs/server.py`

**Changes:**

1. **agent-orchestrator-mcp.py**: Updated entry point
   - Added `httpx>=0.28.0` to UV inline dependencies
   - Updated docstring to reflect new API-based architecture
   - Removed `AGENT_ORCHESTRATOR_COMMAND_PATH` auto-discovery (no longer needed)
   - Updated environment variables documentation

2. **api_client.py**: Created new async HTTP client
   - Uses `httpx` for async HTTP requests to Agent Runtime API
   - Implements Jobs API: `create_job()`, `get_job()`, `wait_for_job()`
   - Implements Sessions API: `get_session_by_name()`, `list_sessions()`, `get_session_status()`, `get_session_result()`, `delete_session()`
   - Implements Agents API: `list_agents()`, `get_agent()`
   - Custom `APIError` exception with status code support

3. **constants.py**: Replaced command constants with API config
   - Removed all `CMD_*` constants and `ENV_COMMAND_PATH`
   - Added `ENV_API_URL`, `DEFAULT_API_URL`, `get_api_url()` function
   - Added `HEADER_AGENT_SESSION_NAME` for HTTP mode callback support
   - Added `ENV_AGENT_SESSION_NAME` for stdio mode callback support

4. **types_models.py**: Updated models for API-based architecture
   - Removed `ScriptExecutionResult`, `AsyncExecutionResult` (no longer needed)
   - Updated `SessionInfo` with new fields: `session_id`, `session_name`, `status`, `parent_session_name`
   - Updated `AgentInfo` with `status` field
   - Changed `ServerConfig` from `commandPath` to `api_url`

5. **core_functions.py**: Complete rewrite to use API client
   - Removed all subprocess execution code
   - All functions now use `APIClient` to call Agent Runtime API
   - `start_agent_session_impl()`: Creates job via `POST /jobs`, waits for completion
   - `resume_agent_session_impl()`: Creates resume job via `POST /jobs`
   - `list_agent_blueprints_impl()`: Calls `GET /agents`
   - `list_agent_sessions_impl()`: Calls `GET /sessions`
   - `get_agent_session_status_impl()`: Calls `GET /sessions/by-name/{name}` then `GET /sessions/{id}/status`
   - `get_agent_session_result_impl()`: Calls `GET /sessions/{id}/result`
   - `delete_all_agent_sessions_impl()`: Lists sessions and deletes each
   - Added `get_parent_session_name()` helper for callback support (reads from env or HTTP headers)

6. **server.py**: Updated configuration
   - Removed `ENV_COMMAND_PATH` import
   - Added `get_api_url` import
   - `get_server_config()` now returns `ServerConfig(api_url=get_api_url())`
   - Startup logging shows `api_url` instead of `commandPath`

**Architecture Change:**

Before (subprocess-based):
```
MCP Server → subprocess.Popen → ao-start/ao-resume → Claude Agent SDK → Agent Runtime API
```

After (API-based):
```
MCP Server → httpx → Agent Runtime API (Jobs API) → Agent Launcher → ao-start/ao-resume
```

**Verification:**
- [x] All Python files pass syntax check (`python -m py_compile`)
- [x] `httpx` dependency added to UV inline script
- [x] `api_client.py` implements all required API endpoints
- [x] `core_functions.py` uses async API client instead of subprocess
- [x] `server.py` uses `api_url` configuration
- [x] Entry point no longer requires `AGENT_ORCHESTRATOR_COMMAND_PATH`

---

## Phase 5: Remove Unused Code - DONE

**Date:** 2025-12-08

**Files deleted:**
- `interfaces/agent-orchestrator-mcp-server/libs/utils.py`

**Changes:**

1. **utils.py**: Deleted entirely
   - Contained unused subprocess-based code: `execute_script()`, `execute_script_async()`
   - Contained unused command mapping: `COMMAND_NAME_MAP`
   - Contained unused parsing functions: `parse_agent_list()`, `parse_session_list()`
   - Contained unused formatting functions: `format_agents_as_*()`, `format_sessions_as_*()`
   - All functionality was replaced by `api_client.py` and inline code in `core_functions.py`

**Note:** `constants.py` was already cleaned up in Phase 4 (CMD_* constants and ENV_COMMAND_PATH removed).

**Verification:**
- [x] `utils.py` deleted
- [x] No remaining imports of `utils` in codebase
- [x] All Python files pass syntax check (`python -m py_compile`)

---

## Implementation Complete

All 5 phases of the MCP Server API refactor have been completed. The MCP server now:
- Uses HTTP API calls to Agent Runtime instead of subprocess execution
- Passes `parent_session_name` through the Jobs API for callback support
- Has no dependency on `AGENT_ORCHESTRATOR_COMMAND_PATH` environment variable
- Only requires `AGENT_ORCHESTRATOR_API_URL` (defaults to `http://127.0.0.1:8765`)
