# Integration Scenarios

Configuration guide for the Agent Orchestrator MCP Server with Claude Code and Claude Desktop.

## Prerequisites

- Python ≥3.10
- [UV](https://docs.astral.sh/uv/getting-started/installation/) installed

## MCP Configuration Schema

All configurations follow this structure:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `command` | string | Yes | Must be `"uv"` |
| `args` | array | Yes | `["run", "/absolute/path/to/agent-orchestrator-mcp.py"]` |
| `env` | object | No | Environment variables (see below) |

## Environment Variables

| Variable | Claude Code | Claude Desktop | Description |
|----------|-------------|----------------|-------------|
| `AGENT_ORCHESTRATOR_COMMAND_PATH` | Auto-discovered | Auto-discovered | Path to commands (override only) |
| `AGENT_ORCHESTRATOR_PROJECT_DIR` | Optional | **Required** | Where agents execute |
| `PATH` | Not needed | **Required** | Must include `uv` and `claude` |
| `MCP_SERVER_DEBUG` | Optional | Optional | Enable debug logging |

## Claude Code Configuration

### Minimal Setup (Recommended)

The MCP server auto-discovers the commands directory. No environment variables needed.

Create `.mcp.json` in your project root:
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "uv",
      "args": ["run", "/absolute/path/to/agent-orchestrator-mcp.py"]
    }
  }
}
```

Orchestrated agents will run in your current Claude Code project directory.

### With Custom Project Directory

Set `AGENT_ORCHESTRATOR_PROJECT_DIR` to run agents in a different directory:

```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "uv",
      "args": ["run", "/absolute/path/to/agent-orchestrator-mcp.py"],
      "env": {
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/target/project"
      }
    }
  }
}
```

## Claude Desktop Configuration

### Config File Location

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

### Configuration

Claude Desktop requires `AGENT_ORCHESTRATOR_PROJECT_DIR` and `PATH`:

```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "uv",
      "args": ["run", "/absolute/path/to/agent-orchestrator-mcp.py"],
      "env": {
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/project",
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
      }
    }
  }
}
```

**Important:**
- `PATH` must include directories containing `uv` and `claude` binaries
- Claude Desktop doesn't inherit shell PATH
- Restart Claude Desktop after configuration changes

## Per-Tool Project Directory Override

All MCP tools accept an optional `project_dir` parameter to override the configured project directory for a single call:

```python
{
  "session_name": "architect",
  "project_dir": "/different/project",
  "prompt": "Analyze this project"
}
```

## Debugging

Enable debug logging:
```json
"env": {
  "MCP_SERVER_DEBUG": "true"
}
```

Logs are written to: `interfaces/agent-orchestrator-mcp-server/logs/mcp-server.log`

## Troubleshooting

### Tools not appearing in Claude Desktop

1. Verify `PATH` includes `uv` and `claude` binary locations
2. Check configuration is valid JSON
3. Ensure all paths are absolute
4. Restart Claude Desktop

### Command execution errors

1. Test server directly: `uv run /path/to/agent-orchestrator-mcp.py`
2. Verify Python ≥3.10: `python --version`
3. Check UV is installed: `uv --version`

For detailed troubleshooting, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).

## Additional Resources

- [README.md](../README.md) - Overview and quick reference
- [TOOLS_REFERENCE.md](./TOOLS_REFERENCE.md) - Detailed tool documentation
- [ENV_VARS.md](./ENV_VARS.md) - Environment variable reference
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Implementation details