# Quick Start Guide

## Prerequisites

1. Node.js >= 18
2. The `agent-orchestrator.sh` script installed and accessible
3. A project directory where you want to run orchestrated agents

## Installation

1. **Install dependencies**:
```bash
npm install
```

2. **Build the TypeScript code**:
```bash
npm run build
```

3. **Configure environment variables**:

Create a `.env` file or set environment variables:
```bash
export AGENT_ORCHESTRATOR_SCRIPT_PATH="/absolute/path/to/agent-orchestrator.sh"
export AGENT_ORCHESTRATOR_PROJECT_DIR="/path/to/your/project"
```

Or copy `.env.example` to `.env` and edit:
```bash
cp .env.example .env
# Edit .env with your paths
```

## Testing the Server

Test the server using the MCP Inspector:

```bash
# Make sure environment variables are set first!
export AGENT_ORCHESTRATOR_SCRIPT_PATH="/Users/ramon/Documents/Projects/ai/claude-dev-skills/agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh"
export AGENT_ORCHESTRATOR_PROJECT_DIR="/Users/ramon/Documents/Projects/ai/claude-dev-skills"

# Run the MCP Inspector
npx @modelcontextprotocol/inspector node dist/index.js
```

This will open a web interface where you can:
- See all available tools
- Test tool calls with different parameters
- View responses in real-time

## Using with Claude Desktop

1. **Find your Claude Desktop configuration file**:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. **Add the MCP server configuration**:

```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "node",
      "args": [
        "/absolute/path/to/agent-orchestrator-mcp-server/dist/index.js"
      ],
      "env": {
        "AGENT_ORCHESTRATOR_SCRIPT_PATH": "/absolute/path/to/agent-orchestrator.sh",
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/your/project"
      }
    }
  }
}
```

**Note**: For more control over session and agent storage locations, you can also set:
- `AGENT_ORCHESTRATOR_SESSIONS_DIR` - Custom path for session storage
- `AGENT_ORCHESTRATOR_AGENTS_DIR` - Custom path for agent definitions

**Replace the paths** with your actual absolute paths!

3. **Restart Claude Desktop**

4. **Verify the tools are available**:
   - In Claude Desktop, you should see the MCP icon
   - The server should show 5 tools available

## Available Tools

1. **list_agents** - Lists all available specialized agent definitions
2. **list_sessions** - Lists all active agent sessions
3. **start_agent** - Starts a new orchestrated agent session
4. **resume_agent** - Resumes an existing agent session
5. **clean_sessions** - Removes all agent sessions

## Example Usage

Once configured in Claude Desktop, you can use natural language:

- "List all available orchestrated agents"
- "Start a new agent session called 'architect' with the system-architect agent and ask it to design a microservices architecture"
- "Show me all my agent sessions"
- "Resume the architect session and ask it to add security considerations"
- "Clean all agent sessions"

## Troubleshooting

### Error: AGENT_ORCHESTRATOR_SCRIPT_PATH environment variable is required

**Solution**: Make sure you've set the `AGENT_ORCHESTRATOR_SCRIPT_PATH` environment variable with the absolute path to the `agent-orchestrator.sh` script.

### Error: Failed to execute script

**Possible causes**:
1. The script path is incorrect
2. The script is not executable (run `chmod +x /path/to/agent-orchestrator.sh`)
3. The project directory doesn't exist or environment variables are not configured correctly

### Tools not showing up in Claude Desktop

**Solutions**:
1. Check the Claude Desktop logs for errors
2. Verify the configuration file is valid JSON
3. Make sure you restarted Claude Desktop after adding the configuration
4. Check that all paths in the configuration are absolute (not relative)

## Development

**Watch mode** (auto-rebuild on changes):
```bash
npm run dev
```

**Clean build**:
```bash
npm run clean
npm run build
```

## Next Steps

- Create custom agent definitions in `.agent-orchestrator/agents/`
- Start orchestrating specialized agents for different tasks
- Use sessions to maintain context across multiple interactions

For more details, see [README.md](./README.md).
