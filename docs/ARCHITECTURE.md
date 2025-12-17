# Agent Orchestrator Architecture

## Overview

Framework for managing multiple concurrent Claude Code agent sessions with real-time observability.

## Project Structure

```
├── dashboard/                    # React web UI for monitoring agents
├── servers/
│   ├── agent-coordinator/            # FastAPI server - sessions, runs, launcher registry
│   ├── agent-launcher/           # Run executor - polls Agent Coordinator, spawns executors
│   │   ├── lib/                  # Core launcher (framework-agnostic)
│   │   └── claude-code/          # Claude Code executors (Claude Agent SDK)
│   └── context-store/            # Document synchronization server
├── plugins/
│   ├── orchestrator/             # Claude Code plugin - orchestrator skill: ao-* CLI commands
│   └── context-store/            # Claude Code plugin - context-store skill: doc-* commands
└── interfaces/
    ├── agent-orchestrator-mcp-server/  # MCP server - calls Runs API
    └── context-store-mcp-server/       # MCP server for document management
```

## Components

### Servers

**Agent Coordinator** (`servers/agent-coordinator/`) - Port 8765
- FastAPI + WebSocket server
- Persists sessions and events in SQLite
- Broadcasts real-time updates to dashboard
- Agent blueprint registry (CRUD API for agent definitions)
- Runs API for asynchronous session start/resume/stop
- Launcher registry with health monitoring
- Callback processor for parent-child session coordination
- Stop command queue for immediate session termination

**Agent Launcher** (`servers/agent-launcher/`)
- Polls Agent Coordinator for pending runs and stop commands
- Executes runs via framework-specific executors
- Supports concurrent run execution
- Reports run status (started, completed, failed, stopped)
- Handles stop commands by terminating running processes
- Maintains heartbeat for health monitoring
- Auto-exits after repeated connection failures

**Claude Code Executors** (`servers/agent-launcher/claude-code/`)
- `ao-start` - Start new Claude Code sessions
- `ao-resume` - Resume existing sessions
- Uses Claude Agent SDK for execution
- Only Claude-specific code in the framework

**Context Store** (`servers/context-store/`) - Port 8766
- Document synchronization between agents
- Tag-based document organization

### Plugins (Claude Code Skills)

**Orchestrator Skill** (`plugins/orchestrator/skills/orchestrator/`)
- ao-* CLI commands that call Agent Coordinator APIs
- `ao-start`, `ao-resume` - Create runs via Runs API
- `ao-list-sessions`, `ao-status`, `ao-get-result` - Query Sessions API
- `ao-list-blueprints`, `ao-show-config`, `ao-delete-all` - Utilities
- Framework-agnostic HTTP clients (no Claude SDK dependency)

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
│  │  │  (ao-* CLI commands)  │  │     │  │  (doc-* commands)     │  │        │
│  │  └───────────┬───────────┘  │     │  └───────────┬───────────┘  │        │
│  └──────────────│──────────────┘     └──────────────│──────────────┘        │
└─────────────────│───────────────────────────────────│───────────────────────┘
                  │                                   │
                  │ HTTP (Runs API)                   │ HTTP
                  ▼                                   ▼
┌─────────────────────────────────────┐   ┌─────────────────────────────────┐
│         Agent Coordinator :8765         │   │       Context Store :8766       │
│  - Sessions API                     │   │   - Document storage            │
│  - Runs API                         │   │   - Tag-based queries           │
│  - Launcher registry                │   │   - Semantic search             │
│  - Callback processor               │   └─────────────────┬───────────────┘
│  - SQLite persistence               │                     │
│  - WebSocket broadcast              │◄──────────────┐     │ HTTP
│  - Agent blueprint registry         │          WS   │     │
└──────────┬──────────────────────────┘               │     │
           │                                          │     │
           │ Long-poll (Runs)                   ┌─────┴─────┴─────┐
           ▼                                    │    Dashboard    │
┌─────────────────────────────────────┐         │ - Session view  │
│        Agent Launcher               │         │ - Launcher mgmt │
│  - Polls for pending runs           │         │ - Blueprint mgmt│
│  - Concurrent run execution         │         │ - Chat tab      │
│  - Reports run status               │         │ - Document view │
│  - Heartbeat / health monitoring    │         └─────────────────┘
└──────────┬──────────────────────────┘
           │
           │ Subprocess
           ▼
┌─────────────────────────────────────┐
│  Claude Code Executors              │
│  (servers/agent-launcher/claude-code)│
│  - ao-start: Start new sessions     │
│  - ao-resume: Resume sessions       │
│  - Uses Claude Agent SDK            │
└─────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  MCP Servers (interfaces/)                           │
│  - agent-orchestrator-mcp: calls Runs API            │──► External MCP Clients
│  - context-store-mcp: runs doc-* as subprocess       │
└──────────────────────────────────────────────────────┘
```

### Interaction Summary

| Source | Target | Protocol | Purpose |
|--------|--------|----------|---------|
| ao-* CLI commands | Agent Coordinator | HTTP | Create runs, query sessions |
| doc-* commands | Context Store | HTTP | Document operations |
| Dashboard | Agent Coordinator | HTTP | Runs API, Sessions API, Blueprints API |
| Dashboard | Agent Coordinator | HTTP | Launcher management |
| Dashboard | Agent Coordinator | WebSocket | Real-time session updates |
| Dashboard | Context Store | HTTP | Document listing/viewing |
| Agent Launcher | Agent Coordinator | HTTP | Long-poll for runs, report status |
| Agent Launcher | Agent Coordinator | HTTP | Registration, heartbeat |
| Agent Launcher | Claude Code Executors | Subprocess | Execute ao-start, ao-resume |
| Agent Orchestrator MCP | Agent Coordinator | HTTP | Runs API (start/resume sessions) |
| Context Store MCP | doc-* commands | Subprocess | Expose as MCP tools |

## Key Environment Variables

| Variable | Default | Used By |
|----------|---------|---------|
| `AGENT_ORCHESTRATOR_API_URL` | `http://127.0.0.1:8765` | ao-* CLI commands, MCP Server, Agent Launcher |
| `VITE_AGENT_ORCHESTRATOR_API_URL` | `http://localhost:8765` | Dashboard |
| `AGENT_ORCHESTRATOR_PROJECT_DIR` | cwd | ao-* CLI commands, MCP Server |
| `AGENT_ORCHESTRATOR_AGENTS_DIR` | `.agent-orchestrator/agents` | Agent Coordinator |
| `DEBUG_LOGGING` | `false` | Agent Coordinator |
| `POLL_TIMEOUT` | `30` | Agent Launcher |
| `HEARTBEAT_INTERVAL` | `60` | Agent Launcher |
| `PROJECT_DIR` | cwd | Agent Launcher |
| `AGENT_SESSION_NAME` | (none) | Claude Code Executors (set by Launcher) |

## Agent Launcher Architecture

The Agent Launcher enables distributed agent execution, separating orchestration (Agent Coordinator) from execution (Launcher + Executors).

### Why Separate?

Starting agent sessions requires spawning AI framework processes (e.g., Claude Code). These processes must run on the host machine—not inside a Docker container. The Agent Launcher runs on hosts where agent frameworks are installed, while the Agent Coordinator can be containerized.

### Architecture

```
┌─────────────────────────────────────┐
│         Agent Coordinator               │
│  - Runs API (queue & dispatch)      │
│  - Launcher registry                │
│  - Callback processor               │
└──────────────┬──────────────────────┘
               │ Long-poll for runs
               ▼
┌─────────────────────────────────────┐
│         Agent Launcher              │
│  - Polls for pending runs           │
│  - Concurrent execution             │
│  - Status reporting                 │
│  - Health monitoring                │
└──────────────┬──────────────────────┘
               │ Subprocess
               ▼
┌─────────────────────────────────────┐
│  Framework-Specific Executors       │
│  ┌───────────────────────────────┐  │
│  │ claude-code/                  │  │
│  │  - ao-start, ao-resume        │  │
│  │  - Uses Claude Agent SDK      │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │ (future: other frameworks)    │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

### Launcher Lifecycle

1. **Registration**: Launcher calls `POST /launcher/register` on startup
2. **Polling**: Long-polls `GET /launcher/runs` for pending runs or stop commands
3. **Execution**: Spawns executor subprocess (e.g., `claude-code/ao-start`)
4. **Reporting**: Reports run status (started, completed, failed, stopped)
5. **Stop Handling**: Receives stop commands and terminates running processes
6. **Heartbeat**: Sends periodic heartbeat for health monitoring
7. **Deregistration**: Graceful shutdown or auto-exit after connection failures

### Callback Architecture

Parent-child session coordination enables orchestration patterns:

1. Parent agent starts child with `callback=true`
2. Agent Coordinator tracks `parent_session_name` on child session
3. When child completes, Callback Processor checks parent status
4. If parent is idle: creates resume run immediately
5. If parent is busy: queues notification for later delivery
6. Parent receives aggregated callback when it becomes idle

```
Parent (orchestrator)          Child (worker)
       │                            │
       │ start with callback=true   │
       │───────────────────────────►│
       │                            │
       │ continues work...          │ executes task...
       │                            │
       │ becomes idle               │ completes
       │                            │
       │◄─── callback notification ─┤
       │     (via resume run)       │
       │                            │
       ▼
  resumes with child result
```

### Extensibility

The architecture supports multiple agent frameworks:
- **Claude Code**: Currently implemented (`servers/agent-launcher/claude-code/`)
- **Future**: LangChain, AutoGen, or other frameworks can add executors

Only the executor directory is framework-specific. The Launcher core, Agent Coordinator, Runs API, and all ao-* CLI commands are framework-agnostic.
