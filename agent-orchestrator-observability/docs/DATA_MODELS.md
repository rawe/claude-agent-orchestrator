# Shared Data Models

Common data structures used across the observability system.

## Event

```json
{
  "event_type": "session_start | pre_tool | post_tool | session_stop | message",
  "session_id": "string",
  "session_name": "string",
  "timestamp": "ISO 8601 string",
  "tool_name": "string (optional)",
  "tool_input": {} // optional object
  "tool_output": "any (optional)",
  "error": "string (optional)",
  "exit_code": "number (optional)",
  "reason": "string (optional)",
  "role": "string (optional)",  // 'assistant' | 'user'
  "content": [] // optional array of content blocks
}
```

### Event Types

- `session_start` - Agent session started
- `pre_tool` - Tool about to be executed
- `post_tool` - Tool execution completed
- `session_stop` - Agent session stopped
- `message` - Agent or user message

### Message Content Block

```json
{
  "type": "text",  // Only 'text' supported for now
  "text": "string"
}
```

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

### PostToolUse Event
```json
{
  "event_type": "post_tool",
  "session_id": "abc-123-def",
  "session_name": "my-agent",
  "timestamp": "2025-11-16T10:30:16.000000Z",
  "tool_name": "Read",
  "tool_input": {
    "file_path": "/path/to/file.py"
  },
  "tool_output": "file contents here...",
  "error": null
}
```

### SessionStop Event
```json
{
  "event_type": "session_stop",
  "session_id": "abc-123-def",
  "session_name": "my-agent",
  "timestamp": "2025-11-16T10:35:00.000000Z",
  "exit_code": 0,
  "reason": "completed"
}
```

### Message Event
```json
{
  "event_type": "message",
  "session_id": "abc-123-def",
  "session_name": "my-agent",
  "timestamp": "2025-11-16T10:34:55.000000Z",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "I've completed the task successfully."
    }
  ]
}
```
