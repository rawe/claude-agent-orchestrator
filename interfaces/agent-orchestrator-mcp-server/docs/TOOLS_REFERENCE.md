# Tools Reference

Detailed API documentation for all MCP tools provided by the Agent Orchestrator server.

## Overview

The Agent Orchestrator MCP Server provides 7 tools for managing orchestrated agent sessions:

1. **list_agent_blueprints** - Discover available agent blueprints
2. **list_agent_sessions** - View all agent session instances with their IDs and project directories
3. **start_agent_session** - Create new agent session instances with optional specialization (supports async execution)
4. **resume_agent_session** - Continue work in existing session instances (supports async execution)
5. **delete_all_agent_sessions** - Permanently delete all session instances
6. **get_agent_session_status** - Check the status of a running or completed session instance
7. **get_agent_session_result** - Retrieve the result from a completed session instance

All tools support optional `project_dir` override for managing multiple projects.

---

## 1. list_agent_blueprints

Lists all available agent blueprints that can be used to create agent sessions.

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

## 2. list_agent_sessions

Lists all agent session instances (running, completed, or initializing).

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

## 3. start_agent_session

Start a new agent session instance that immediately begins execution.

### Parameters

- `session_name` (required): Unique identifier for this agent session instance (alphanumeric, dash, underscore; max 60 chars)
- `agent_blueprint_name` (optional): Name of agent blueprint to use for this session (optional for generic sessions)
- `project_dir` (optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!
- `prompt` (required): Initial task description or prompt for the agent session
- `async` (optional): Run in background (default: `false`). When `true`, returns immediately and use `get_agent_session_status` / `get_agent_session_result` to check progress

### Example (synchronous)

```python
{
  "session_name": "architect",
  "agent_blueprint_name": "system-architect",
  "prompt": "Design a microservices architecture for an e-commerce platform"
}
```

### Example (asynchronous)

```python
{
  "session_name": "architect",
  "agent_blueprint_name": "system-architect",
  "prompt": "Design a microservices architecture for an e-commerce platform",
  "async": true
}
```

### Example with project_dir override

```python
{
  "session_name": "architect",
  "agent_blueprint_name": "system-architect",
  "project_dir": "/absolute/path/to/project",
  "prompt": "Design a microservices architecture for an e-commerce platform"
}
```

### Response

**Synchronous mode (`async: false` or omitted)**: The agent's result after completing the task.

**Asynchronous mode (`async: true`)**: Immediate confirmation that the session started. Use `get_agent_session_status` to check progress and `get_agent_session_result` to retrieve the final result.

---

## 4. resume_agent_session

Resume an existing agent session instance with a new prompt to continue work.

### Parameters

- `session_name` (required): Name of the existing agent session instance to resume
- `project_dir` (optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!
- `prompt` (required): Continuation prompt building on previous session context
- `async` (optional): Run in background (default: `false`). When `true`, returns immediately and use `get_agent_session_status` / `get_agent_session_result` to check progress

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

**Asynchronous mode (`async: true`)**: Immediate confirmation that the session resumed. Use `get_agent_session_status` to check progress and `get_agent_session_result` to retrieve the final result.

---

## 5. delete_all_agent_sessions

Permanently delete all agent session instances and their associated data.

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

## 6. get_agent_session_status

Check the current status of an agent session instance (running, finished, or not_existent). Used with asynchronous execution to monitor progress.

### Parameters

- `session_name` (required): Name of the agent session instance to check
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
- `"running"` - Agent session instance is still executing
- `"finished"` - Agent session instance has completed, use `get_agent_session_result` to retrieve output
- `"not_existent"` - Session instance does not exist

---

## 7. get_agent_session_result

Retrieve the final output/result from a completed agent session instance. Used with asynchronous execution to get the final output.

### Parameters

- `session_name` (required): Name of the completed agent session instance
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

**Note**: If the session is still running or does not exist, an appropriate error will be returned. Use `get_agent_session_status` first to check if the session has finished.

---

## Session Naming Rules

Session names must follow these constraints:
- **Length**: 1-60 characters
- **Characters**: Only alphanumeric, dash (`-`), and underscore (`_`)
- **Uniqueness**: Cannot create a session with a name that already exists
- **Examples**: `architect`, `code-reviewer`, `my_agent_123`, `dev-session-1`

## Error Handling

The server provides clear, actionable error messages:

- **Session already exists**: Use `resume_agent_session` or choose a different name
- **Session does not exist**: Use `start_agent_session` to create it first
- **Invalid session name**: Check naming rules (alphanumeric, dash, underscore; max 60 chars)
- **Agent not found**: Use `list_agent_blueprints` to see available agent blueprints
- **Script execution failed**: Check that the script path and environment variables are configured correctly
