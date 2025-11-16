# Getting Started

Get the Agent Orchestrator MCP Server (Python) up and running quickly with this guide.

## Prerequisites

1. **Python** >= 3.10
2. **uv** (Python package manager) installed and in PATH - [Installation Guide](https://docs.astral.sh/uv/getting-started/installation/)
3. The agent orchestrator Python commands installed and accessible
4. A project directory where you want to run orchestrated agents

## Installation

**No installation or build step required!** The Python implementation uses UV's inline dependency management.

Simply verify UV is installed:
```bash
uv --version
```

## Quick Setup - Claude Desktop

### 1. Find Your Configuration File

Locate your Claude Desktop configuration file:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### 2. Add the MCP Server Configuration

Add this configuration to your Claude Desktop config file:

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
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin",
        "AGENT_ORCHESTRATOR_COMMAND_PATH": "/absolute/path/to/commands",
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/your/project"
      }
    }
  }
}
```

**Configuration Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `command` | string | Yes | Must be `"uv"` |
| `args` | array | Yes | `["run", "/absolute/path/to/agent-orchestrator-mcp.py"]` |
| `env` | object | Yes | Environment variables (see below) |

**Environment Variables:**

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `AGENT_ORCHESTRATOR_COMMAND_PATH` | **Yes** | Absolute path to commands directory | `/Users/you/agent-orchestrator-cli/commands` |
| `AGENT_ORCHESTRATOR_PROJECT_DIR` | **Yes** (Claude Desktop) | Project directory for agent execution | `/Users/you/my-project` |
| `PATH` | **Yes** (Claude Desktop) | Must include paths to `uv` and `claude` binaries | `/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin` |
| `AGENT_ORCHESTRATOR_SESSIONS_DIR` | No | Custom session storage location | `/Users/you/.sessions` |
| `AGENT_ORCHESTRATOR_AGENTS_DIR` | No | Custom agent definitions location | `/Users/you/.agents` |
| `MCP_SERVER_DEBUG` | No | Enable debug logging (`"true"` or `"false"`) | `"true"` |

**Important**:
- Replace all paths with your actual absolute paths
- `PATH` must include directories containing `uv` and `claude` binaries (required for Claude Desktop)
- See [README.md - Environment Variables Reference](./README.md#environment-variables-reference) for complete details

### 3. Restart Claude Desktop

Completely quit and restart Claude Desktop for the changes to take effect.

### 4. Verify It Works

After restart:
- Look for the MCP icon in Claude Desktop
- The server should show **7 tools available**
- Try: "List all available orchestrated agents"

## Quick Setup - Claude Code

### 1. Create or Edit Your MCP Configuration

**For project-specific setup**, create `simple.mcp.json` in your project root:

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
        "AGENT_ORCHESTRATOR_COMMAND_PATH": "/absolute/path/to/commands"
      }
    }
  }
}
```

**Note**: Claude Code automatically sets `AGENT_ORCHESTRATOR_PROJECT_DIR` to the current directory, so you typically don't need to specify it.

### 2. Verify Configuration

Run Claude Code in your project and verify the tools are available:
- Ask: "List available MCP tools"
- Should show 7 agent orchestrator tools

## Testing with MCP Inspector (Optional)

Test the server locally before integrating with Claude Desktop/Code:

```bash
# Set environment variables
export AGENT_ORCHESTRATOR_COMMAND_PATH="/absolute/path/to/commands"
export AGENT_ORCHESTRATOR_PROJECT_DIR="/path/to/your/project"

# Run MCP Inspector
npx @modelcontextprotocol/inspector uv run /path/to/agent-orchestrator-mcp.py
```

This opens a web interface where you can:
- See all 7 available tools
- Test tool calls with different parameters
- View responses in real-time

## Available Tools

The MCP server provides 7 tools:

1. **list_agents** - Lists all available specialized agent definitions
2. **list_sessions** - Lists all active agent sessions with their IDs and project directories
3. **start_agent** - Starts a new orchestrated agent session (supports async)
4. **resume_agent** - Resumes an existing agent session (supports async)
5. **clean_sessions** - Removes all agent sessions
6. **get_agent_status** - Check status of running or completed sessions
7. **get_agent_result** - Retrieve result from completed sessions

**Note**: All tools accept an optional `project_dir` parameter (must be absolute path) that allows per-tool override of the project directory. Only set when instructed to set a project dir!

For detailed tool parameters and examples, see [TOOLS_REFERENCE.md](./TOOLS_REFERENCE.md).

## Example Usage

Once configured, you can use natural language in Claude Desktop or Claude Code:

- "List all available orchestrated agents"
- "Start a new agent session called 'architect' with the system-architect agent and ask it to design a microservices architecture"
- "Show me all my agent sessions"
- "Resume the architect session and ask it to add security considerations"
- "Start an async agent session called 'researcher' to analyze the codebase"
- "Check the status of the researcher session"

## Quick Troubleshooting

### Tools Not Showing Up

1. Verify configuration file is valid JSON
2. Ensure Claude Desktop was completely restarted
3. Check all paths are absolute (not relative)
4. Verify `PATH` environment variable includes `uv` and `claude` binary locations
5. Test UV directly: `uv run /path/to/agent-orchestrator-mcp.py`

### Environment Variable Errors

If you see errors about missing environment variables:
- `AGENT_ORCHESTRATOR_COMMAND_PATH` must point to the **commands directory** containing Python scripts
- Verify `uv` is installed and accessible: `which uv`
- For PATH issues on macOS, try: `/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin`

For detailed environment variable documentation, see [README.md - Environment Variables Reference](./README.md#environment-variables-reference).

### UV or Python Errors

If you see import or dependency errors:
- Ensure Python >= 3.10: `python3 --version`
- Ensure UV is installed: `uv --version`
- UV will automatically install dependencies on first run
- Check internet connection for dependency downloads

### Enable Debug Logging

Add `"MCP_SERVER_DEBUG": "true"` to the `env` section of your configuration, then check:
```bash
cat agent-orchestrator-mcp-python/logs/mcp-server.log | jq '.'
```

For comprehensive debugging instructions, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).

## Next Steps

**For advanced configurations and integration scenarios**:
- See [SETUP_GUIDE.md](./SETUP_GUIDE.md) for different use cases (local, remote, hybrid)

**For complete reference**:
- [README.md](./README.md) - Overview and quick reference
- [TOOLS_REFERENCE.md](./TOOLS_REFERENCE.md) - Complete API documentation
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Debugging and common issues

**For architecture details**:
- [ARCHITECTURE.md](./ARCHITECTURE.md) - UV standalone implementation details

**To create custom agents**:
- Create agent definitions in `.agent-orchestrator/agents/` within your project
- Start orchestrating specialized agents for different tasks
- Use sessions to maintain context across multiple interactions
