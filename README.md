# Agent Orchestrator Framework (AOF)

A framework for building, running, and observing AI agents. Define agent blueprints, run them as managed sessions, and observe execution in real-time.

**Design principles:**
- **Provider-agnostic** — Executor layer abstracts the AI framework (Claude Code implemented, others pluggable)
- **Minimal setup** — Pre-built container images or local development scripts
- **Observable** — Dashboard for monitoring agent sessions and debugging

## What is the Agent Orchestrator Framework?

Infrastructure for building AI agent systems. It provides:

- **Agent Coordinator** — Manages sessions, queues agent runs, tracks state
- **Agent Runner** — Executes agents via pluggable executors (Claude Code implemented)
- **Context Store** — Document storage and sharing between agents
- **Dashboard** — Real-time monitoring and session management

Use it to prototype agent workflows, build multi-agent systems, or as a backend for agent-powered applications.

See [Architecture](./docs/ARCHITECTURE.md) for detailed component interactions and terminology.

## Quick Start

### Option A: Container Images (Recommended)

Requires only **Docker**.

1. Get a Claude Code OAuth token:
   ```bash
   claude setup-token
   ```

2. Create a `.env` file:
   ```bash
   CLAUDE_CODE_OAUTH_TOKEN=<your-token>
   ```

3. Create the config directory:
   ```bash
   mkdir -p config/agents
   ```

4. Start services:
   ```bash
   docker compose -f docker-compose.quickstart.yml up
   ```

5. Open http://localhost:3000

### Option B: Local Development

Requires **Claude Code CLI**, **Docker**, **Python ≥3.11** + **[uv](https://docs.astral.sh/uv/)**.

```bash
git clone <repo-url>
cd claude-agent-orchestrator
make start-all
```

Then start the Agent Runner in your project directory:

```bash
cd /path/to/your/project
/path/to/claude-agent-orchestrator/servers/agent-runner/agent-runner
```

Open http://localhost:3000

### Stopping Services

```bash
# Containers
docker compose -f docker-compose.quickstart.yml down

# Local development
make stop-all
```

## Repository Structure

```
├── README.md
├── Makefile                           # Build, run, deploy commands
├── docker-compose.yml                 # Full dev environment
├── docker-compose.quickstart.yml      # Minimal setup with pre-built images
│
├── docs/                              # Documentation
│   ├── ARCHITECTURE.md                # System architecture overview
│   ├── GETTING_STARTED.md             # Detailed setup guide
│   └── containers/                    # Container image documentation
│
├── servers/
│   ├── agent-coordinator/             # Session management, agent registry, SSE events
│   ├── agent-runner/                  # Polls coordinator, executes agent runs
│   │   ├── lib/agent_orchestrator_mcp/  # Embedded MCP server
│   │   └── executors/
│   │       └── claude-code/           # Claude Code executor (Agent SDK)
│   └── context-store/                 # Document storage server
│
├── mcps/                              # External MCP servers
│   ├── context-store/                 # Document management MCP
│   ├── neo4j/                         # Neo4j graph database MCP
│   ├── atlassian/                     # Jira + Confluence MCP
│   └── ado/                           # Azure DevOps MCP
│
├── apps/dashboard/                    # Web UI (React + Vite)
│
├── plugins/                           # Claude Code plugins
│   ├── orchestrator/                  # ao-* orchestration commands
│   └── context-store/                 # doc-* document commands
│
├── config/agents/                     # Agent blueprints
├── scripts/                           # Dev startup scripts
└── tests/                             # Integration tests
```

## MCP Servers

Optional MCP servers in `mcps/` extend agent capabilities (Neo4j, Atlassian, Azure DevOps, Context Store).

The **Agent Orchestrator MCP** is embedded in the Agent Runner and automatically available to running agents.

See [mcps/README.md](./mcps/README.md) for setup and configuration.

## Example Agents

The `config/agents/` directory contains example agent blueprints demonstrating various patterns: web research, Atlassian/ADO integration, knowledge management, browser automation, and more.

See [config/agents/README.md](./config/agents/README.md) for the full list.

## Context Store

Document storage server for sharing context between agents. Supports tagging, querying, and parent-child document relationships.

Optional **semantic search** enables finding documents by meaning (requires Ollama + Elasticsearch).

See [servers/context-store/README.md](./servers/context-store/README.md) for setup and API documentation.

## Service URLs

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:3000 |
| Agent Coordinator | http://localhost:8765 |
| Context Store | http://localhost:8766 |

## Testing

The framework includes an integration test suite for verifying Agent Coordinator and Agent Runner functionality. Tests can be run with either a deterministic test executor or the real Claude Code executor.

See [tests/README.md](./tests/README.md) for setup and test case documentation.

## Documentation

- **[Architecture](./docs/ARCHITECTURE.md)** - Full system architecture and component interactions
- **[Getting Started Guide](./docs/GETTING_STARTED.md)** - Detailed setup and configuration
- **[Docker Deployment](./DOCKER.md)** - Docker setup and configuration
- **[Documentation Index](./docs/README.md)** - All documentation topics
- **[Agent Runner](./servers/agent-runner/README.md)** - Run executor with embedded Agent Orchestrator MCP
- **[Context Store](./servers/context-store/README.md)** - Document storage server with semantic search
- **[MCP Servers Overview](./mcps/README.md)** - All available MCP servers
- **[Context Store MCP](./mcps/context-store/README.md)** - MCP server for document management
