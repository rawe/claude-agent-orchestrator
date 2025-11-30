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
- Agent Runtime (port 8765) - Session tracking
- Agent Registry (port 8767) - Agent blueprints
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

## Use Case 2: MCP Server

*(Coming soon)* - Use with Claude Desktop or other MCP-compatible clients.

See [interfaces/agent-orchestrator-mcp-server/README.md](../interfaces/agent-orchestrator-mcp-server/README.md) for current MCP setup.
