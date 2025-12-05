# Getting Started

Quick setup guide for the Agent Orchestrator Framework.

## Use Case 1: Claude Code Plugin

Use the orchestrator directly within Claude Code via plugins.

### Setup

**1. Clone the repository:**
```bash
git clone https://github.com/your-org/claude-agent-orchestrator.git
cd claude-agent-orchestrator
```

**2. Start the backend services:**
```bash
make start-bg
```

This starts in the background:
- Agent Runtime (port 8765) - Session tracking + Agent blueprints
- Context Store (port 8766) - Document storage
- Dashboard (port 3000) - Web UI

**3. Open the dashboard:**
```bash
make open
```

Verify the dashboard is running at http://localhost:3000

**4. Add plugins to Claude Code:**
- Start Claude Code in your project directory
- Open Claude Code settings
- Add a new marketplace pointing to your cloned directory
- Activate both plugins:
  - `orchestrator` - Agent session management (ao-* commands)
  - `context-store` - Document sharing (doc-* commands)
- Restart Claude Code

**5. Verify the orchestrator skill:**
```
/agent-orchestrator-init
```

This confirms the orchestrator skill is loaded and ready.

### Usage

Ask Claude Code to spawn an agent:

```
Start a math agent to calculate 1+1 in the background
```

Claude Code will use the orchestrator skill to create a new agent session.

### Verify

- Dashboard at http://localhost:3000 shows active sessions
- Use `ao-list-sessions` to see sessions from CLI
- Use `ao-status <session-name>` to check progress

---

## Use Case 2: MCP Server (HTTP Mode)

Use the orchestrator with Claude Desktop or other MCP-compatible clients via HTTP.

### Setup

**1. Clone the repository:**
```bash
git clone https://github.com/your-org/claude-agent-orchestrator.git
cd claude-agent-orchestrator
```

**2. Configure environment variables:**
```bash
cp .env.template .env
```

Edit `.env` and set the project directory for your agents:
```bash
# Required: Set the default project directory for agent sessions
AGENT_ORCHESTRATOR_PROJECT_DIR=/path/to/your/project

# Optional: Customize port (default: 9500)
# AGENT_ORCHESTRATOR_MCP_PORT=9500
```

> **Important:** In HTTP mode, the MCP server runs standalone, so `AGENT_ORCHESTRATOR_PROJECT_DIR` must be set to tell agents which project to work in.

**3. Start the backend services:**
```bash
make start-bg
```

This starts in the background:
- Agent Runtime (port 8765) - Session tracking + Agent blueprints
- Context Store (port 8766) - Document storage
- Dashboard (port 3000) - Web UI

**4. Open the dashboard:**
```bash
make open
```

Verify the dashboard is running at http://localhost:3000

**5. Start the MCP server (HTTP mode):**
```bash
make start-ao-mcp
```

This starts the Agent Orchestrator MCP server at `http://localhost:9500/mcp`

**6. Configure your MCP client:**

**Option A: Claude Desktop**

Add to your Claude Desktop config file:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "type": "http",
      "url": "http://localhost:9500/mcp"
    }
  }
}
```

**Option B: Other MCP clients**

Use the provided config file:
```
interfaces/agent-orchestrator-mcp-server/.mcp-agent-orchestrator-http.json
```

Or configure your client to connect to: `http://localhost:9500/mcp`

**7. Restart your MCP client** (e.g., Claude Desktop) to pick up the new configuration.

### Usage

In Claude Desktop, you can now use the orchestrator tools:

```
List available agent blueprints
```

```
Start a new agent session called "my-task" to analyze the codebase
```

### Available Tools

| Tool | Description |
|------|-------------|
| `list_agent_blueprints` | List available agent configurations |
| `list_agent_sessions` | List all agent sessions |
| `start_agent_session` | Start a new agent session |
| `resume_agent_session` | Continue an existing session |
| `get_agent_session_status` | Check session status |
| `get_agent_session_result` | Get result from completed session |
| `delete_all_agent_sessions` | Clean up all sessions |

### Stopping the Server

```bash
make stop-ao-mcp
```

### Verify

- Dashboard at http://localhost:3000 shows active sessions
- MCP server endpoint: http://localhost:9500/mcp

See [interfaces/agent-orchestrator-mcp-server/README.md](../interfaces/agent-orchestrator-mcp-server/README.md) for detailed MCP server documentation.
