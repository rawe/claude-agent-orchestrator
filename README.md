# Agent Orchestrator Framework (AOF)

A comprehensive framework for orchestrating specialized Claude Code agent sessions with multiple usage levels and integration approaches.

## What is the Agent Orchestrator Framework?

The Agent Orchestrator Framework (AOF) enables you to create, manage, and orchestrate specialized Claude Code agent sessions programmatically. Whether you want to delegate tasks to specialized agents, run long-running background processes, or manage multiple concurrent AI workflows, AOF provides the tools and abstractions you need.

**Key Capabilities:**
- Launch specialized Claude Code agent sessions programmatically
- Configure agents with custom system prompts and instructions
- Manage multiple concurrent agent sessions
- Inject different MCP server configurations per agent
- Extract and process results from completed agents
- Create reusable agent blueprints for common tasks
- Support for long-running and background tasks

## Prerequisites

Both integration options require the backend services running. The plugins and MCP server are thin HTTP clients.

```bash
git clone <your-repo-url>
cd claude-agent-orchestrator
make start-bg    # Starts Dashboard (:3000), Agent Runtime (:8765), Agent Registry (:8767), Context Store (:8766)
```

**Requirements:** 

* Claude Code CLI
* Docker (Desktop or Engine + Compose V2)
* Python ≥3.10, [uv](https://docs.astral.sh/uv/) (only for integration option 1)

## Two Integration Options

### Option 1: Claude Code Plugin

**Best for:** Direct integration within Claude Code with full control

- Python-based `ao-*` commands for agent orchestration
- Slash commands for agent management
- Skills for creating and managing agents

**Setup:** Add this repository as a marketplace in Claude Code `/plugin` settings (use the path to the checked out repo), activate `orchestrator` plugin, restart.

**Usage:**
```
/agent-orchestrator-init
Use the orchestrator skill to create a new session called "code-review"
```

**Documentation:** [plugins/orchestrator/README.md](./plugins/orchestrator/README.md)

---

### Option 2: MCP Server

**Best for:** Claude Desktop or other MCP-compatible clients

- 7 MCP tools for agent orchestration
- Works with Claude Desktop, Claude Code, or any MCP system

**Setup:** Configure in Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "uv",
      "args": ["run", "/path/to/interfaces/agent-orchestrator-mcp-server/agent-orchestrator-mcp.py"],
      "env": {
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/project",
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
      }
    }
  }
}
```

**Usage Example (from Claude Desktop):**
```
List available agents
Create a new agent session called "code-review" using the code-reviewer agent
```

**Documentation:** [interfaces/agent-orchestrator-mcp-server/README.md](./interfaces/agent-orchestrator-mcp-server/README.md)

**Limitation:** Due to a [known Claude Code bug](https://github.com/anthropics/claude-code/issues/3426), stdio MCP servers don't work in headless mode (`-p`). Orchestrated agents won't have access to stdio-based MCP servers. Use SSE transport or Option 1 as workaround.

---

## Which Option Should You Use?

| Option | Use When... | Integration |
|--------|-------------|-------------|
| **Option 1: Plugin** | You work within Claude Code | Claude Code only |
| **Option 2: MCP** | You use Claude Desktop or other MCP clients | Any MCP system |

Both options can be used together.

## Repository Structure

```
agent-orchestrator-framework/
│
├── README.md                          # This file
├── Makefile                           # Build, run, deploy commands
├── docker-compose.yml                 # Container orchestration
│
├── docs/                              # Documentation
│   ├── ARCHITECTURE.md                # System architecture overview
│   └── agent-runtime/                 # Agent Runtime server docs
│
├── servers/                           # Backend servers
│   ├── agent-runtime/                 # Session management + event capture
│   ├── agent-registry/                # Blueprint management (CRUD)
│   └── context-store/                 # Document storage
│
├── interfaces/
│   └── agent-orchestrator-mcp-server/ # MCP protocol interface
│
├── dashboard/                         # Web UI (React + Vite)
│
└── plugins/                           # Claude Code plugins
    ├── orchestrator/                  # Agent orchestration commands
    │   └── skills/orchestrator/
    │       └── commands/              # ao-* commands
    │
    └── context-store/                 # Document management commands
        └── skills/context-store/
            └── commands/              # doc-* commands
```

## Quick Start

See **[Getting Started](./docs/GETTING_STARTED.md)** for setup instructions.

## Core Concepts

### Agent Blueprints
Reusable configurations that define specialized agent behavior. Each blueprint can include a custom system prompt, instructions, and MCP server configurations. Managed via the Agent Registry server or stored in `.agent-orchestrator/agents/`.

### Sessions
Isolated Claude Code sessions for individual agents. Each session has a unique ID and configuration. Session data is persisted in the Agent Runtime server (SQLite).

### MCP Configuration
Different agents can have different MCP server configurations, enabling specialized capabilities per agent type.

### Orchestration Commands
The Python-based `ao-*` commands (`ao-start`, `ao-resume`, `ao-status`, etc.) are the foundation of both usage levels. They handle session lifecycle, agent configuration, and result extraction.


## Dashboard & Observability

Monitor your agent orchestration in real-time with the unified Dashboard:

- **Real-time monitoring** of agent sessions and tool calls
- **WebSocket-based** live updates
- **Docker support** for one-command deployment
- **Agent blueprint management** via web UI
- **Document management** for context sharing

**Quick Start:**
```bash
# Start all services (Dashboard + all backend servers)
make start-bg

# Open http://localhost:3000
make open
```

**Service URLs:**
| Service | URL | Purpose |
|---------|-----|---------|
| Dashboard | http://localhost:3000 | Web UI for agents, sessions, documents |
| Agent Runtime | http://localhost:8765 | Session management, WebSocket events |
| Agent Registry | http://localhost:8767 | Blueprint CRUD API |
| Context Store | http://localhost:8766 | Document storage API |

See **[DOCKER.md](./DOCKER.md)** for deployment details and **[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)** for full architecture.

## Glossary

| Term | Definition |
|------|------------|
| **Agent Blueprint** | A reusable configuration that defines specialized agent behavior, including system prompts, MCP server configs, and capability descriptions. Managed by the Agent Registry. |
| **Session** | A named, persistent Claude Code conversation. Sessions can be created, resumed, and monitored via the `ao-*` commands. |
| **Agent Runtime** | Backend server (port 8765) that manages session lifecycle, spawns agents, and captures events. |
| **Agent Registry** | Backend server (port 8767) that stores and serves agent blueprints via REST API. |
| **Context Store** | Backend server (port 8766) for document storage and retrieval with tag-based querying. |
| **Dashboard** | React web UI (port 3000) for monitoring sessions, managing blueprints, and browsing documents. |

## Documentation

- **[Getting Started](./docs/GETTING_STARTED.md)** - Quick setup guide
- **[Architecture](./docs/ARCHITECTURE.md)** - Full system architecture and component interactions
- **[Docker Deployment](./DOCKER.md)** - Docker setup and configuration
- **[Orchestrator Plugin](./plugins/orchestrator/README.md)** - Option 1: Claude Code plugin
- **[MCP Server](./interfaces/agent-orchestrator-mcp-server/README.md)** - Option 2: MCP implementation
- **[Context Store Plugin](./plugins/context-store/README.md)** - Document management plugin
