# Shared Data Models

Common data structures used by the Agent Coordinator.

## Event

```json
{
  "event_type": "session_start | pre_tool | post_tool | session_stop | message",
  "session_id": "string",
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
  "status": "pending | running | stopping | stopped | finished",
  "created_at": "ISO 8601 string",
  "project_dir": "string (optional)",
  "agent_name": "string (optional)",
  "last_resumed_at": "ISO 8601 string (optional)",
  "parent_session_id": "string (optional)",
  "execution_mode": "sync | async_poll | async_callback",
  "executor_session_id": "string (optional)",
  "executor_type": "string (optional)",
  "hostname": "string (optional)"
}
```

**Fields:**
- `session_id` - Coordinator-generated unique identifier (format: `ses_{12-char-hex}`)
- `status` - Current session state (see status values below)
- `created_at` - ISO 8601 timestamp when session was created
- `project_dir` - Optional absolute path to the project directory
- `agent_name` - Optional name of the agent blueprint that created this session
- `last_resumed_at` - Optional timestamp when session was last resumed
- `parent_session_id` - Optional ID of the parent session (for hierarchy tracking)
- `execution_mode` - How parent-child sessions interact (default: `sync`)
- `executor_session_id` - Framework's session ID (e.g., Claude SDK UUID)
- `executor_type` - Type of executor running this session (e.g., `claude-code`)
- `hostname` - Machine hostname where session is running

**Session Status Values:**
- `pending` - Session created but execution not yet started
- `running` - Session is actively executing
- `stopping` - Stop requested, waiting for termination
- `stopped` - Session was terminated by stop command
- `finished` - Session completed normally

**Execution Modes:**
- `sync` - Parent waits for child completion, receives result directly
- `async_poll` - Parent continues immediately, polls for child status/result
- `async_callback` - Parent continues immediately, coordinator auto-resumes parent when child completes

## Run

```json
{
  "run_id": "string",
  "type": "start_session | resume_session",
  "session_id": "string",
  "agent_name": "string (optional)",
  "prompt": "string",
  "project_dir": "string (optional)",
  "parent_session_id": "string (optional)",
  "execution_mode": "sync | async_poll | async_callback",
  "demands": {
    "hostname": "string (optional)",
    "project_dir": "string (optional)",
    "executor_type": "string (optional)",
    "tags": ["string"]
  },
  "status": "pending | claimed | running | stopping | completed | failed | stopped",
  "runner_id": "string (optional)",
  "error": "string (optional)",
  "created_at": "ISO 8601 string",
  "claimed_at": "ISO 8601 string (optional)",
  "started_at": "ISO 8601 string (optional)",
  "completed_at": "ISO 8601 string (optional)",
  "timeout_at": "ISO 8601 string (optional)"
}
```

**Fields:**
- `run_id` - Unique identifier for the run (format: `run_{12-char-hex}`)
- `type` - Run type: `start_session` or `resume_session`
- `session_id` - Coordinator-generated session ID (format: `ses_{12-char-hex}`)
- `agent_name` - Optional name of the agent blueprint to use
- `prompt` - User prompt/instruction for the agent
- `project_dir` - Optional project directory path
- `parent_session_id` - Optional parent session ID (for hierarchy tracking)
- `execution_mode` - How parent-child sessions interact (default: `sync`)
- `demands` - Runner demands for capability matching (see below)
- `status` - Current run status
- `runner_id` - ID of the runner that claimed/executed the run
- `error` - Error message if run failed
- `created_at` - Timestamp when run was created
- `claimed_at` - Timestamp when runner claimed the run
- `started_at` - Timestamp when run execution started
- `completed_at` - Timestamp when run completed or failed
- `timeout_at` - Timestamp when run will fail if no matching runner found

**Run Status Values:**
- `pending` - Run created, waiting for runner
- `claimed` - Runner claimed the run
- `running` - Run execution started
- `stopping` - Stop requested, waiting for runner to terminate process
- `completed` - Run completed successfully
- `failed` - Run execution failed (or no matching runner within timeout)
- `stopped` - Run was stopped (terminated by stop command)

## Runner Demands

Requirements that runs demand from runners for capability matching.

```json
{
  "hostname": "string (optional)",
  "project_dir": "string (optional)",
  "executor_type": "string (optional)",
  "tags": ["string"]
}
```

**Fields:**
- `hostname` - Property demand: runner must be on this host (exact match)
- `project_dir` - Property demand: runner must be in this directory (exact match)
- `executor_type` - Property demand: runner must use this executor (exact match)
- `tags` - Capability demands: runner must have ALL specified tags

**Notes:**
- Property demands require exact match if specified
- Tag demands are cumulative (runner must have ALL tags)
- Runs with demands have a 5-minute timeout for matching
- Demands from agent blueprints are merged with `additional_demands` from run creation

## Runner

```json
{
  "runner_id": "string",
  "registered_at": "ISO 8601 string",
  "last_heartbeat": "ISO 8601 string",
  "hostname": "string",
  "project_dir": "string",
  "executor_type": "string",
  "tags": ["string"]
}
```

**Fields:**
- `runner_id` - Deterministic identifier derived from (hostname, project_dir, executor_type) (format: `lnch_{12-char-hex}`)
- `registered_at` - Timestamp when runner registered
- `last_heartbeat` - Timestamp of the most recent heartbeat
- `hostname` - Machine hostname where runner is running
- `project_dir` - Default project directory for this runner
- `executor_type` - Executor type (e.g., `claude-code`)
- `tags` - Capability tags for demand matching

**Note:** When fetching runners via GET /runners, additional computed fields are included:
- `status` - Computed status: `online` or `stale`
- `seconds_since_heartbeat` - Seconds since last heartbeat

**Runner Identity:**
- `runner_id` is deterministically computed from (hostname, project_dir, executor_type)
- This enables automatic reconnection recognition after crashes
- Prevents duplicate runner registration (returns 409 Conflict)

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
  "tags": ["string"],
  "demands": {
    "hostname": "string (optional)",
    "project_dir": "string (optional)",
    "executor_type": "string (optional)",
    "tags": ["string"]
  },
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
- `tags` - Optional list of categorization tags for filtering agents
- `demands` - Optional blueprint demands for runner matching (merged with run demands)
- `status` - Agent status: `active` or `inactive`
- `created_at` - Timestamp when agent was created
- `modified_at` - Timestamp when agent was last modified

**Blueprint Demands:**
When a run is created using an agent with `demands`, those demands are merged with any `additional_demands` specified in the run creation request. This allows agents to require specific runner capabilities (e.g., an agent that needs web access can demand runners with the `web-access` tag).

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
  "session_id": "ses_abc123def456",
  "timestamp": "2025-11-16T10:30:00.000000Z"
}
```

### PreToolUse Event
```json
{
  "event_type": "pre_tool",
  "session_id": "ses_abc123def456",
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
  "session_id": "ses_abc123def456",
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
  "session_id": "ses_abc123def456",
  "timestamp": "2025-11-16T10:35:00.000000Z",
  "exit_code": 0,
  "reason": "completed"
}
```

### Message Event (User)
```json
{
  "event_type": "message",
  "session_id": "ses_abc123def456",
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
  "session_id": "ses_abc123def456",
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
