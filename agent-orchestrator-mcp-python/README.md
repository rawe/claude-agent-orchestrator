# Agent Orchestrator MCP Server (Python)

Model Context Protocol (MCP) server for orchestrating specialized Claude Code agents. Provides tools to create, manage, and execute agent sessions programmatically.

## Quick Start

**Requirements:** Python ≥3.10, [uv](https://docs.astral.sh/uv/getting-started/installation/)

**Run:**
```bash
uv run /path/to/agent-orchestrator-mcp.py
```

Dependencies (mcp≥1.7.0, pydantic≥2.0.0) are automatically managed via inline script metadata.

**Example usage:**
- "List all available orchestrated agents"
- "Start a new agent session called 'architect' and ask it to design a microservices architecture"
- "Check the status of the architect session"

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

**Config file location:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

**Configuration:**
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

**After updating:** Restart Claude Desktop. Verify 7 tools are available in the MCP icon.

## Environment Variables

**Required:**
- `AGENT_ORCHESTRATOR_COMMAND_PATH` - Path to commands directory
- `AGENT_ORCHESTRATOR_PROJECT_DIR` - Project directory (Claude Desktop only)
- `PATH` - Include `uv` and `claude` binaries (Claude Desktop only)

**Optional:**
- `AGENT_ORCHESTRATOR_SESSIONS_DIR` - Custom session storage location
- `AGENT_ORCHESTRATOR_AGENTS_DIR` - Custom agent definitions location
- `MCP_SERVER_DEBUG` - Enable debug logging

**For complete reference, defaults, and examples, see [ENV_VARS.md](./docs/ENV_VARS.md)**

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

**For detailed API documentation, parameters, and examples, see [TOOLS_REFERENCE.md](./docs/TOOLS_REFERENCE.md)**

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

**For comprehensive debugging guide, log filtering, and troubleshooting common issues, see [TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md)**

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
