# Hooks → Backend API

Interface between hook scripts and the observability backend.

## Available Hooks

### SessionStart Hook
**File:** `hooks/session_start_hook.py`
**Trigger:** When a Claude Code agent session starts
**Data Captured:**
- `session_id` - Unique session identifier
- `session_name` - Name of the session
- `timestamp` - When the session started

### PreToolUse Hook
**File:** `hooks/pre_tool_hook.py`
**Trigger:** Before a tool is executed
**Data Captured:**
- `session_id` - Session identifier
- `tool_name` - Name of the tool (e.g., "Read", "Write", "Bash")
- `tool_input` - Input parameters passed to the tool

### PostToolUse Hook
**File:** `hooks/post_tool_hook.py`
**Trigger:** After a tool execution completes
**Data Captured:**
- `session_id` - Session identifier
- `tool_name` - Name of the tool
- `tool_input` - Original input parameters
- `tool_output` - Result returned by the tool
- `error` - Error message if execution failed (null otherwise)

### Stop Hook
**File:** `hooks/stop_hook.py`
**Trigger:** When a Claude Code agent session stops
**Data Captured:**
- `session_id` - Session identifier
- `exit_code` - Exit code (0 for success)
- `reason` - Reason for stopping (e.g., "completed")

**Additional Processing:**
This hook also reads the session transcript file and extracts the last message to send as a separate `message` event (see Message Events below).

---

## Message Events

**Note:** Message events are **not triggered by a hook directly**. They are extracted from the session transcript by the Stop hook.

**Source:** Session transcript JSONL file (last line)
**Sent by:** `hooks/stop_hook.py` (after sending `session_stop` event)
**Data Captured:**
- `session_id` - Session identifier
- `role` - Message author (`assistant` or `user`)
- `content` - Array of content blocks (see [Message Content Block](DATA_MODELS.md#message-content-block))

**Event Structure:**
See [Message Event](DATA_MODELS.md#message-event) in DATA_MODELS.md

---

## Endpoint

**URL:** `http://127.0.0.1:8765/events`
**Method:** `POST`
**Content-Type:** `application/json`

## Request Body

See [Event model](DATA_MODELS.md#event) in DATA_MODELS.md

## Response

**Success:**
```json
{
  "ok": true
}
```
**Status Code:** `200 OK`

## Configuration

**Environment Variable:**
```bash
OBSERVABILITY_BACKEND_URL="http://127.0.0.1:8765/events"
```

Default: `http://127.0.0.1:8765/events` (used if not set)

## Error Handling

Hooks fail gracefully - if backend is unreachable, they log a warning but don't block agent execution.
