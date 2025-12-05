# Agent Orchestrator Architecture

## Overview

Framework for managing multiple concurrent Claude Code agent sessions with real-time observability.

## Project Structure

```
├── dashboard/                    # React web UI for monitoring agents
├── servers/
│   ├── agent-runtime/            # FastAPI server - session/event tracking + agent registry
│   └── context-store/            # Document synchronization server
├── plugins/
│   ├── orchestrator/             # Claude Code plugin - with orchestrator skill: ao-* commands
│   └── context-store/            # Claude Code plugin - with context-store skill: doc-* commands
└── interfaces/
    ├── agent-orchestrator-mcp-server/  # MCP server for agent orchestration
    └── context-store-mcp-server/       # MCP server for document management
```

## Components

### Servers

**Agent Runtime** (`servers/agent-runtime/`) - Port 8765
- FastAPI + WebSocket server
- Persists sessions and events in SQLite
- Broadcasts real-time updates to dashboard
- Agent blueprint registry (CRUD API for agent definitions)
- File-based agent blueprint storage

**Context Store** (`servers/context-store/`) - Port 8766
- Document synchronization between agents
- Tag-based document organization

### Plugins (Claude Code Skills)

**Orchestrator Skill** (`plugins/orchestrator/skills/orchestrator/`)
- `ao-start`, `ao-resume` - Start/resume agent sessions
- `ao-list-sessions`, `ao-status`, `ao-get-result` - Session management
- `ao-list-blueprints`, `ao-show-config`, `ao-delete-all` - Utilities

**Context Store Skill** (`plugins/context-store/skills/context-store/`)
- `doc-push`, `doc-pull` - Sync documents to/from server
- `doc-read`, `doc-query`, `doc-info`, `doc-delete` - Document operations

### Dashboard (`dashboard/`)
- Real-time session monitoring via WebSocket
- Event timeline and tool call visualization

## Component Interactions

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Claude Code                                    │
│  ┌─────────────────────────────┐     ┌─────────────────────────────┐        │
│  │   Orchestrator Plugin       │     │   Context Store Plugin      │        │
│  │  ┌───────────────────────┐  │     │  ┌───────────────────────┐  │        │
│  │  │  orchestrator skill   │  │     │  │  context-store skill  │  │        │
│  │  │  (ao-* commands)      │  │     │  │  (doc-* commands)     │  │        │
│  │  └───────────┬───────────┘  │     │  └───────────┬───────────┘  │        │
│  └──────────────│──────────────┘     └──────────────│──────────────┘        │
└─────────────────│───────────────────────────────────│───────────────────────┘
                  │                                   │
                  │ HTTP                              │ HTTP
                  ▼                                   ▼
┌─────────────────────────────────────┐   ┌─────────────────────────────────┐
│         Agent Runtime :8765         │   │   Context Store :8766           │
│  - Session management               │   │   - Document storage            │
│  - Event tracking                   │   │   - Tag-based queries           │
│  - SQLite persistence               │   │   - Semantic search             │
│  - WebSocket broadcast              │   └─────────────────┬───────────────┘
│  - Agent blueprint registry         │                     ▲
│  - Agent CRUD API                   │◄─────────────┐      │ HTTP
└─────────────────────────────────────┘              │      │
                  ▲                             WS   │      │
                  │ HTTP (via ao-*)                  │      │
┌─────────────────┴─────────────────┐      ┌─────────┴──────┴────────┐
│  Agent Control API :9500          │ HTTP │      Dashboard          │
│  (not dockerized)                 │◄─────│   - Session monitor     │
│  - Runs ao-start, ao-resume       │      │   - Document viewer     │
│    as subprocess                  │      │   - Blueprint mgmt      │
└───────────────────────────────────┘      │   - Chat (start/resume) │
                                           └─────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  MCP Servers (interfaces/)                           │
│  (not dockerized)                                    │
│  - agent-orchestrator-mcp: runs ao-* as subprocess   │──► External MCP Clients
│  - context-store-mcp: runs doc-* as subprocess       │
└──────────────────────────────────────────────────────┘
```

**Note:** The Agent Control API (`make start-ao-api`) is a temporary non-dockerized service that runs `ao-start` and `ao-resume` as subprocesses. Session updates flow to the Dashboard via the existing WebSocket connection to Agent Runtime. See [Future: Agent Launcher Architecture](#future-agent-launcher-architecture) for why this is separate and the planned solution.

### Interaction Summary

| Source | Target | Protocol | Purpose |
|--------|--------|----------|---------|
| ao-* commands | Agent Runtime | HTTP | Session/event CRUD |
| ao-* commands | Agent Runtime | HTTP | Get agent blueprints |
| doc-* commands | Context Store | HTTP | Document operations |
| Dashboard | Agent Runtime | WebSocket | Real-time session updates |
| Dashboard | Agent Runtime | HTTP | Blueprint management |
| Dashboard | Agent Control API | HTTP | Start/resume sessions (Chat tab) |
| Dashboard | Context Store | HTTP | Document listing/viewing |
| Agent Orchestrator MCP | ao-* commands | Subprocess | Expose as MCP tools |
| Context Store MCP | doc-* commands | Subprocess | Expose as MCP tools |

## Key Environment Variables

| Variable | Default | Used By |
|----------|---------|---------|
| `AGENT_ORCHESTRATOR_API_URL` | `http://127.0.0.1:8765` | ao-* Commands |
| `VITE_AGENT_ORCHESTRATOR_API_URL` | `http://localhost:8765` | Dashboard |
| `VITE_AGENT_CONTROL_API_URL` | `http://localhost:9500` | Dashboard (Chat tab) |
| `AGENT_ORCHESTRATOR_PROJECT_DIR` | cwd | Commands, MCP Server |
| `AGENT_ORCHESTRATOR_AGENTS_DIR` | `.agent-orchestrator/agents` | Agent Runtime |
| `DEBUG_LOGGING` | `false` | Agent Runtime |

## Future: Agent Launcher Architecture

### Current Limitation

The Agent Control API exists as a separate, non-dockerized service because starting agent sessions requires spawning Claude Code processes. These processes can only run on the host machine—not inside a Docker container.

This is why session start/resume functionality is not included in the dockerized Agent Runtime.

### Planned Solution

To properly integrate agent execution into the architecture, we would introduce an **Agent Launcher** model:

```
┌─────────────────────────────────────┐
│         Agent Runtime               │
│  - Session orchestration            │
│  - Launcher registration            │
│  - Job queue & dispatch             │
└──────────────┬──────────────────────┘
               │ Register & receive jobs
    ┌──────────┴──────────┐
    ▼                     ▼
┌─────────────┐     ┌─────────────┐
│  Launcher A │     │  Launcher B │
│  (Host 1)   │     │  (Host 2)   │
│  Claude Code│     │  Claude Code│
└─────────────┘     └─────────────┘
```

**Agent Launchers** would be lightweight processes that:
- Run on hosts where Claude Code (or other agents) is installed
- Register with Agent Runtime on startup
- Receive session start/resume requests from Agent Runtime
- Execute agents locally and report status back

This is analogous to **GitLab's Runner architecture**, but for AI agents instead of CI/CD jobs. It would enable:
- Horizontal scaling across multiple hosts
- Support for different agent types (Claude Code, other LLM agents)
- Centralized orchestration with distributed execution
