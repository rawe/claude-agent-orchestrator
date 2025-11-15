# Agent Orchestrator MCP Server (Python)

A Model Context Protocol (MCP) server that provides tools for orchestrating specialized Claude Code agents through the agent orchestrator Python commands.

> **Python Implementation**: This is a Python implementation of the Agent Orchestrator MCP Server. It provides identical functionality to the TypeScript version but uses the MCP Python SDK and runs via `uv` for self-contained dependency management.

## Overview

### What is the Agent Orchestrator Framework (AOF)?

The **Agent Orchestrator Framework (AOF)** is the combination of this MCP server and the agent orchestrator Python commands (from the `agent-orchestrator-cli` package). Together they enable creating and managing specialized Claude Code agent sessions that work autonomously on tasks.

**Key components**:
- **This MCP server**: Provides MCP tools for orchestrating agents from any MCP-compatible AI system
- **Python commands**: The underlying Python commands (`ao-new`, `ao-resume`, etc.) that launch and manage Claude Code sessions via `uv`
- **Agent definitions**: Specialized agent configurations (`.agent-orchestrator/agents/`)
- **Sessions**: Active or completed agent work sessions (`.agent-orchestrator/sessions/`)

### Relationship to Claude Code Plugin

Previously, the agent orchestrator was available only as a Claude Code skill/plugin installed in `.claude/skills/`. This MCP server **provides an abstraction layer** that:
- Works with any AI agent system supporting MCP (Claude Desktop, Claude Code, etc.)
- No longer requires installing the skill as a Claude Code plugin
- Provides a standardized MCP interface for agent orchestration

### What This MCP Server Does

Provides 7 MCP tools for managing orchestrated agent sessions:
- Discover available specialized agent definitions
- Create new agent sessions (generic or specialized)
- Resume existing agent sessions
- List active sessions
- Clean up sessions
- Check agent status (for async mode)
- Retrieve agent results (for async mode)

## Features

- **7 MCP Tools**:
  - `list_agents` - Discover available specialized agent definitions
  - `list_sessions` - View all agent sessions with their IDs and project directories
  - `start_agent` - Create new agent sessions with optional specialization (sync/async modes)
  - `resume_agent` - Continue work in existing sessions (sync/async modes)
  - `clean_sessions` - Remove all sessions
  - `get_agent_status` - Check session status for async polling
  - `get_agent_result` - Retrieve completed session results

- **Type-Safe**: Full Python implementation with Pydantic validation
- **Flexible Output**: Support for both Markdown (human-readable) and JSON (machine-readable) formats
- **Comprehensive Error Handling**: Clear, actionable error messages
- **Character Limits**: Automatic truncation for large responses
- **Self-Contained**: Uses `uv` for automatic dependency management - no manual installation required

## Installation

### Prerequisites

- **Python**: >= 3.10
- **uv**: Python package manager ([install instructions](https://docs.astral.sh/uv/getting-started/installation/))
- **Agent Orchestrator CLI**: The Python commands that this server orchestrates

### Quick Start

**No installation required!** The MCP server is self-contained when run with `uv`. Dependencies are automatically managed.

#### For Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/agent-orchestrator-mcp-python",
        "run",
        "python",
        "-m",
        "agent_orchestrator_mcp"
      ],
      "env": {
        "AGENT_ORCHESTRATOR_COMMAND_PATH": "/absolute/path/to/agent-orchestrator-cli/commands",
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/absolute/path/to/your/project",
        "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin"
      }
    }
  }
}
```

#### For Testing with MCP Inspector

```bash
# Navigate to the project directory
cd /path/to/agent-orchestrator-mcp-python

# Set required environment variables
export AGENT_ORCHESTRATOR_COMMAND_PATH="/absolute/path/to/agent-orchestrator-cli/commands"
export AGENT_ORCHESTRATOR_PROJECT_DIR="/absolute/path/to/your/project"

# Run with MCP Inspector (uv handles dependencies automatically)
uv run mcp-inspector python -m agent_orchestrator_mcp
```

### How It Works

When you run the server with `uv`:
1. `uv` automatically creates a virtual environment (if needed)
2. `uv` installs all dependencies from `pyproject.toml` (if needed)
3. `uv` runs the server

**No manual installation required** - `uv` handles everything automatically!

## Environment Variables Reference

This is the **single source of truth** for all environment variables used by the Agent Orchestrator MCP Server.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AGENT_ORCHESTRATOR_COMMAND_PATH` | **Yes** | - | Absolute path to the commands directory containing Python scripts (e.g., `/path/to/agent-orchestrator-cli/commands`) |
| `AGENT_ORCHESTRATOR_PROJECT_DIR` | **Claude Desktop: Yes**<br>Claude Code: No | Current directory (Claude Code only) | Project directory where orchestrated agents execute. Controls the base for other defaults. |
| `AGENT_ORCHESTRATOR_SESSIONS_DIR` | No | `$PROJECT_DIR/.agent-orchestrator/sessions` | Custom location for agent session storage. Use for centralized session management across projects. |
| `AGENT_ORCHESTRATOR_AGENTS_DIR` | No | `$PROJECT_DIR/.agent-orchestrator/agents` | Custom location for agent definitions. Use to share agent definitions across projects. |
| `AGENT_ORCHESTRATOR_ENABLE_LOGGING` | No | `false` | Set to `"true"` to enable logging of orchestrated agent execution. Used for debugging agent sessions. |
| `MCP_SERVER_DEBUG` | No | `false` | Set to `"true"` to enable debug logging to `logs/mcp-server.log`. Used for troubleshooting MCP server issues. |
| `PATH` | **Claude Desktop only** | - | Must include path to Python and uv binaries. Claude Desktop does not inherit shell PATH. Example: `/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin` |

### Variable Details

**`AGENT_ORCHESTRATOR_COMMAND_PATH`** (Required)
- Absolute path to the commands directory containing Python scripts
- Example (local development): `/Users/yourname/projects/agent-orchestrator-cli/commands`
- Example (production): `/usr/local/lib/agent-orchestrator/commands`
- The directory should contain: `ao-new`, `ao-resume`, `ao-list-sessions`, `ao-list-agents`, `ao-clean`, `ao-status`, `ao-get-result`

**`AGENT_ORCHESTRATOR_PROJECT_DIR`** (Conditionally Required)
- Directory where orchestrated agents execute
- Required for Claude Desktop
- Optional for Claude Code (defaults to current directory where MCP server is invoked)
- This is the working directory for all agent sessions
- Example: `/Users/yourname/my-project`

**`AGENT_ORCHESTRATOR_SESSIONS_DIR`** (Optional)
- Custom path for storing session data
- Defaults to `.agent-orchestrator/sessions/` within the project directory
- Use when you want centralized session management across multiple projects
- Example: `/Users/yourname/.agent-orchestrator-global/sessions`

**`AGENT_ORCHESTRATOR_AGENTS_DIR`** (Optional)
- Custom path for agent definition files
- Defaults to `.agent-orchestrator/agents/` within the project directory
- Use when you want to share agent definitions across multiple projects
- Example: `/Users/yourname/.agent-orchestrator-global/agents`

**`AGENT_ORCHESTRATOR_ENABLE_LOGGING`** (Optional)
- Enable logging for orchestrated agent sessions
- Set to `"true"` for debugging purposes
- Logs agent execution details

**`MCP_SERVER_DEBUG`** (Optional)
- Enable debug logging for the MCP server itself
- Set to `"true"` to write logs to `logs/mcp-server.log`
- Logs include server startup, tool calls, script execution, and errors

**`PATH`** (Claude Desktop Only)
- Required for Claude Desktop because UI applications do not inherit shell environment PATH
- Must include the directory containing the `python` and `uv` binaries
- Common values:
  - macOS with Homebrew: `/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin`
  - Linux: `/usr/local/bin:/usr/bin:/bin`

## Tools Reference

### 1. list_agents

Lists all available specialized agent definitions.

**Parameters**:
- `project_dir` (optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!
- `response_format` (optional): `"markdown"` or `"json"` (default: `"markdown"`)

**Example**:
```python
{
  "response_format": "json"
}
```

**Response** (JSON format):
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

### 2. list_sessions

Lists all existing agent sessions with their session IDs and project directories.

**Parameters**:
- `project_dir` (optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!
- `response_format` (optional): `"markdown"` or `"json"` (default: `"markdown"`)

**Example**:
```python
{
  "response_format": "json"
}
```

**Response** (JSON format):
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

### 3. start_agent

Creates a new orchestrated agent session.

**Parameters**:
- `session_name` (required): Unique session name (alphanumeric, dash, underscore; max 60 chars)
- `agent_name` (optional): Name of agent definition to use
- `project_dir` (optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!
- `prompt` (required): Initial task description
- `async` (optional): Run in background mode (default: `false`)

**Example**:
```python
{
  "session_name": "architect",
  "agent_name": "system-architect",
  "prompt": "Design a microservices architecture for an e-commerce platform"
}
```

**Response**: The agent's result after completing the task.

### 4. resume_agent

Resumes an existing agent session with a new prompt.

**Parameters**:
- `session_name` (required): Name of existing session to resume
- `project_dir` (optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!
- `prompt` (required): Continuation prompt
- `async` (optional): Run in background mode (default: `false`)

**Example**:
```python
{
  "session_name": "architect",
  "prompt": "Add security considerations to the architecture design"
}
```

**Response**: The agent's result after processing the new prompt.

### 5. clean_sessions

Removes all agent sessions permanently.

**Parameters**:
- `project_dir` (optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!

**Example**:
```python
{}
```

**Response**: Confirmation message (e.g., "All sessions removed" or "No sessions to remove").

### 6. get_agent_status

Check the current status of an agent session (for async mode).

**Parameters**:
- `session_name` (required): Name of the session to check
- `project_dir` (optional): Project directory path
- `wait_seconds` (optional): Seconds to wait before checking (default: 0, max: 300)

**Example**:
```python
{
  "session_name": "architect",
  "wait_seconds": 10
}
```

**Response**:
```json
{
  "status": "finished"
}
```

Possible statuses: `"running"`, `"finished"`, `"not_existent"`

### 7. get_agent_result

Retrieve the final result from a completed agent session (for async mode).

**Parameters**:
- `session_name` (required): Name of the completed session
- `project_dir` (optional): Project directory path

**Example**:
```python
{
  "session_name": "architect"
}
```

**Response**: The agent's final response/result as text.

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

## Development

### Project Structure

```
agent-orchestrator-mcp-python/
├── src/
│   └── agent_orchestrator_mcp/
│       ├── __init__.py       # Package initialization
│       ├── __main__.py       # Main MCP server with tool implementations
│       ├── types.py          # Pydantic type definitions
│       ├── schemas.py        # Pydantic validation schemas
│       ├── constants.py      # Constants and configuration
│       ├── utils.py          # Shared utility functions
│       └── logger.py         # File-based logging system
├── logs/                     # Log directory (created at runtime)
├── pyproject.toml            # Python dependencies and project config
└── README.md                 # This file
```

### Running Locally

```bash
# Navigate to project directory
cd /path/to/agent-orchestrator-mcp-python

# Set environment variables
export AGENT_ORCHESTRATOR_COMMAND_PATH="/path/to/commands"
export AGENT_ORCHESTRATOR_PROJECT_DIR="/path/to/project"

# Run server (uv handles dependencies automatically)
uv run python -m agent_orchestrator_mcp
```

### Testing

After implementation, you can test the server using the MCP Inspector:

```bash
cd /path/to/agent-orchestrator-mcp-python
export AGENT_ORCHESTRATOR_COMMAND_PATH="/path/to/commands"
export AGENT_ORCHESTRATOR_PROJECT_DIR="/path/to/project"

uv run mcp-inspector python -m agent_orchestrator_mcp
```

Make sure to set the required environment variables before testing.

## Debugging and Troubleshooting

The MCP server includes comprehensive debug logging to help troubleshoot issues.

### Enabling Debug Logging

Debug logging is **disabled by default**. To enable it, set the `MCP_SERVER_DEBUG` environment variable to `"true"`:

```bash
export MCP_SERVER_DEBUG="true"
```

Or add it to your MCP configuration:
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/agent-orchestrator-mcp-python",
        "run",
        "python",
        "-m",
        "agent_orchestrator_mcp"
      ],
      "env": {
        "AGENT_ORCHESTRATOR_COMMAND_PATH": "/path/to/commands",
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/project",
        "MCP_SERVER_DEBUG": "true"
      }
    }
  }
}
```

### Debug Logs Location

When enabled, all debug logs are written to:
```
agent-orchestrator-mcp-python/logs/mcp-server.log
```

### What's Logged

The logs include:
- **Server startup**: Configuration, environment variables, working directory
- **Tool calls**: Which tools are called with what parameters
- **Script execution**: Full command-line arguments, environment, stdout/stderr
- **Errors**: Detailed error messages with stack traces
- **Performance**: Execution duration for long-running operations

### Viewing Logs

**View the entire log file**:
```bash
cat agent-orchestrator-mcp-python/logs/mcp-server.log
```

**View formatted logs** (each line is JSON):
```bash
cat agent-orchestrator-mcp-python/logs/mcp-server.log | jq '.'
```

**Follow logs in real-time**:
```bash
tail -f agent-orchestrator-mcp-python/logs/mcp-server.log | jq '.'
```

**Filter by log level**:
```bash
# Show only errors
cat agent-orchestrator-mcp-python/logs/mcp-server.log | jq 'select(.level == "ERROR")'

# Show errors and warnings
cat agent-orchestrator-mcp-python/logs/mcp-server.log | jq 'select(.level == "ERROR" or .level == "WARN")'
```

**Search for specific operations**:
```bash
# Find all start_agent calls
cat agent-orchestrator-mcp-python/logs/mcp-server.log | jq 'select(.message | contains("start_agent"))'
```

### Common Issues

1. **`start_agent` fails but `list_agents` works**:
   - Check that the `claude` CLI is installed and in PATH
   - Review script execution logs for the exact error
   - Verify `AGENT_ORCHESTRATOR_PROJECT_DIR` is set correctly (or omit it to use current directory)

2. **Command execution errors**:
   - Look for "Command execution error" or "Command execution completed" log entries
   - Check the `exitCode`, `stdout`, and `stderr` fields in the logs
   - Verify the command path in `AGENT_ORCHESTRATOR_COMMAND_PATH` is correct

3. **Environment issues**:
   - Check the "Agent Orchestrator MCP Server starting" log entry
   - Verify all environment variables are set correctly
   - Check that `PWD` and `PATH` are what you expect

4. **uv not found**:
   - Ensure `uv` is installed: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Verify `uv` is in your PATH
   - For Claude Desktop, add the directory containing `uv` to the `PATH` environment variable

## Requirements

- **Python**: >= 3.10
- **uv**: Python package manager (must be in PATH)
- **MCP SDK**: >= 1.7.0 (installed automatically by uv)
- **Pydantic**: >= 2.0.0 (installed automatically by uv)

## License

MIT

## Related Projects

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- Agent Orchestrator CLI (Python commands referenced by this server)
