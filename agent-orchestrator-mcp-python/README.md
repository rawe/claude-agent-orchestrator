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
| `PATH` | **Claude Desktop only** | - | Must include path to `uv` and `claude` binaries. Claude Desktop does not inherit shell PATH. Example: `/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin` |

### Variable Details

**`AGENT_ORCHESTRATOR_COMMAND_PATH`** (Required)
- Absolute path to the commands directory containing Python scripts
- Example (local development): `/Users/yourname/projects/agent-orchestrator-cli/commands`
- Example (production): `/usr/local/lib/agent-orchestrator/commands`
- The directory should contain: `ao-new`, `ao-resume`, `ao-list-sessions`, `ao-list-agents`, `ao-clean`

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
- Must include directories containing the `uv` and `claude` binaries
- Common values:
  - macOS with Homebrew: `/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin`
  - macOS with custom install: `/Users/yourname/.local/bin:/usr/local/bin:/usr/bin:/bin`

## MCP Tools

The server provides 7 MCP tools for managing orchestrated agent sessions:

| Tool | Description |
|------|-------------|
| `list_agents` | Discover available specialized agent definitions |
| `list_sessions` | View all agent sessions with their IDs and project directories |
| `start_agent` | Create new agent sessions (supports async execution) |
| `resume_agent` | Continue work in existing sessions (supports async execution) |
| `clean_sessions` | Remove all sessions |
| `get_agent_status` | Check status of running or completed sessions |
| `get_agent_result` | Retrieve result from completed sessions |

All tools support optional `project_dir` parameter for managing multiple projects.

**For detailed API documentation, parameters, and examples, see [TOOLS_REFERENCE.md](./TOOLS_REFERENCE.md)**

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

Enable debug logging by setting `MCP_SERVER_DEBUG="true"`. Logs are written to `logs/mcp-server.log`.

**For comprehensive debugging guide, log filtering, and troubleshooting common issues, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)**

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
