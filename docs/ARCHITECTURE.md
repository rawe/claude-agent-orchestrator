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
│         Agent Runtime :8765         │   │   Context Store :8766           │
│  - Session management               │   │   - Document storage            │
│  - Event tracking                   │   │   - Tag-based queries           │
│  - SQLite persistence               │   │   - Semantic search             │
│  - WebSocket broadcast              │   └───────────────┬─────────────────┘
│  - Agent blueprint registry         │                   ▲
│  - Agent CRUD API                   │◄──────────┐       │ HTTP
└─────────────────────────────────────┘           │       │
                                            WS    │       │
                                      ┌───────────┴───────┴─────┐
                                      │      Dashboard          │
                                      │   - Session monitor     │
                                      │   - Document viewer     │
                                      │   - Blueprint mgmt      │
                                      └─────────────────────────┘

┌─────────────────────────────────────┐
│  MCP Servers (interfaces/)          │
│  - agent-orchestrator-mcp: ao-*     │──► External MCP Clients
│  - context-store-mcp: doc-*         │
└─────────────────────────────────────┘
```

### Interaction Summary

| Source | Target | Protocol | Purpose |
|--------|--------|----------|---------|
| ao-* commands | Agent Runtime | HTTP | Session/event CRUD |
| ao-* commands | Agent Runtime | HTTP | Get agent blueprints |
| doc-* commands | Context Store | HTTP | Document operations |
| Dashboard | Agent Runtime | WebSocket | Real-time session updates |
| Dashboard | Agent Runtime | HTTP | Blueprint management |
| Dashboard | Context Store | HTTP | Document listing/viewing |
| Agent Orchestrator MCP | ao-* commands | Subprocess | Expose as MCP tools |
| Context Store MCP | doc-* commands | Subprocess | Expose as MCP tools |

## Key Environment Variables

| Variable | Default | Used By |
|----------|---------|---------|
| `AGENT_ORCHESTRATOR_SESSION_MANAGER_URL` | `http://127.0.0.1:8765` | Commands |
| `AGENT_ORCHESTRATOR_AGENT_API_URL` | `http://localhost:8765` | Commands |
| `AGENT_ORCHESTRATOR_PROJECT_DIR` | cwd | Commands, MCP Server |
| `AGENT_ORCHESTRATOR_AGENTS_DIR` | `.agent-orchestrator/agents` | Agent Runtime |
| `DEBUG_LOGGING` | `false` | Agent Runtime |
