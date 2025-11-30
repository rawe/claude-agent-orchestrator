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
- Create reusable agent definitions for common tasks
- Support for long-running and background tasks

## Two Usage Levels

AOF provides two distinct usage levels, allowing you to choose the integration approach that best fits your needs:

### Level 1: Claude Code Plugin

**Best for:** Direct integration within Claude Code with full control

Install the `orchestrator` plugin to get:
- Python-based `ao-*` commands for agent orchestration
- Slash commands for agent management
- Skills for creating and managing agents
- Complete control over agent lifecycle

**Quick Start:**
```bash
# Install the plugin by adding this repo to Claude Code
# The plugin provides the core framework
```

**Usage Example:**
```
/agent-orchestrator-init
Use the orchestrator skill to create a new session called "code-review"
```

**Documentation:** [plugins/orchestrator/README.md](./plugins/orchestrator/README.md)

---

### Level 2: MCP Server (Alternative for Claude Desktop)

**Best for:** Integration with AI assistants that only support MCP protocol (like Claude Desktop)

Use the standalone MCP server implementation to get:
- **No Claude Code plugin required!**
- Works with Claude Desktop, Claude Code, or any MCP-compatible system
- 5 MCP tools for agent orchestration
- Python implementation with automatic dependency management
- Works with the same Python commands as Level 1

**Requirements:** Python ≥3.10, [uv](https://docs.astral.sh/uv/getting-started/installation/)

**Quick Start:**
```bash
# 1. Clone this repository
git clone <your-repo-url>

# 2. Configure in Claude Desktop or Claude Code
# MCP server now auto-discovers commands - minimal setup required!
# See interfaces/agent-orchestrator-mcp-server/README.md
```

**Usage Example (from Claude Desktop):**
```
List available agents
Create a new agent session called "code-review" using the code-reviewer agent
```

**Documentation:** [interfaces/agent-orchestrator-mcp-server/README.md](./interfaces/agent-orchestrator-mcp-server/README.md)

**Important Limitation:**
Due to a [known bug in Claude Code](https://github.com/anthropics/claude-code/issues/3426#issuecomment-3522720980), **stdio MCP servers do not work when using the `-p` parameter (headless mode)**. Since the Agent Orchestrator Framework launches agents using headless Claude Code sessions, stdio-based MCP servers configured in Claude Desktop will not be accessible to orchestrated agents in Level 2 integration. This affects the `protocolVersion` field handling in initialization requests and causes 30-second timeouts during tool discovery. As a workaround, consider using SSE (Server-Sent Events) transport for MCP servers, or use Level 1 integration which operates within a single Claude Code session.

---

## Which Level Should You Use?

| Usage Level | Use When... | Installation | Integration |
|-------------|-------------|--------------|-------------|
| **Level 1** | You want direct control within Claude Code | Install plugins | Claude Code only |
| **Level 2** | You need to use with Claude Desktop or other MCP-only AI assistants | Configure MCP server | Any MCP system |

**Can you use multiple levels?** Yes! Level 2 (MCP) can be used independently or alongside Level 1 plugins.

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

### Agent Definitions
Markdown files that define specialized agent configurations with custom system prompts, instructions, and MCP configurations. Stored in `.agent-orchestrator/agents/`.

### Sessions
Isolated Claude Code sessions for individual agents. Each session has a unique ID and configuration. Session data is persisted in the Agent Runtime server (SQLite).

### MCP Configuration
Different agents can have different MCP server configurations, enabling specialized capabilities per agent type.

### Orchestration Commands
The Python-based `ao-*` commands (`ao-new`, `ao-resume`, `ao-status`, etc.) are the foundation of both usage levels. They handle session lifecycle, agent configuration, and result extraction.


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

## Documentation

- **[Getting Started](./docs/GETTING_STARTED.md)** - Quick setup guide
- **[Architecture](./docs/ARCHITECTURE.md)** - Full system architecture and component interactions
- **[Docker Deployment](./DOCKER.md)** - Docker setup and configuration
- **[Orchestrator Plugin](./plugins/orchestrator/README.md)** - Level 1: Claude Code plugin
- **[MCP Server](./interfaces/agent-orchestrator-mcp-server/README.md)** - Level 2: MCP implementation
- **[Context Store Plugin](./plugins/context-store/README.md)** - Document management plugin
