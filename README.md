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
make start-bg    # Starts Dashboard (:3000), Agent Runtime (:8765), Context Store (:8766)
```

**Requirements:** 

* Claude Code CLI
* Docker (Desktop or Engine + Compose V2)
* Python ≥3.10, [uv](https://docs.astral.sh/uv/)

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

- 7 MCP tools for agent orchestration + 7 MCP tools for document management
- Works with Claude Desktop, Claude Code, or any MCP system

**Setup:** Configure in Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "uv",
      "args": ["run", "/path/to/mcps/agent-orchestrator/agent-orchestrator-mcp.py"],
      "env": {
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/project",
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
      }
    },
    "context-store": {
      "command": "uv",
      "args": ["run", "/path/to/mcps/context-store/context-store-mcp.py"],
      "env": {
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

**Documentation:** [mcps/agent-orchestrator/README.md](./mcps/agent-orchestrator/README.md)

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
│   ├── agent-runtime/                 # Session management + event capture + agent registry
│   └── context-store/                 # Document storage
│
├── mcps/                              # MCP servers (agent capabilities)
│   ├── agent-orchestrator/            # Agent orchestration MCP (dual-purpose: capabilities + framework access)
│   ├── context-store/                 # Document management MCP
│   ├── atlassian/                     # Jira + Confluence MCP (Docker)
│   └── ado/                           # Azure DevOps MCP (Docker)
│
├── dashboard/                         # Web UI (React + Vite)
│
├── plugins/                           # Claude Code plugins
│   ├── orchestrator/                  # Agent orchestration commands
│   └── context-store/                 # Document management commands
│
└── config/                            # Configuration
    └── agents/                        # Agent blueprints
```

## MCP Servers (Agent Capabilities)

The `mcps/` directory contains MCP servers that provide capabilities to agents. These are the tools agents can use to interact with external services and the framework itself.

| MCP Server | Port | Purpose | Type |
|------------|------|---------|------|
| `agent-orchestrator` | 9500 | Agent orchestration tools + framework access for any MCP-capable AI | Internal |
| `context-store` | 9501 | Document storage and retrieval | Internal |
| `atlassian` | 9000 | Jira + Confluence integration | External (Docker) |
| `ado` | 9001 | Azure DevOps work items | External (Docker) |

**Start all MCP servers:**
```bash
make start-mcps
```

**Start individually:**
```bash
make start-mcp-agent-orchestrator  # Our orchestration framework
make start-mcp-context-store       # Document management
make start-mcp-atlassian           # Requires mcps/atlassian/.env
make start-mcp-ado                 # Requires mcps/ado/.env
```

The **Agent Orchestrator MCP** has a dual purpose:
1. Provides agent orchestration capabilities to orchestrated agents
2. Exposes the framework to any MCP-compatible AI client (Claude Desktop, etc.)

See `mcps/README.md` for detailed setup.

## Example Agents

The `config/agents/` folder contains example agent blueprints.

| Agent | Purpose | MCP Dependency |
|-------|---------|----------------|
| `atlassian-agent` | Jira & Confluence CRUD | Atlassian MCP |
| `confluence-researcher` | Confluence research (CQL) | Atlassian MCP |
| `ado-agent` | Azure DevOps work items | ADO MCP |
| `ado-researcher` | ADO research | ADO MCP |
| `web-researcher` | Web research | None (built-in) |
| `browser-tester` | Playwright automation | Playwright (npx) |

## Quick Start

See **[Getting Started](./docs/GETTING_STARTED.md)** for setup instructions.

## Agent Launcher

The Agent Launcher is a critical component that bridges the Agent Runtime with actual agent execution. It polls for jobs and spawns Claude Code sessions.

**Start the launcher in your project directory:**
```bash
cd /path/to/your/project
/path/to/claude-agent-orchestrator/servers/agent-launcher/agent-launcher
```

> **Important:** The launcher must run in the directory where you want agents to execute. Without a running launcher, agent sessions will be queued but not executed.

The launcher:
- Registers with Agent Runtime and appears in the Dashboard
- Polls for pending jobs (start/resume sessions)
- Executes jobs as Claude Code sessions
- Reports job status back to the runtime

Currently implements **Claude Code** as the agent backend. The architecture supports adding other backends in the future.

See [servers/agent-launcher/README.md](./servers/agent-launcher/README.md) for detailed documentation.

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
| Agent Runtime | http://localhost:8765 | Session management, WebSocket events, Blueprint API |
| Context Store | http://localhost:8766 | Document storage API |

See **[DOCKER.md](./DOCKER.md)** for deployment details and **[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)** for full architecture.

## Glossary

| Term | Definition |
|------|------------|
| **Agent Blueprint** | A reusable configuration that defines specialized agent behavior, including system prompts, MCP server configs, and capability descriptions. Managed by the Agent Runtime. |
| **Session** | A named, persistent Claude Code conversation. Sessions can be created, resumed, and monitored via the `ao-*` commands. |
| **Agent Runtime** | Backend server (port 8765) that manages session lifecycle, queues jobs, captures events, and stores agent blueprints. |
| **Agent Launcher** | Standalone process that polls Agent Runtime for jobs and executes them as Claude Code sessions. Must run in your project directory. |
| **Context Store** | Backend server (port 8766) for document storage and retrieval with tag-based querying. |
| **Dashboard** | React web UI (port 3000) for monitoring sessions, managing blueprints, and browsing documents. |

## Testing

The framework includes an integration test suite for verifying Agent Runtime and Agent Launcher functionality. Tests can be run with either a deterministic test executor or the real Claude Code executor.

See **[tests/README.md](./tests/README.md)** for setup and test case documentation.

## Documentation

- **[Getting Started](./docs/GETTING_STARTED.md)** - Quick setup guide
- **[Architecture](./docs/ARCHITECTURE.md)** - Full system architecture and component interactions
- **[Docker Deployment](./DOCKER.md)** - Docker setup and configuration
- **[Agent Launcher](./servers/agent-launcher/README.md)** - Job execution bridge
- **[Orchestrator Plugin](./plugins/orchestrator/README.md)** - Option 1: Claude Code plugin
- **[Agent Orchestrator MCP](./mcps/agent-orchestrator/README.md)** - Option 2: MCP server for agent orchestration
- **[Context Store MCP](./mcps/context-store/README.md)** - MCP server for document management
- **[MCP Servers Overview](./mcps/README.md)** - All available MCP servers
- **[Context Store Plugin](./plugins/context-store/README.md)** - Document management plugin
