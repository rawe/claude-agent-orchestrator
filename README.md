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

## Three Usage Levels

AOF provides three distinct usage levels, allowing you to choose the integration approach that best fits your needs:

### Level 1: Claude Code Plugin (Core Framework)

**Best for:** Direct, low-level control of agent orchestration within Claude Code

Install the `agent-orchestrator` plugin to get:
- Python-based `ao-*` commands for agent orchestration
- 4 slash commands for agent management
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
Use the agent-orchestrator skill to create a new session called "code-review"
```

**Documentation:** [agent-orchestrator/README.md](./agent-orchestrator/README.md)

---

### Level 2: Claude Code Plugin + Subagents Extension

**Best for:** Simplified, delegation-based workflow with pre-configured subagents

Install both the `agent-orchestrator` plugin AND the `agent-orchestrator-subagents` extension to get:
- All Level 1 capabilities
- Pre-configured Claude Code subagents for common tasks
- Natural language delegation interface
- Automatic session management

**Quick Start:**
```bash
# Install both plugins:
# 1. agent-orchestrator (core framework)
# 2. agent-orchestrator-subagents (extension)
```

**Usage Example:**
```
Use the orchestrated-agent-launcher subagent to create a new code review session
```

**Documentation:**
- [agent-orchestrator-subagents/README.md](./agent-orchestrator-subagents/README.md)
- [agent-orchestrator/README.md](./agent-orchestrator/README.md)

---

### Level 3: MCP Server (Protocol Abstraction)

**Best for:** Integration with any MCP-compatible AI system (Claude Desktop, other AI tools)

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
cd agent-orchestrator-mcp-server
# See README.md for configuration examples
```

**Usage Example (from Claude Desktop):**
```
List available agents
Create a new agent session called "code-review" using the code-reviewer agent
```

**Documentation:** [agent-orchestrator-mcp-server/README.md](./agent-orchestrator-mcp-server/README.md)

**Important Limitation:**
Due to a [known bug in Claude Code](https://github.com/anthropics/claude-code/issues/3426#issuecomment-3522720980), **stdio MCP servers do not work when using the `-p` parameter (headless mode)**. Since the Agent Orchestrator Framework launches agents using headless Claude Code sessions, stdio-based MCP servers configured in Claude Desktop will not be accessible to orchestrated agents in Level 3 integration. This affects the `protocolVersion` field handling in initialization requests and causes 30-second timeouts during tool discovery. As a workaround, consider using SSE (Server-Sent Events) transport for MCP servers, or use Level 1/2 integration approaches which operate within a single Claude Code session.

---

## Which Level Should You Use?

| Usage Level | Use When... | Installation | Integration |
|-------------|-------------|--------------|-------------|
| **Level 1** | You want direct control within Claude Code | Install plugin | Claude Code only |
| **Level 2** | You want simplified delegation workflow | Install 2 plugins | Claude Code only |
| **Level 3** | You want to use with Claude Desktop or other AI systems | Build & configure MCP | Any MCP system |

**Can you use multiple levels?** Yes! Level 3 (MCP) can be used independently or alongside Level 1/2 plugins.

## Repository Structure

```
agent-orchestrator-framework/
├── agent-orchestrator/              # Level 1: Core framework plugin
│   ├── skills/
│   │   └── agent-orchestrator/
│   │       ├── commands/                # Python ao-* commands
│   │       ├── SKILL.md                 # Skill definition
│   │       ├── references/              # Technical documentation
│   │       └── example/                 # Example agent definitions
│   ├── commands/                    # Slash commands
│   └── README.md
│
├── agent-orchestrator-subagents/    # Level 2: Subagents extension plugin
│   ├── agents/
│   │   ├── orchestrated-agent-launcher.md
│   │   └── orchestrated-agent-lister.md
│   └── README.md
│
├── agent-orchestrator-mcp-server/   # Level 3: MCP server implementation
│   ├── agent-orchestrator-mcp.py   # Main MCP server script
│   ├── libs/                        # Supporting libraries
│   ├── docs/                        # Documentation
│   └── README.md                    # Full documentation
│
├── agent-orchestrator-observability/ # Real-time observability platform
│   ├── backend/                     # FastAPI + WebSocket backend
│   ├── frontend/                    # React-based web UI
│   ├── hooks/                       # Hook scripts for event capture
│   ├── docker/                      # Docker setup
│   └── README.md                    # Full documentation
│
└── README.md                        # This file
```

## Quick Start Guide

### For Claude Code Users (Level 1 or 2)

1. **Add this repository to Claude Code:**
   - Your repository URL will point to this marketplace
   - Claude Code will discover all available plugins

2. **Choose your plugins:**
   - **Level 1**: Install `agent-orchestrator` only
   - **Level 2**: Install both `agent-orchestrator` and `agent-orchestrator-subagents`

3. **Start orchestrating:**
   ```
   /agent-orchestrator-init
   ```

### For Claude Desktop Users (Level 3)

**Requirements:** Python ≥3.10, [uv](https://docs.astral.sh/uv/getting-started/installation/)

1. **Clone repository:**
   ```bash
   git clone <your-repo-url>
   cd agent-orchestrator-framework/agent-orchestrator-mcp-server
   ```

2. **Configure MCP server:**
   See [agent-orchestrator-mcp-server/README.md](./agent-orchestrator-mcp-server/README.md)

3. **Use from Claude Desktop:**
   ```
   List available agents
   ```

## Core Concepts

### Agent Definitions
Markdown files that define specialized agent configurations with custom system prompts, instructions, and MCP configurations. Stored in `.agent-orchestrator/agents/`.

### Sessions
Isolated Claude Code sessions for individual agents. Each session has a unique ID, configuration, and result storage. Stored in `.agent-orchestrator/sessions/`.

### MCP Configuration
Different agents can have different MCP server configurations, enabling specialized capabilities per agent type.

### Orchestration Commands
The Python-based `ao-*` commands (`ao-new`, `ao-resume`, `ao-status`, etc.) are the foundation of all three usage levels. They handle session lifecycle, agent configuration, and result extraction.


## Observability

Monitor your agent orchestration in real-time with the built-in observability platform:

- **Real-time monitoring** of agent sessions and tool calls
- **WebSocket-based** live updates
- **Docker support** for one-command deployment
- **Hook-based integration** with Claude Code events

**Quick Start:**
```bash
cd agent-orchestrator-observability
docker-compose up -d
# Open http://localhost:5173
```

See **[agent-orchestrator-observability/README.md](./agent-orchestrator-observability/README.md)** for full documentation.

## Documentation

- **[Level 1: Core Framework](./agent-orchestrator/README.md)** - Plugin documentation
- **[Level 2: Subagents Extension](./agent-orchestrator-subagents/README.md)** - Extension plugin
- **[Level 3: MCP Server](./agent-orchestrator-mcp-server/README.md)** - MCP implementation
- **[Observability Platform](./agent-orchestrator-observability/README.md)** - Real-time monitoring
- **[Technical Architecture](./agent-orchestrator/skills/agent-orchestrator/references/AGENT-ORCHESTRATOR.md)** - Deep dive into how it works
