# Agent Orchestrator MCP Server (Python)

Model Context Protocol (MCP) server for orchestrating specialized Claude Code agents. Provides tools to create, manage, and execute agent sessions programmatically.

## Quick Start

**Requirements:** Python ≥3.10, [uv](https://docs.astral.sh/uv/getting-started/installation/)

**Run:**
```bash
uv run /path/to/agent-orchestrator-mcp.py
```

Dependencies (mcp≥1.7.0, pydantic≥2.0.0) are automatically managed via inline script metadata.

## Configuration

### Claude Code

**simple.mcp.json:**
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "uv",
      "args": [
        "run",
        "/absolute/path/to/agent-orchestrator-mcp.py"
      ],
      "env": {
        "AGENT_ORCHESTRATOR_COMMAND_PATH": "/path/to/commands",
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/project"
      }
    }
  }
}
```

### Claude Desktop

**claude_desktop_config.json:**
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "uv",
      "args": [
        "run",
        "/absolute/path/to/agent-orchestrator-mcp.py"
      ],
      "env": {
        "AGENT_ORCHESTRATOR_COMMAND_PATH": "/path/to/commands",
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/project",
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
      }
    }
  }
}
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AGENT_ORCHESTRATOR_COMMAND_PATH` | Yes | Absolute path to commands directory |
| `AGENT_ORCHESTRATOR_PROJECT_DIR` | Claude Desktop: Yes<br>Claude Code: No | Project directory for agent execution |
| `AGENT_ORCHESTRATOR_SESSIONS_DIR` | No | Custom session storage location |
| `AGENT_ORCHESTRATOR_AGENTS_DIR` | No | Custom agent definitions location |
| `MCP_SERVER_DEBUG` | No | Set to `"true"` for debug logging to `logs/mcp-server.log` |
| `PATH` | Claude Desktop only | Must include path to uv and claude code binary |

## MCP Tools

### 1. list_agents
List available agent definitions.

**Parameters:**
- `project_dir` (optional): Project directory override
- `response_format` (optional): `"markdown"` or `"json"` (default: `"markdown"`)

### 2. list_sessions
List all agent sessions with IDs and project directories.

**Parameters:**
- `project_dir` (optional): Project directory override
- `response_format` (optional): `"markdown"` or `"json"`

### 3. start_agent
Create new agent session.

**Parameters:**
- `session_name` (required): Unique name (alphanumeric, dash, underscore; max 60 chars)
- `agent_name` (optional): Agent definition to use
- `project_dir` (optional): Project directory override
- `prompt` (required): Task description
- `async` (optional): Run in background (default: `false`)

### 4. resume_agent
Continue existing agent session.

**Parameters:**
- `session_name` (required): Session to resume
- `project_dir` (optional): Project directory override
- `prompt` (required): Continuation prompt
- `async` (optional): Run in background (default: `false`)

### 5. clean_sessions
Remove all agent sessions.

**Parameters:**
- `project_dir` (optional): Project directory override

### 6. get_agent_status
Check session status (for async mode).

**Parameters:**
- `session_name` (required): Session to check
- `project_dir` (optional): Project directory override
- `wait_seconds` (optional): Wait before checking (0-300 seconds)

**Returns:** `{"status": "running"|"finished"|"not_existent"}`

### 7. get_agent_result
Retrieve result from completed session (for async mode).

**Parameters:**
- `session_name` (required): Completed session name
- `project_dir` (optional): Project directory override

**Returns:** Agent's final response

## Project Structure

```
agent-orchestrator-mcp-python/
├── agent-orchestrator-mcp.py    # Main entry point (~40 lines)
├── libs/                        # Modular library code
│   ├── constants.py            # Constants and configuration
│   ├── logger.py               # Debug logging
│   ├── schemas.py              # Input validation
│   ├── server.py               # MCP server logic
│   ├── types_models.py         # Type definitions
│   └── utils.py                # Utility functions
├── logs/                        # Debug logs (when MCP_SERVER_DEBUG=true)
└── README.md
```

## Debugging

Enable debug logging:
```bash
export MCP_SERVER_DEBUG="true"
```

View logs:
```bash
tail -f logs/mcp-server.log | jq '.'
```

Logs include server startup, tool calls, script execution, and errors.

## Session Naming Rules

- Length: 1-60 characters
- Characters: Alphanumeric, dash (`-`), underscore (`_`) only
- Must be unique

## Common Errors

- **Session already exists**: Use `resume_agent` or different name
- **Session does not exist**: Use `start_agent` first
- **Invalid session name**: Check naming rules
- **Agent not found**: Use `list_agents` to see available agents
- **Command path error**: Verify `AGENT_ORCHESTRATOR_COMMAND_PATH` is correct

## Testing

```bash
export AGENT_ORCHESTRATOR_COMMAND_PATH="/path/to/commands"
export AGENT_ORCHESTRATOR_PROJECT_DIR="/path/to/project"
uv run agent-orchestrator-mcp.py
```

With MCP Inspector:
```bash
uv run mcp-inspector agent-orchestrator-mcp.py
```

## Implementation

Uses UV's inline dependency management (PEP 723). Dependencies declared in script header:
```python
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "mcp>=1.7.0",
#   "pydantic>=2.0.0",
# ]
# ///
```

UV automatically manages virtual environment and dependencies on first run.

## License

MIT
