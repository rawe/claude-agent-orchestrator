# Agent Orchestrator Architecture

## Overview

Framework for managing multiple concurrent Claude Code agent sessions with real-time observability.

## Project Structure

```
├── dashboard/                    # React web UI for monitoring agents
├── servers/
│   ├── agent-runtime/            # FastAPI server - session/event tracking
│   ├── agent-registry/           # Agent blueprint API
│   └── context-store/            # Document synchronization server
├── plugins/
│   ├── orchestrator/             # Claude Code plugin - with orchestrator skill: ao-* commands
│   └── context-store/            # Claude Code plugin - with context-store skill: doc-* commands
└── interfaces/
    └── agent-orchestrator-mcp-server/  # MCP server interface
```

## Components

### Servers

**Agent Runtime** (`servers/agent-runtime/`) - Port 8765
- FastAPI + WebSocket server
- Persists sessions and events in SQLite
- Broadcasts real-time updates to dashboard

**Agent Registry** (`servers/agent-registry/`) - Port 8767
- Stores and serves agent blueprint definitions
- API for agent CRUD operations

**Context Store** (`servers/context-store/`) - Port 8766
- Document synchronization between agents
- Tag-based document organization

### Plugins (Claude Code Skills)

**Orchestrator Skill** (`plugins/orchestrator/skills/orchestrator/`)
- `ao-new`, `ao-resume` - Start/resume agent sessions
- `ao-list-sessions`, `ao-status`, `ao-get-result` - Session management
- `ao-list-agents`, `ao-show-config`, `ao-clean` - Utilities

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
│  ┌─────────────────────────────┐     ┌─────────────────────────────┐       │
│  │   Orchestrator Plugin       │     │   Context Store Plugin      │       │
│  │  ┌───────────────────────┐  │     │  ┌───────────────────────┐  │       │
│  │  │  orchestrator skill   │  │     │  │  context-store skill  │  │       │
│  │  │  (ao-* commands)      │  │     │  │  (doc-* commands)     │  │       │
│  │  └───────────┬───────────┘  │     │  └───────────┬───────────┘  │       │
│  └──────────────│──────────────┘     └──────────────│──────────────┘       │
└─────────────────│───────────────────────────────────│───────────────────────┘
                  │                                   │
                  │ HTTP                              │ HTTP
                  ▼                                   ▼
┌─────────────────────────────────────┐   ┌─────────────────────────────────┐
│         SERVERS                     │   │   Context Store :8766           │
│  ┌──────────────────────────────┐   │   │   - Document storage            │
│  │  Agent Runtime :8765         │   │   │   - Tag-based queries           │
│  │  - Session management        │   │   └───────────────┬─────────────────┘
│  │  - Event tracking            │   │                   │
│  │  - SQLite persistence        │   │                   │ HTTP
│  │  - WebSocket broadcast       │◄──┼─────────┐         │
│  └──────────────────────────────┘   │         │         │
│                                     │         │ WS      │
│  ┌──────────────────────────────┐   │         │         │
│  │  Agent Registry :8767        │   │   ┌─────┴─────────┴─────┐
│  │  - Agent blueprints          │   │   │      Dashboard      │
│  │  - CRUD API                  │   │   │   - Session monitor │
│  └──────────────────────────────┘   │   │   - Document viewer │
└─────────────────────────────────────┘   └─────────────────────┘

┌─────────────────────────────────────┐
│  MCP Server (interfaces/)           │
│  - Wraps ao-* as MCP tools          │──► External MCP Clients
│  - Subprocess execution             │
└─────────────────────────────────────┘
```

### Interaction Summary

| Source | Target | Protocol | Purpose |
|--------|--------|----------|---------|
| ao-* commands | Agent Runtime | HTTP | Session/event CRUD |
| ao-* commands | Agent Registry | HTTP | Get agent blueprints |
| doc-* commands | Context Store | HTTP | Document operations |
| Dashboard | Agent Runtime | WebSocket | Real-time session updates |
| Dashboard | Context Store | HTTP | Document listing/viewing |
| MCP Server | ao-* commands | Subprocess | Expose as MCP tools |

## Key Environment Variables

| Variable | Default | Used By |
|----------|---------|---------|
| `AGENT_ORCHESTRATOR_SESSION_MANAGER_URL` | `http://127.0.0.1:8765` | Commands |
| `AGENT_ORCHESTRATOR_AGENT_API_URL` | `http://localhost:8767` | Commands |
| `AGENT_ORCHESTRATOR_PROJECT_DIR` | cwd | Commands, MCP Server |
| `DEBUG_LOGGING` | `false` | Agent Runtime |