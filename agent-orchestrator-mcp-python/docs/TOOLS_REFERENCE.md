# Tools Reference

Detailed API documentation for all MCP tools provided by the Agent Orchestrator server.

## Overview

The Agent Orchestrator MCP Server provides 7 tools for managing orchestrated agent sessions:

1. **list_agents** - Discover available specialized agent definitions
2. **list_sessions** - View all agent sessions with their IDs and project directories
3. **start_agent** - Create new agent sessions with optional specialization (supports async execution)
4. **resume_agent** - Continue work in existing sessions (supports async execution)
5. **clean_sessions** - Remove all sessions
6. **get_agent_status** - Check the status of a running or completed session
7. **get_agent_result** - Retrieve the result from a completed session

All tools support optional `project_dir` override for managing multiple projects.

---

## 1. list_agents

Lists all available specialized agent definitions.

### Parameters

- `project_dir` (optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!
- `response_format` (optional): `"markdown"` or `"json"` (default: `"markdown"`)

### Example

```python
{
  "response_format": "json"
}
```

### Example with project_dir override

```python
{
  "project_dir": "/absolute/path/to/project",
  "response_format": "json"
}
```

### Response (JSON format)

```json
{
  "total": 3,
  "agents": [
    {
      "name": "system-architect",
      "description": "Expert in designing scalable system architectures"
    },
    {
      "name": "code-reviewer",
      "description": "Reviews code for best practices and improvements"
    },
    {
      "name": "documentation-writer",
      "description": "Creates comprehensive technical documentation"
    }
  ]
}
```

---

## 2. list_sessions

Lists all existing agent sessions with their session IDs and project directories.

### Parameters

- `project_dir` (optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!
- `response_format` (optional): `"markdown"` or `"json"` (default: `"markdown"`)

### Example

```python
{
  "response_format": "json"
}
```

### Example with project_dir override

```python
{
  "project_dir": "/absolute/path/to/project",
  "response_format": "json"
}
```

### Response (JSON format)

```json
{
  "total": 2,
  "sessions": [
    {
      "name": "architect",
      "session_id": "3db5dca9-6829-4cb7-a645-c64dbd98244d",
      "project_dir": "/Users/ramon/my-project"
    },
    {
      "name": "reviewer",
      "session_id": "initializing",
      "project_dir": "/Users/ramon/another-project"
    }
  ]
}
```

---

## 3. start_agent

Creates a new orchestrated agent session.

### Parameters

- `session_name` (required): Unique session name (alphanumeric, dash, underscore; max 60 chars)
- `agent_name` (optional): Name of agent definition to use
- `project_dir` (optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!
- `prompt` (required): Initial task description
- `async` (optional): Run in background (default: `false`). When `true`, returns immediately and use `get_agent_status` / `get_agent_result` to check progress

### Example (synchronous)

```python
{
  "session_name": "architect",
  "agent_name": "system-architect",
  "prompt": "Design a microservices architecture for an e-commerce platform"
}
```

### Example (asynchronous)

```python
{
  "session_name": "architect",
  "agent_name": "system-architect",
  "prompt": "Design a microservices architecture for an e-commerce platform",
  "async": true
}
```

### Example with project_dir override

```python
{
  "session_name": "architect",
  "agent_name": "system-architect",
  "project_dir": "/absolute/path/to/project",
  "prompt": "Design a microservices architecture for an e-commerce platform"
}
```

### Response

**Synchronous mode (`async: false` or omitted)**: The agent's result after completing the task.

**Asynchronous mode (`async: true`)**: Immediate confirmation that the session started. Use `get_agent_status` to check progress and `get_agent_result` to retrieve the final result.

---

## 4. resume_agent

Resumes an existing agent session with a new prompt.

### Parameters

- `session_name` (required): Name of existing session to resume
- `project_dir` (optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!
- `prompt` (required): Continuation prompt
- `async` (optional): Run in background (default: `false`). When `true`, returns immediately and use `get_agent_status` / `get_agent_result` to check progress

### Example (synchronous)

```python
{
  "session_name": "architect",
  "prompt": "Add security considerations to the architecture design"
}
```

### Example (asynchronous)

```python
{
  "session_name": "architect",
  "prompt": "Add security considerations to the architecture design",
  "async": true
}
```

### Example with project_dir override

```python
{
  "session_name": "architect",
  "project_dir": "/absolute/path/to/project",
  "prompt": "Add security considerations to the architecture design"
}
```

### Response

**Synchronous mode (`async: false` or omitted)**: The agent's result after processing the new prompt.

**Asynchronous mode (`async: true`)**: Immediate confirmation that the session resumed. Use `get_agent_status` to check progress and `get_agent_result` to retrieve the final result.

---

## 5. clean_sessions

Removes all agent sessions permanently.

### Parameters

- `project_dir` (optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!

### Example

```python
{}
```

### Example with project_dir override

```python
{
  "project_dir": "/absolute/path/to/project"
}
```

### Response

Confirmation message (e.g., "All sessions removed" or "No sessions to remove").

---

## 6. get_agent_status

Check the status of a running or completed agent session. Used with asynchronous execution to monitor progress.

### Parameters

- `session_name` (required): Name of session to check
- `project_dir` (optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!
- `wait_seconds` (optional): Wait before checking status (0-300 seconds). Useful for polling with a delay.

### Example

```python
{
  "session_name": "architect"
}
```

### Example with wait

```python
{
  "session_name": "architect",
  "wait_seconds": 5
}
```

### Example with project_dir override

```python
{
  "session_name": "architect",
  "project_dir": "/absolute/path/to/project"
}
```

### Response

```json
{
  "status": "running"
}
```

or

```json
{
  "status": "finished"
}
```

or

```json
{
  "status": "not_existent"
}
```

**Status values:**
- `"running"` - Agent is still executing
- `"finished"` - Agent has completed, use `get_agent_result` to retrieve output
- `"not_existent"` - Session does not exist

---

## 7. get_agent_result

Retrieve the result from a completed agent session. Used with asynchronous execution to get the final output.

### Parameters

- `session_name` (required): Name of completed session
- `project_dir` (optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!

### Example

```python
{
  "session_name": "architect"
}
```

### Example with project_dir override

```python
{
  "session_name": "architect",
  "project_dir": "/absolute/path/to/project"
}
```

### Response

The agent's final result/output from the completed session.

**Note**: If the session is still running or does not exist, an appropriate error will be returned. Use `get_agent_status` first to check if the session has finished.

---

## Session Naming Rules

Session names must follow these constraints:
- **Length**: 1-60 characters
- **Characters**: Only alphanumeric, dash (`-`), and underscore (`_`)
- **Uniqueness**: Cannot create a session with a name that already exists
- **Examples**: `architect`, `code-reviewer`, `my_agent_123`, `dev-session-1`

## Error Handling

The server provides clear, actionable error messages:

- **Session already exists**: Use `resume_agent` or choose a different name
- **Session does not exist**: Use `start_agent` to create it first
- **Invalid session name**: Check naming rules (alphanumeric, dash, underscore; max 60 chars)
- **Agent not found**: Use `list_agents` to see available agents
- **Script execution failed**: Check that the script path and environment variables are configured correctly
