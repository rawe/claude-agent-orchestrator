# Getting Started

Quick setup guide for the Agent Orchestrator Framework.

## Prerequisites

- Claude Code CLI installed
- Docker (Desktop or Engine + Compose V2)
- Python 3.11+, [uv](https://docs.astral.sh/uv/)

## Architecture Overview

The framework has three layers:

1. **Backend Services** (Docker) - Agent Coordinator, Context Store, Dashboard
2. **Agent Runner** - Bridge that executes agent runs (runs in your project directory)
3. **Interface** - Plugin (Claude Code) or MCP Server (Claude Desktop)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Claude Code    │     │  Agent Coordinator  │     │ Agent Runner    │
│  or Claude      │────▶│    (Docker)     │────▶│ (your project)  │
│  Desktop        │     │    :8765        │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                                ┌─────────────────┐
                                                │  Claude Code    │
                                                │  Agent Session  │
                                                └─────────────────┘
```

---

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
- Agent Coordinator (port 8765) - Session tracking + Agent blueprints
- Context Store (port 8766) - Document storage
- Dashboard (port 3000) - Web UI

**3. Start the Agent Runner in your project directory:**
```bash
cd /path/to/your/project
/path/to/claude-agent-orchestrator/servers/agent-runner/agent-runner
```

The runner must run in the directory where you want agents to execute. It polls the Agent Coordinator for runs and spawns Claude Code sessions.

**4. Open the dashboard:**
```bash
make open
```

Verify the dashboard is running at http://localhost:3000. You should see the runner registered.

**5. Add plugins to Claude Code:**
- Start Claude Code in your project directory
- Open Claude Code settings
- Add a new marketplace pointing to your cloned directory
- Activate both plugins:
  - `orchestrator` - Agent session management (ao-* commands)
  - `context-store` - Document sharing (doc-* commands)
- Restart Claude Code

**6. Verify the orchestrator skill:**
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

**3. Start the backend services:**
```bash
make start-bg
```

This starts in the background:
- Agent Coordinator (port 8765) - Session tracking + Agent blueprints
- Context Store (port 8766) - Document storage
- Dashboard (port 3000) - Web UI

**4. Start the Agent Runner in your project directory:**
```bash
cd /path/to/your/project
/path/to/claude-agent-orchestrator/servers/agent-runner/agent-runner
```

> **Important:** The Agent Runner must run in the directory where you want agents to execute. Without the runner, agent runs will be queued but not executed.

**5. Open the dashboard:**
```bash
make open
```

Verify the dashboard is running at http://localhost:3000. You should see the runner registered.

**6. Start the MCP server (HTTP mode):**
```bash
make start-mcp-agent-orchestrator
```

This starts the Agent Orchestrator MCP server at `http://localhost:9500/mcp`

**7. Configure your MCP client:**

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
mcps/agent-orchestrator/.mcp-agent-orchestrator-http.json
```

Or configure your client to connect to: `http://localhost:9500/mcp`

**8. Restart your MCP client** (e.g., Claude Desktop) to pick up the new configuration.

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
make stop-mcp-agent-orchestrator
```

### Verify

- Dashboard at http://localhost:3000 shows active sessions and registered runner
- MCP server endpoint: http://localhost:9500/mcp

See [mcps/agent-orchestrator/README.md](../mcps/agent-orchestrator/README.md) for detailed MCP server documentation.

---

## Agent Runner

The Agent Runner is a critical component that bridges the Agent Coordinator with actual agent execution. It must be running for agents to execute.

### Starting the Runner

```bash
# Navigate to your project directory
cd /path/to/your/project

# Start the runner
/path/to/claude-agent-orchestrator/servers/agent-runner/agent-runner

# Or with options
./servers/agent-runner/agent-runner --coordinator-url http://localhost:8765 -v
```

### What It Does

1. Registers with Agent Coordinator
2. Polls for pending runs (start/resume sessions)
3. Executes runs as Claude Code sessions
4. Reports run status back to the Agent Coordinator

### Why Run in Project Directory?

The runner spawns Claude Code sessions in its current working directory. Running it in your project ensures agents have access to your codebase.

### Dashboard Integration

Once registered, the runner appears in the Dashboard. You can:
- See runner status and metadata
- View running runs
- Deregister runners remotely

See [servers/agent-runner/README.md](../servers/agent-runner/README.md) for detailed documentation.

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `make start-bg` | Start backend services (Docker) |
| `make stop` | Stop backend services |
| `make start-mcps` | Start all MCP servers |
| `make stop-mcps` | Stop all MCP servers |
| `make start-all` | Start everything |
| `make stop-all` | Stop everything |
| `make open` | Open Dashboard in browser |
| `./servers/agent-runner/agent-runner` | Start Agent Runner |
