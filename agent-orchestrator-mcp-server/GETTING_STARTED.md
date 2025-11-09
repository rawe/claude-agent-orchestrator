# Getting Started

Get the Agent Orchestrator MCP Server up and running quickly with this guide.

## Prerequisites

1. Node.js >= 18
2. The `agent-orchestrator.sh` script installed and accessible
3. A project directory where you want to run orchestrated agents

## Installation

1. **Install dependencies**:
```bash
cd agent-orchestrator-mcp-server
npm install
```

2. **Build the TypeScript code**:
```bash
npm run build
```

3. **Verify build output**:

The build creates a `dist/` folder with the compiled MCP server:
```
agent-orchestrator-mcp-server/dist/index.js
```

This is the entry point you'll reference in your MCP configuration.

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
      "command": "node",
      "args": [
        "/absolute/path/to/agent-orchestrator-mcp-server/dist/index.js"
      ],
      "env": {
        "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin",
        "AGENT_ORCHESTRATOR_SCRIPT_PATH": "/absolute/path/to/agent-orchestrator.sh",
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/your/project"
      }
    }
  }
}
```

**Important**:
- Replace all paths with your actual absolute paths
- `PATH` must include the directory containing your `node` binary (required for Claude Desktop)
- See [README.md - Environment Variables Reference](./README.md#environment-variables-reference) for details on all variables

### 3. Restart Claude Desktop

Completely quit and restart Claude Desktop for the changes to take effect.

### 4. Verify It Works

After restart:
- Look for the MCP icon in Claude Desktop
- The server should show **5 tools available**
- Try: "List all available orchestrated agents"

## Testing with MCP Inspector (Optional)

Test the server locally before integrating with Claude Desktop:

```bash
# Set environment variables
export AGENT_ORCHESTRATOR_SCRIPT_PATH="/absolute/path/to/agent-orchestrator.sh"
export AGENT_ORCHESTRATOR_PROJECT_DIR="/path/to/your/project"

# Run MCP Inspector
npx @modelcontextprotocol/inspector node dist/index.js
```

This opens a web interface where you can:
- See all 5 available tools
- Test tool calls with different parameters
- View responses in real-time

## Available Tools

The MCP server provides 5 tools:

1. **list_agents** - Lists all available specialized agent definitions
2. **list_sessions** - Lists all active agent sessions
3. **start_agent** - Starts a new orchestrated agent session
4. **resume_agent** - Resumes an existing agent session
5. **clean_sessions** - Removes all agent sessions

For detailed tool parameters and examples, see [README.md - Tools Reference](./README.md#tools-reference).

## Example Usage

Once configured, you can use natural language in Claude Desktop:

- "List all available orchestrated agents"
- "Start a new agent session called 'architect' with the system-architect agent and ask it to design a microservices architecture"
- "Show me all my agent sessions"
- "Resume the architect session and ask it to add security considerations"

## Quick Troubleshooting

### Tools Not Showing Up

1. Verify configuration file is valid JSON
2. Ensure Claude Desktop was completely restarted
3. Check all paths are absolute (not relative)
4. Verify `PATH` environment variable includes `node` binary location

### Environment Variable Errors

If you see errors about missing environment variables:
- `AGENT_ORCHESTRATOR_SCRIPT_PATH` must point to the **agent-orchestrator.sh** bash script
- For PATH issues on macOS, try: `/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin`

For detailed environment variable documentation, see [README.md - Environment Variables Reference](./README.md#environment-variables-reference).

### Enable Debug Logging

Add `"MCP_SERVER_DEBUG": "true"` to the `env` section of your configuration, then check:
```bash
cat agent-orchestrator-mcp-server/logs/mcp-server.log | jq '.'
```

For comprehensive debugging instructions, see [README.md - Debugging and Troubleshooting](./README.md#debugging-and-troubleshooting).

## Next Steps

**For Claude Code integration and advanced configurations**:
- See [SETUP_GUIDE.md](./SETUP_GUIDE.md) for different use cases (local, remote, hybrid)

**For complete reference**:
- [README.md](./README.md) - Full documentation, API reference, and environment variables

**To create custom agents**:
- Create agent definitions in `.agent-orchestrator/agents/` within your project
- Start orchestrating specialized agents for different tasks
- Use sessions to maintain context across multiple interactions
