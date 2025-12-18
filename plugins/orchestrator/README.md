# Orchestrator Plugin

The core Agent Orchestrator Framework (AOF) plugin for Claude Code. Provides Python-based orchestration commands, slash commands, and skills for managing specialized Claude Code agent sessions.

## Overview

The Orchestrator plugin enables you to create and manage specialized Claude Code agent sessions. It provides:
- Launch multiple Claude Code sessions programmatically
- Configure agents with custom system prompts and MCP server configurations
- Manage long-running tasks in isolated sessions
- Extract and process results from completed agents
- Use predefined agent blueprints for specialized tasks

## Architecture

The plugin uses a **thin-client architecture** where the `ao-*` commands are HTTP clients that communicate with the backend server:

```
┌─────────────────┐     HTTP      ┌───────────────────┐
│  ao-* commands  │ ──────────▶  │  Agent Coordinator│
│  (thin clients) │              │  (Port 8765)      │
└─────────────────┘              │  - Sessions       │
                                 │  - Events         │
                                 │  - Results        │
                                 │  - Blueprints     │
                                 └───────────────────┘
```

## What's Included

### 1. Core Commands
**Location**: `skills/orchestrator/commands/`

Python-based `ao-*` commands (thin HTTP clients):
- `ao-start` - Start new agent session
- `ao-resume` - Resume existing session
- `ao-status` - Check session state
- `ao-get-result` - Extract result from finished session
- `ao-list-sessions` - List all sessions
- `ao-list-blueprints` - List available agent blueprints
- `ao-show-config` - Display session configuration
- `ao-delete-all` - Delete all sessions

### 2. Slash Commands

Four slash commands for interacting with the framework:

- **`/agent-orchestrator-init`**: Initialize the orchestrator in your conversation
- **`/agent-orchestrator-create-agent`**: Create new agent blueprints
- **`/agent-orchestrator-create-runtime-report`**: Generate runtime analysis reports
- **`/agent-orchestrator-extract-token-usage`**: Extract token usage statistics

### 3. Skill Documentation
**Location**: `skills/orchestrator/SKILL.md`

Comprehensive skill definition with usage instructions and examples.

### 4. Reference Documentation
**Location**: `skills/orchestrator/references/`

- `AGENT-ORCHESTRATOR.md` - Framework architecture and concepts
- `ENV_VARS.md` - Environment variable configuration

## Requirements

- **Python**: ≥3.11 for running the `ao-*` commands
- **uv**: Python package manager ([uv documentation](https://docs.astral.sh/uv/))
- **Backend services**: Agent Coordinator and Agent Registry must be running

## Quick Start

### 1. Start Backend Services

```bash
# From repository root
make start-bg
```

### 2. Use the Plugin

Initialize in your conversation:
```
/agent-orchestrator-init
```

Use the skill to launch agents:
```
Use the orchestrator skill to create a new session called "code-review" and review the changes in src/
```

### 3. Check Available Blueprints

```bash
uv run --script skills/orchestrator/commands/ao-list-blueprints
```

## Key Concepts

### Agent Blueprints
Reusable configurations stored in the Agent Coordinator that define specialized agent behavior:
- Custom system prompts
- MCP server configurations
- Capability descriptions

Managed via the Agent Coordinator API (port 8765) or the Dashboard UI.

### Sessions
Running agent conversations managed by the Agent Coordinator:
- Unique session names for easy reference
- Persistent conversation history
- Real-time status and event tracking

### API-Based Architecture
All state is managed by the Agent Coordinator backend server (port 8765):
- Blueprint CRUD operations
- Session lifecycle, events, results

The `ao-*` commands are stateless thin clients.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_ORCHESTRATOR_API_URL` | `http://localhost:8765` | Agent Orchestrator API URL (sessions + blueprints) |

See `skills/orchestrator/references/ENV_VARS.md` for all options.

## Related Documentation

- **[Main README](../../README.md)** - Framework overview
- **[Architecture](../../docs/ARCHITECTURE.md)** - System architecture
- **[MCP Server](../../interfaces/agent-orchestrator-mcp-server/README.md)** - MCP protocol interface
- **[Dashboard](../../dashboard/README.md)** - Web UI for management
