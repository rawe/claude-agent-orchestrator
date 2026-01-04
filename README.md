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
- **Agent Coordinator** at http://localhost:8765
- **Context Store** at http://localhost:8766
- **Neo4j** at http://localhost:7475
- **MCP Servers** (Agent Orchestrator, Context Store, Neo4j)

> **Note:** Atlassian and Azure DevOps MCPs require credentials in `.env` files and will be skipped if not configured. See [mcps/README.md](./mcps/README.md) for setup.

### 2. Start the Agent Runner

The Agent Runner executes agent runs. Run it in your **project directory** (where agents should work):

```bash
cd /path/to/your/project
/path/to/claude-agent-orchestrator/servers/agent-runner/agent-runner
```

The runner connects to Agent Coordinator and waits for runs. Keep it running while using the framework.

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
# Ctrl+C         # Stop the agent runner
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
│   └── agent-coordinator/             # Agent Coordinator server docs
│
├── servers/                           # Backend servers
│   ├── agent-coordinator/             # Session management + event capture + agent registry
│   ├── agent-runner/                  # Run executor (polls coordinator, runs Claude Code)
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
| `agent-orchestrator` | embedded in Agent Runner | Agent orchestration tools + framework access | No |
| `context-store` | 9501 | Document storage and retrieval | No |
| `neo4j` | 9003 | Neo4j graph database queries | No (has defaults) |
| `atlassian` | 9000 | Jira + Confluence integration | Yes |
| `ado` | 9001 | Azure DevOps work items | Yes |

**Start MCP servers:**
```bash
make start-mcps                    # Start all external MCP servers
make start-mcp-context-store       # Document management
make start-mcp-neo4j               # Neo4j queries (uses defaults)
make start-mcp-atlassian           # Requires mcps/atlassian/.env
make start-mcp-ado                 # Requires mcps/ado/.env
```

The **Agent Orchestrator MCP** is embedded in the Agent Runner:
- When running agents via the framework, the MCP server is automatically available
- Agent configurations use `${AGENT_ORCHESTRATOR_MCP_URL}` placeholder (dynamically replaced)
- For external clients (Claude Desktop), start the runner with `--mcp-port 9500` to expose a fixed endpoint

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

## Context Store

The Context Store server provides document storage and retrieval for sharing context between agents and sessions. Documents can be tagged, queried, and organized with parent-child relationships.

**Optional: Semantic Search** - Search documents by meaning using vector embeddings. Requires [Ollama](https://ollama.com/) running locally with an embedding model. See [Context Store README](./servers/context-store/README.md) for setup instructions.

## Core Concepts

### Agent Blueprints
Reusable configurations that define specialized agent behavior. Each blueprint can include a custom system prompt, instructions, and MCP server configurations. Managed via the Agent Registry server or stored in `.agent-orchestrator/agents/`.

### Sessions
Isolated Claude Code sessions for individual agents. Each session has a unique ID and configuration. Session data is persisted in the Agent Coordinator server (SQLite).

### MCP Configuration
Different agents can have different MCP server configurations, enabling specialized capabilities per agent type.

### Orchestration Commands
The Python-based `ao-*` commands (`ao-start`, `ao-resume`, `ao-status`, etc.) are the foundation of both usage levels. They handle session lifecycle, agent configuration, and result extraction.


## Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Dashboard | http://localhost:3000 | Web UI for agents, sessions, documents |
| Agent Coordinator | http://localhost:8765 | Session management, SSE events, Blueprint API |
| Context Store | http://localhost:8766 | Document storage API |
| Neo4j Browser | http://localhost:7475 | Graph database UI (neo4j/agent-orchestrator) |

See **[DOCKER.md](./DOCKER.md)** for deployment details and **[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)** for full architecture.

## Glossary

| Term | Definition |
|------|------------|
| **Agent Blueprint** | Reusable agent configuration (system prompt, MCP config, metadata) that gets instantiated into sessions. |
| **Session** | Named, persistent Claude Code conversation with state and history. Can have multiple runs. |
| **Agent Run** | Single execution of a session (start, resume, or stop). Transient work unit queued for a runner. |
| **Agent Coordinator** | Backend server (port 8765) managing sessions, runs, runners, blueprints, and callbacks. |
| **Agent Runner** | Standalone process that polls for runs and executes them. Must run in your project directory. |
| **Context Store** | Backend server (port 8766) for document storage and sharing context between agents. |
| **Dashboard** | Web UI (port 3000) for monitoring sessions, managing blueprints, and browsing documents. |

See **[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md#core-terminology)** for the complete terminology and conceptual hierarchy.

## Testing

The framework includes an integration test suite for verifying Agent Coordinator and Agent Runner functionality. Tests can be run with either a deterministic test executor or the real Claude Code executor.

See **[tests/README.md](./tests/README.md)** for setup and test case documentation.

## Documentation

- **[Architecture](./docs/ARCHITECTURE.md)** - Full system architecture and component interactions
- **[Getting Started Guide](./docs/GETTING_STARTED.md)** - Detailed setup and configuration
- **[Docker Deployment](./DOCKER.md)** - Docker setup and configuration
- **[Agent Runner](./servers/agent-runner/README.md)** - Run executor with embedded Agent Orchestrator MCP
- **[Context Store](./servers/context-store/README.md)** - Document storage server with semantic search
- **[MCP Servers Overview](./mcps/README.md)** - All available MCP servers
- **[Context Store MCP](./mcps/context-store/README.md)** - MCP server for document management
