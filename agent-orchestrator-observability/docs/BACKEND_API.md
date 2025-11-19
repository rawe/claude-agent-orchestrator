# Backend API

API for writing and updating data in the observability backend.

**Used by:**
- Hook scripts (session_start, pre_tool, post_tool, stop, user_prompt_submit)
- Python CLI commands (for updating session metadata)
- External clients that need to send events or update sessions

**For reading data** (used by the frontend UI), see [FRONTEND_API.md](FRONTEND_API.md).

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

### UserPromptSubmit Hook
**File:** `hooks/user_prompt_submit_hook.py`
**Trigger:** When the user submits a prompt to Claude
**Data Captured:**
- `session_id` - Session identifier
- `prompt` - The user's input text

**Event Sent:**
Sends a `message` event with `role: "user"` and the prompt as text content.

### Stop Hook
**File:** `hooks/stop_hook.py`
**Trigger:** When a Claude Code agent session stops
**Data Captured:**
- `session_id` - Session identifier
- `exit_code` - Exit code (0 for success)
- `reason` - Reason for stopping (e.g., "completed")

**Additional Processing:**
This hook also reads the session transcript file and extracts the last message to send as a separate `message` event with `role: "assistant"` (see Message Events below).

---

## Message Events

Message events capture the conversation between the user and the assistant.

**Sources:**
1. **User messages** - Sent directly by `hooks/user_prompt_submit_hook.py` when user submits a prompt
2. **Assistant messages** - Extracted from session transcript by `hooks/stop_hook.py` when session ends

**Data Structure:**
- `session_id` - Session identifier
- `role` - Message author (`user` or `assistant`)
- `content` - Array of content blocks (see [Message Content Block](DATA_MODELS.md#message-content-block))

**Event Structure:**
See [Message Event](DATA_MODELS.md#message-event) in DATA_MODELS.md

---

## Endpoints

### POST /events

Send events to the observability backend.

**URL:** `http://127.0.0.1:8765/events`
**Method:** `POST`
**Content-Type:** `application/json`

**Request Body:**

See [Event model](DATA_MODELS.md#event) in DATA_MODELS.md

**Response:**

**Success:**
```json
{
  "ok": true
}
```
**Status Code:** `200 OK`

---

### PATCH /sessions/{session_id}/metadata

Update session metadata (name and/or project directory).

**URL:** `http://127.0.0.1:8765/sessions/{session_id}/metadata`
**Method:** `PATCH`
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "session_name": "New Session Name",  // optional
  "project_dir": "/path/to/project"    // optional
}
```

Both fields are optional - include only the fields you want to update.

**Response:**

**Success:**
```json
{
  "ok": true,
  "session": {
    "session_id": "abc-123",
    "session_name": "New Session Name",
    "status": "running",
    "created_at": "2025-11-19T10:00:00Z",
    "project_dir": "/path/to/project"
  }
}
```
**Status Code:** `200 OK`

**Error (Session Not Found):**
```json
{
  "detail": "Session not found"
}
```
**Status Code:** `404 Not Found`

**Notes:**
- Updates are broadcast to all connected WebSocket clients via `session_updated` message (see [FRONTEND_API.md](FRONTEND_API.md))
- At least one field must be provided
- `project_dir` is typically an absolute path to the project directory

---

## Configuration

**Environment Variable:**
```bash
OBSERVABILITY_BACKEND_URL="http://127.0.0.1:8765/events"
```

Default: `http://127.0.0.1:8765/events` (used if not set)

## Error Handling

Hooks fail gracefully - if backend is unreachable, they log a warning but don't block agent execution.
