# MCP Server API Refactor - Bug Collection

Bugs discovered during testing of the MCP Server API refactor.

---

## Bug 1: REST API `/api/sessions` KeyError on `name` - FIXED ✅

**File:** `interfaces/agent-orchestrator-mcp-server/libs/rest_api.py`

**Line:** 168

**Error:**
```
KeyError: 'name'
```

**Cause:**
The `list_agent_sessions_impl()` function returns sessions from the Agent Runtime API with field `session_name`, but `rest_api.py` tries to access `s["name"]`.

**Fix Applied (2025-12-08):**
Changed line 168 from:
```python
name=s["name"],
```
to:
```python
name=s["session_name"],
```

**Status:** Fixed and verified working.

---

## Bug 2: REST API missing `callback` parameter - OPEN

**File:** `interfaces/agent-orchestrator-mcp-server/libs/rest_api.py`

**Issue:**
The `StartSessionRequest` and `ResumeSessionRequest` models don't include the `callback` parameter, so the REST API can't be used to enable callback mode.

**Current State:**
The MCP tool has `callback: bool = Field(...)` but the REST API doesn't expose it.

**Fix Required:**
1. Add `callback: bool = Field(default=False, ...)` to `StartSessionRequest` and `ResumeSessionRequest`
2. Pass `callback=request.callback` in `start_session()` and `resume_session()` endpoint functions
3. Pass HTTP headers to `start_agent_session_impl()` and `resume_agent_session_impl()`

**Severity:** Low - MCP tools work correctly with callback, only REST API affected.

---
