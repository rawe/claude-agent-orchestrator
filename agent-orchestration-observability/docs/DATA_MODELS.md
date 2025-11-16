# Shared Data Models

Common data structures used across the observability system.

## Event

```json
{
  "event_type": "session_start | pre_tool",
  "session_id": "string",
  "session_name": "string",
  "timestamp": "ISO 8601 string",
  "tool_name": "string (optional)",
  "tool_input": {} // optional object
}
```

### Event Types

- `session_start` - Agent session started
- `pre_tool` - Tool about to be executed

## Session

```json
{
  "session_id": "string",
  "session_name": "string",
  "status": "running | finished",
  "created_at": "ISO 8601 string"
}
```

## Examples

### SessionStart Event
```json
{
  "event_type": "session_start",
  "session_id": "abc-123-def",
  "session_name": "my-agent",
  "timestamp": "2025-11-16T10:30:00.000000Z"
}
```

### PreToolUse Event
```json
{
  "event_type": "pre_tool",
  "session_id": "abc-123-def",
  "session_name": "my-agent",
  "timestamp": "2025-11-16T10:30:15.000000Z",
  "tool_name": "Read",
  "tool_input": {
    "file_path": "/path/to/file.py"
  }
}
```
