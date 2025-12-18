# Agent Orchestrator MCP Server

Model Context Protocol (MCP) server for orchestrating specialized Claude Code agents. Provides tools to create, manage, and execute agent sessions programmatically.

## Quick Start

**Requirements:** Python ≥3.10, [uv](https://docs.astral.sh/uv/getting-started/installation/)

**Run:**
```bash
uv run --script /path/to/interfaces/agent-orchestrator-mcp-server/agent-orchestrator-mcp.py
```

Dependencies (mcp≥1.7.0, pydantic≥2.0.0) are automatically managed via inline script metadata.

**Note:** The MCP server now automatically discovers the commands directory relative to its location. No `AGENT_ORCHESTRATOR_COMMAND_PATH` environment variable needed for basic setup!

**Example usage:**
- "List all available orchestrated agents"
- "Start a new agent session called 'architect' and ask it to design a microservices architecture"
- "Check the status of the architect session"

## Configuration

### Claude Code

**Minimal Configuration (auto-discovery):**
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "uv",
      "args": [
        "run",
        "--script",
        "/absolute/path/to/interfaces/agent-orchestrator-mcp-server/agent-orchestrator-mcp.py"
      ]
    }
  }
}
```

**With Custom Project Directory:**
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "uv",
      "args": [
        "run",
        "--script",
        "/absolute/path/to/interfaces/agent-orchestrator-mcp-server/agent-orchestrator-mcp.py"
      ],
      "env": {
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/project"
      }
    }
  }
}
```

**Note:** `AGENT_ORCHESTRATOR_COMMAND_PATH` is no longer required (auto-discovered). Set `AGENT_ORCHESTRATOR_PROJECT_DIR` only if you want orchestrated agents to run in a specific directory instead of the current directory.

### Claude Desktop

**Config file location:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

**Minimal Configuration:**
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "uv",
      "args": [
        "run",
        "--script",
        "/absolute/path/to/interfaces/agent-orchestrator-mcp-server/agent-orchestrator-mcp.py"
      ],
      "env": {
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/project",
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
      }
    }
  }
}
```

**Note:**
- `AGENT_ORCHESTRATOR_COMMAND_PATH` is no longer required (auto-discovered)
- `AGENT_ORCHESTRATOR_PROJECT_DIR` sets where orchestrated agents run
- `PATH` must include `uv` and `claude` binaries (Claude Desktop doesn't inherit shell PATH)

**After updating:** Restart Claude Desktop. Verify 7 tools are available in the MCP icon.

## Environment Variables

**Auto-Discovered (No Configuration Needed):**
- `AGENT_ORCHESTRATOR_COMMAND_PATH` - Now auto-discovered relative to MCP server location. Can still be set to override.

**Required for Claude Desktop:**
- `AGENT_ORCHESTRATOR_PROJECT_DIR` - Project directory where orchestrated agents run (must be set for Claude Desktop only)
- `PATH` - Include `uv` and `claude` binaries (Claude Desktop doesn't inherit shell PATH)

**Optional:**
- `MCP_SERVER_DEBUG` - Enable debug logging

**For complete reference, defaults, and examples, see [ENV_VARS.md](./docs/ENV_VARS.md)**

## MCP Tools

The server provides 7 MCP tools for managing orchestrated agent sessions:

| Tool | Description |
|------|-------------|
| `list_agent_blueprints` | Discover available agent blueprints |
| `list_agent_sessions` | View all agent session instances with their IDs and project directories |
| `start_agent_session` | Create new agent session instances (supports async execution) |
| `resume_agent_session` | Continue work in existing session instances (supports async execution) |
| `delete_all_agent_sessions` | Permanently delete all session instances |
| `get_agent_session_status` | Check status of running or completed session instances |
| `get_agent_session_result` | Retrieve result from completed session instances |

All tools support optional `project_dir` parameter for managing multiple projects.

**For detailed API documentation, parameters, and examples, see [TOOLS_REFERENCE.md](./docs/TOOLS_REFERENCE.md)**

## HTTP & API Mode

The server supports multiple transport modes beyond the default stdio:

| Mode | Command | Description |
|------|---------|-------------|
| stdio | `uv run --script agent-orchestrator-mcp.py` | Default, for Claude Desktop/CLI |
| HTTP | `--http-mode` | MCP protocol over HTTP |
| SSE | `--sse-mode` | Legacy SSE transport |
| **API** | `--api-mode` | REST API + MCP combined with OpenAPI docs |

**API Mode** provides both MCP protocol and a REST API with automatic OpenAPI documentation:

```bash
# Using Make (from project root)
make start-ao-api

# Direct command
uv run --script agent-orchestrator-mcp.py --api-mode --port 9500
```

When running in API mode:
- `/mcp` - MCP protocol endpoint
- `/api/*` - REST API endpoints
- `/api/docs` - Swagger UI documentation
- `/api/redoc` - ReDoc documentation

**For complete API mode documentation, client examples, and integration guide, see [API-MODE.md](./docs/API-MODE.md)**

## Project Structure

```
agent-orchestrator-mcp-server/
├── agent-orchestrator-mcp.py    # Main entry point with CLI args
├── libs/                        # Modular library code
│   ├── constants.py            # Constants and configuration
│   ├── core_functions.py       # Core async functions (shared by MCP & REST)
│   ├── logger.py               # Debug logging
│   ├── rest_api.py             # FastAPI REST endpoints
│   ├── schemas.py              # Input validation
│   ├── server.py               # MCP server & combined app logic
│   ├── types_models.py         # Type definitions
│   └── utils.py                # Utility functions
├── docs/                        # Documentation
│   ├── API-MODE.md             # REST API mode guide
│   ├── ENV_VARS.md             # Environment variables reference
│   ├── TOOLS_REFERENCE.md      # MCP tools documentation
│   └── TROUBLESHOOTING.md      # Debugging guide
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

- **Session already exists**: Use `resume_agent_session` or different name
- **Session does not exist**: Use `start_agent_session` first
- **Invalid session name**: Check naming rules
- **Agent not found**: Use `list_agent_blueprints` to see available agent blueprints
- **Command path error**: Verify `AGENT_ORCHESTRATOR_COMMAND_PATH` is correct

## Testing

```bash
# No environment variables needed! Commands are auto-discovered
uv run --script agent-orchestrator-mcp.py
```

With custom project directory:
```bash
export AGENT_ORCHESTRATOR_PROJECT_DIR="/path/to/project"
uv run --script agent-orchestrator-mcp.py
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
