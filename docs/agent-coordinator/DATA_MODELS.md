# Shared Data Models

Common data structures used by the Agent Coordinator.

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
  "created_at": "ISO 8601 string",
  "project_dir": "string (optional)",
  "agent_name": "string (optional)",
  "last_resumed_at": "ISO 8601 string (optional)",
  "parent_session_name": "string (optional)"
}
```

**Fields:**
- `session_id` - Unique identifier for the session
- `session_name` - Display name for the session
- `status` - Current session state (`running` or `finished`)
- `created_at` - ISO 8601 timestamp when session was created
- `project_dir` - Optional absolute path to the project directory (e.g., `/Users/name/projects/my-app`)
- `agent_name` - Optional name of the agent blueprint that created this session
- `last_resumed_at` - Optional timestamp when session was last resumed
- `parent_session_name` - Optional name of the parent session (for callback support)

## Run

```json
{
  "run_id": "string",
  "type": "start_session | resume_session",
  "session_name": "string",
  "agent_name": "string (optional)",
  "prompt": "string",
  "project_dir": "string (optional)",
  "parent_session_name": "string (optional)",
  "status": "pending | claimed | running | stopping | completed | failed | stopped",
  "runner_id": "string (optional)",
  "error": "string (optional)",
  "created_at": "ISO 8601 string",
  "claimed_at": "ISO 8601 string (optional)",
  "started_at": "ISO 8601 string (optional)",
  "completed_at": "ISO 8601 string (optional)"
}
```

**Fields:**
- `run_id` - Unique identifier for the run (e.g., `run_abc123`)
- `type` - Run type: `start_session` or `resume_session`
- `session_name` - Name of the session to start/resume
- `agent_name` - Optional name of the agent blueprint to use
- `prompt` - User prompt/instruction for the agent
- `project_dir` - Optional project directory path
- `parent_session_name` - Optional parent session name (for callbacks)
- `status` - Current run status
- `runner_id` - ID of the runner that claimed/executed the run
- `error` - Error message if run failed
- `created_at` - Timestamp when run was created
- `claimed_at` - Timestamp when runner claimed the run
- `started_at` - Timestamp when run execution started
- `completed_at` - Timestamp when run completed or failed

**Run Status Values:**
- `pending` - Run created, waiting for runner
- `claimed` - Runner claimed the run
- `running` - Run execution started
- `stopping` - Stop requested, waiting for runner to terminate process
- `completed` - Run completed successfully
- `failed` - Run execution failed
- `stopped` - Run was stopped (terminated by stop command)

## Runner

```json
{
  "runner_id": "string",
  "registered_at": "ISO 8601 string",
  "last_heartbeat": "ISO 8601 string",
  "hostname": "string (optional)",
  "project_dir": "string (optional)",
  "executor_type": "string (optional)"
}
```

**Fields:**
- `runner_id` - Unique identifier for the runner (e.g., `lnch_abc123`)
- `registered_at` - Timestamp when runner registered
- `last_heartbeat` - Timestamp of the most recent heartbeat
- `hostname` - Optional machine hostname where runner is running
- `project_dir` - Optional default project directory for this runner
- `executor_type` - Optional executor type (folder name, e.g., `claude-code`, `test-executor`)

**Note:** When fetching runners via GET /runners, additional computed fields are included:
- `status` - Computed status: `online`, `stale`, or `offline`
- `seconds_since_heartbeat` - Seconds since last heartbeat

## Agent

Agent blueprints (templates for creating agents with specific configurations).

```json
{
  "name": "string",
  "description": "string",
  "system_prompt": "string (optional)",
  "mcp_servers": {
    "server-name": {
      "type": "stdio | http",
      "command": "string",
      "args": ["string"],
      "env": { "KEY": "value" },
      "url": "string",
      "headers": { "KEY": "value" }
    }
  },
  "skills": ["string"],
  "status": "active | inactive",
  "created_at": "ISO 8601 string",
  "modified_at": "ISO 8601 string"
}
```

**Fields:**
- `name` - Unique identifier/name for the agent blueprint
- `description` - Human-readable description of the agent's purpose
- `system_prompt` - Optional custom system prompt for the agent
- `mcp_servers` - Optional MCP server configurations (see below)
- `skills` - Optional list of skill tags (e.g., `["research", "coding"]`)
- `status` - Agent status: `active` or `inactive`
- `created_at` - Timestamp when agent was created
- `modified_at` - Timestamp when agent was last modified

**MCP Server Config (stdio):**
```json
{
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-brave-search"],
  "env": { "BRAVE_API_KEY": "..." }
}
```

**MCP Server Config (http):**
```json
{
  "type": "http",
  "url": "https://api.example.com",
  "headers": { "Authorization": "Bearer ..." }
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

### Message Event (User)
```json
{
  "event_type": "message",
  "session_id": "abc-123-def",
  "session_name": "my-agent",
  "timestamp": "2025-11-16T10:34:50.000000Z",
  "role": "user",
  "content": [
    {
      "type": "text",
      "text": "calculate 1+1"
    }
  ]
}
```

### Message Event (Assistant)
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
