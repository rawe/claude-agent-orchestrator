# Agent Orchestrator Architecture

## Overview

Framework for managing multiple concurrent Claude Code agent sessions with real-time observability.

## Core Terminology

| Term | Definition |
|------|------------|
| **Agent Blueprint** | Reusable agent configuration (system prompt, MCP config, metadata). Templates that get instantiated into sessions. |
| **Session** | Named, persistent agent conversation with state and history. Can have multiple runs over its lifetime. |
| **Agent Run** | Single execution of a session (start, resume, or stop). Transient work unit queued in the Runs API. |
| **Agent Coordinator** | Backend server (port 8765) managing sessions, runs, runners, blueprints, and callbacks. |
| **Agent Runner** | Standalone process that polls for runs, executes them via executors, and reports status. |
| **Executor** | Framework-specific code that spawns the actual agent process (e.g., Claude Code via Agent SDK). |
| **Context Store** | Backend server (port 8766) for document storage and sharing context between agents. |

### Conceptual Hierarchy

```
Agent Blueprint (template)
    ↓ instantiate
Session (persistent instance)
    ↓ execute
Agent Run (transient execution)
    ↓ claimed by
Agent Runner (execution manager)
    ↓ delegates to
Executor (framework-specific)
    ↓ spawns
Claude Code / AI Framework
```

## Project Structure

```
├── dashboard/                    # React web UI for monitoring agents
├── servers/
│   ├── agent-coordinator/            # FastAPI server - sessions, runs, runner registry
│   ├── agent-runner/           # Run executor - polls Agent Coordinator, spawns executors
│   │   ├── lib/                  # Core runner (framework-agnostic)
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
- Runner registry with health monitoring
- Callback processor for parent-child session coordination
- Stop command queue for immediate session termination

**Agent Runner** (`servers/agent-runner/`)
- Polls Agent Coordinator for pending runs and stop commands
- Executes runs via framework-specific executors
- Supports concurrent run execution
- Reports run status (started, completed, failed, stopped)
- Handles stop commands by terminating running processes
- Maintains heartbeat for health monitoring
- Auto-exits after repeated connection failures

**Claude Code Executors** (`servers/agent-runner/claude-code/`)
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
│  - Runner registry                  │   │   - Semantic search             │
│  - Callback processor               │   └─────────────────┬───────────────┘
│  - SQLite persistence               │                     │
│  - WebSocket broadcast              │◄──────────────┐     │ HTTP
│  - Agent blueprint registry         │          WS   │     │
└──────────┬──────────────────────────┘               │     │
           │                                          │     │
           │ Long-poll (Runs)                   ┌─────┴─────┴─────┐
           ▼                                    │    Dashboard    │
┌─────────────────────────────────────┐         │ - Session view  │
│        Agent Runner                 │         │ - Runner mgmt   │
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
│  (servers/agent-runner/claude-code) │
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
| Dashboard | Agent Coordinator | HTTP | Runner management |
| Dashboard | Agent Coordinator | WebSocket | Real-time session updates |
| Dashboard | Context Store | HTTP | Document listing/viewing |
| Agent Runner | Agent Coordinator | HTTP | Long-poll for runs, report status |
| Agent Runner | Agent Coordinator | HTTP | Registration, heartbeat |
| Agent Runner | Claude Code Executors | Subprocess | Execute ao-start, ao-resume |
| Agent Orchestrator MCP | Agent Coordinator | HTTP | Runs API (start/resume sessions) |
| Context Store MCP | doc-* commands | Subprocess | Expose as MCP tools |

## Key Environment Variables

| Variable | Default | Used By |
|----------|---------|---------|
| `AGENT_ORCHESTRATOR_API_URL` | `http://127.0.0.1:8765` | ao-* CLI commands, MCP Server, Agent Runner |
| `VITE_AGENT_ORCHESTRATOR_API_URL` | `http://localhost:8765` | Dashboard |
| `AGENT_ORCHESTRATOR_PROJECT_DIR` | cwd | ao-* CLI commands, MCP Server |
| `AGENT_ORCHESTRATOR_AGENTS_DIR` | `.agent-orchestrator/agents` | Agent Coordinator |
| `DEBUG_LOGGING` | `false` | Agent Coordinator |
| `POLL_TIMEOUT` | `30` | Agent Runner |
| `HEARTBEAT_INTERVAL` | `60` | Agent Runner |
| `PROJECT_DIR` | cwd | Agent Runner |
| `AGENT_SESSION_NAME` | (none) | Claude Code Executors (set by Runner) |

## Agent Runner Architecture

The Agent Runner enables distributed agent execution, separating orchestration (Agent Coordinator) from execution (Runner + Executors).

### Why Separate?

Starting agent sessions requires spawning AI framework processes (e.g., Claude Code). These processes must run on the host machine—not inside a Docker container. The Agent Runner runs on hosts where agent frameworks are installed, while the Agent Coordinator can be containerized.

### Architecture

```
┌─────────────────────────────────────┐
│         Agent Coordinator               │
│  - Runs API (queue & dispatch)      │
│  - Runner registry                  │
│  - Callback processor               │
└──────────────┬──────────────────────┘
               │ Long-poll for runs
               ▼
┌─────────────────────────────────────┐
│         Agent Runner                │
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

### Runner Lifecycle

1. **Registration**: Runner calls `POST /runner/register` on startup
2. **Polling**: Long-polls `GET /runner/runs` for pending runs or stop commands
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
- **Claude Code**: Currently implemented (`servers/agent-runner/claude-code/`)
- **Future**: LangChain, AutoGen, or other frameworks can add executors

Only the executor directory is framework-specific. The Runner core, Agent Coordinator, Runs API, and all ao-* CLI commands are framework-agnostic.
