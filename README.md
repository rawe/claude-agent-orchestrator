# Agent Orchestrator Framework (AOF)

A comprehensive framework for orchestrating specialized Claude Code agent sessions.

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

## Quick Start

### Requirements

- **Claude Code CLI** - installed and authenticated
- **Docker** - Desktop or Engine + Compose V2
- **Python ≥3.11** + **[uv](https://docs.astral.sh/uv/)**

### 1. Clone and Start Services

```bash
git clone <repo-url>
cd claude-agent-orchestrator
make start-all
```

This starts:
- **Dashboard** at http://localhost:3000
- **Agent Runtime** at http://localhost:8765
- **Context Store** at http://localhost:8766
- **Neo4j** at http://localhost:7475
- **MCP Servers** (Agent Orchestrator, Context Store, Neo4j)

> **Note:** Atlassian and Azure DevOps MCPs require credentials in `.env` files and will be skipped if not configured. See [mcps/README.md](./mcps/README.md) for setup.

### 2. Start the Agent Launcher

The Agent Launcher executes agent jobs. Run it in your **project directory** (where agents should work):

```bash
cd /path/to/your/project
/path/to/claude-agent-orchestrator/servers/agent-launcher/agent-launcher
```

The launcher connects to Agent Runtime and waits for jobs. Keep it running while using the framework.

### 3. Open the Dashboard

```bash
make open
# Or manually: open http://localhost:3000
```

From the Dashboard you can:
- Create and manage agent sessions
- Monitor agent execution in real-time
- Browse and edit agent blueprints
- Manage documents in the Context Store

### Stopping Everything

```bash
make stop-all    # Stop all services
# Ctrl+C         # Stop the agent launcher
```

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
│   ├── agent-launcher/                # Job executor (polls runtime, runs Claude Code)
│   └── context-store/                 # Document storage
│
├── mcps/                              # MCP servers (agent capabilities)
│   ├── agent-orchestrator/            # Agent orchestration MCP (dual-purpose: capabilities + framework access)
│   ├── context-store/                 # Document management MCP
│   ├── neo4j/                         # Neo4j graph database MCP (Docker)
│   ├── atlassian/                     # Jira + Confluence MCP (Docker, requires credentials)
│   └── ado/                           # Azure DevOps MCP (Docker, requires credentials)
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

| MCP Server | Port | Purpose | Requires .env |
|------------|------|---------|---------------|
| `agent-orchestrator` | 9500 | Agent orchestration tools + framework access | No |
| `context-store` | 9501 | Document storage and retrieval | No |
| `neo4j` | 9003 | Neo4j graph database queries | No (has defaults) |
| `atlassian` | 9000 | Jira + Confluence integration | Yes |
| `ado` | 9001 | Azure DevOps work items | Yes |

**Start all MCP servers:**
```bash
make start-mcps
```

**Start individually:**
```bash
make start-mcp-agent-orchestrator  # Agent orchestration
make start-mcp-context-store       # Document management
make start-mcp-neo4j               # Neo4j queries (uses defaults)
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

## Core Concepts

### Agent Blueprints
Reusable configurations that define specialized agent behavior. Each blueprint can include a custom system prompt, instructions, and MCP server configurations. Managed via the Agent Registry server or stored in `.agent-orchestrator/agents/`.

### Sessions
Isolated Claude Code sessions for individual agents. Each session has a unique ID and configuration. Session data is persisted in the Agent Runtime server (SQLite).

### MCP Configuration
Different agents can have different MCP server configurations, enabling specialized capabilities per agent type.

### Orchestration Commands
The Python-based `ao-*` commands (`ao-start`, `ao-resume`, `ao-status`, etc.) are the foundation of both usage levels. They handle session lifecycle, agent configuration, and result extraction.


## Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Dashboard | http://localhost:3000 | Web UI for agents, sessions, documents |
| Agent Runtime | http://localhost:8765 | Session management, WebSocket events, Blueprint API |
| Context Store | http://localhost:8766 | Document storage API |
| Neo4j Browser | http://localhost:7475 | Graph database UI (neo4j/agent-orchestrator) |

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

- **[Architecture](./docs/ARCHITECTURE.md)** - Full system architecture and component interactions
- **[Getting Started Guide](./docs/GETTING_STARTED.md)** - Detailed setup and configuration
- **[Docker Deployment](./DOCKER.md)** - Docker setup and configuration
- **[Agent Launcher](./servers/agent-launcher/README.md)** - Job execution bridge details
- **[MCP Servers Overview](./mcps/README.md)** - All available MCP servers
- **[Agent Orchestrator MCP](./mcps/agent-orchestrator/README.md)** - MCP server for agent orchestration
- **[Context Store MCP](./mcps/context-store/README.md)** - MCP server for document management
