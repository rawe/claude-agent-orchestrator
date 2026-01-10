# Agent Orchestrator Architecture

## Overview

Framework for managing multiple concurrent Claude Code agent sessions with real-time observability.

## Core Terminology

| Term | Definition |
|------|------------|
| **Agent Blueprint** | Reusable agent configuration (system prompt, MCP config, metadata). Templates that get instantiated into sessions. |
| **Session** | Named, persistent agent conversation with state and history. Can have multiple agent runs over its lifetime. |
| **Agent Run** | Single execution of a session (start, resume, or stop). Transient work unit queued in the Agent Runs API. |
| **Agent Coordinator** | Backend server (port 8765) managing sessions, agent runs, runners, blueprints, and callbacks. |
| **Agent Runner** | Standalone process that polls for agent runs, processes them via executors, and reports status. |
| **Agent Coordinator Proxy** | Local HTTP proxy started by Agent Runner that forwards executor requests to Agent Coordinator with authentication. |
| **Executor** | Framework-specific code that spawns the actual agent process (e.g., Claude Code via Agent SDK). Communicates with Agent Coordinator via the proxy. |
| **Agent Type** | Classification of agents: **autonomous** (AI-powered, supports resumption) or **procedural** (deterministic CLI execution, stateless). See [agent-types.md](architecture/agent-types.md). |
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
│   ├── agent-coordinator/            # FastAPI server - sessions, agent runs, runner registry
│   ├── agent-runner/           # Processes agent runs - polls Agent Coordinator, spawns executors
│   │   ├── lib/                  # Core runner (framework-agnostic)
│   │   └── claude-code/          # Claude Code executors (Claude Agent SDK)
│   └── context-store/            # Document synchronization server
├── plugins/
│   ├── orchestrator/             # Claude Code plugin - orchestrator skill: ao-* CLI commands
│   └── context-store/            # Claude Code plugin - context-store skill: doc-* commands
└── mcps/                         # MCP servers
    ├── context-store/            # Context Store MCP server
    ├── neo4j/                    # Neo4j MCP server
    ├── atlassian/                # Atlassian (Jira + Confluence) MCP
    └── ado/                      # Azure DevOps MCP
```

## Components

### Servers

**Agent Coordinator** (`servers/agent-coordinator/`) - Port 8765
- FastAPI server with SSE
- Persists sessions and events in SQLite
- Broadcasts real-time updates to dashboard
- Agent blueprint registry (CRUD API for agent definitions)
- Agent Runs API for asynchronous session start/resume/stop
- Runner registry with health monitoring
- Callback processor for parent-child session coordination
- Stop command queue for immediate session termination
- OIDC authentication with Auth0 (see [auth-oidc.md](architecture/auth-oidc.md))

**Agent Runner** (`servers/agent-runner/`)
- Polls Agent Coordinator for pending agent runs and stop commands
- Starts Agent Coordinator Proxy for executor communication (see below)
- Hosts embedded Agent Orchestrator MCP server (use `--mcp-port` for external clients)
- Processes agent runs via framework-specific executors
- Supports concurrent agent run processing
- Reports agent run status (started, completed, failed, stopped)
- Handles stop commands by terminating running processes
- Maintains heartbeat for health monitoring
- Auto-exits after repeated connection failures

**Agent Coordinator Proxy** (`servers/agent-runner/lib/coordinator_proxy.py`)
- Local HTTP proxy started by Agent Runner on a dynamic port
- Forwards all executor HTTP requests to Agent Coordinator
- Handles authentication transparently (Auth0 M2M tokens)
- Executors don't need authentication credentials
- Supports multiple runners on the same machine (each gets own port)

**Claude Code Executors** (`servers/agent-runner/claude-code/`)
- `ao-claude-code-exec` - Start new Claude Code sessions or resumes existing ones
- Uses Claude Agent SDK for execution
- Only Claude-specific code in the framework

**Context Store** (`servers/context-store/`) - Port 8766
- Document synchronization between agents
- Tag-based document organization

### Plugins (Claude Code Skills)

**Orchestrator Skill** (`plugins/orchestrator/skills/orchestrator/`)
- ao-* CLI commands that call Agent Coordinator APIs
- `ao-start`, `ao-resume` - Queue agent runs via Agent Runs API
- `ao-list-sessions`, `ao-status`, `ao-get-result` - Query Sessions API
- `ao-list-blueprints`, `ao-show-config`, `ao-delete-all` - Utilities
- Framework-agnostic HTTP clients (no Claude SDK dependency)

**Context Store Skill** (`plugins/context-store/skills/context-store/`)
- `doc-push`, `doc-pull` - Sync documents to/from server
- `doc-read`, `doc-query`, `doc-info`, `doc-delete` - Document operations

### Dashboard (`dashboard/`)
- Real-time session monitoring via SSE
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
                  │ HTTP (Agent Runs API)             │ HTTP
                  ▼                                   ▼
┌─────────────────────────────────────┐   ┌─────────────────────────────────┐
│         Agent Coordinator :8765     │   │       Context Store :8766       │
│  - Sessions API                     │   │   - Document storage            │
│  - Agent Runs API                   │   │   - Tag-based queries           │
│  - Runner registry                  │   │   - Semantic search             │
│  - Callback processor               │   └─────────────────┬───────────────┘
│  - SQLite persistence               │                     │
│  - SSE broadcast                    │◄──────────────┐     │ HTTP
│  - Agent blueprint registry         │          SSE  │     │
└──────────┬──────────────────────────┘               │     │
           │                                          │     │
           │ Long-poll (Agent Runs)             ┌─────┴─────┴─────┐
           ▼                                    │    Dashboard    │
┌─────────────────────────────────────┐         │ - Session view  │
│        Agent Runner                 │         │ - Runner mgmt   │
│  - Polls for pending agent runs     │         │ - Blueprint mgmt│
│  - Concurrent agent run processing  │         │ - Chat tab      │
│  - Reports agent run status         │         │ - Document view │
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
│  MCP Servers                                         │
│  - Agent Orchestrator: embedded in Agent Runner      │──► Agents + External Clients
│  - Context Store (mcps/context-store/): port 9501    │
└──────────────────────────────────────────────────────┘
```

### Interaction Summary

| Source | Target | Protocol | Purpose |
|--------|--------|----------|---------|
| ao-* CLI commands | Agent Coordinator | HTTP | Queue agent runs, query sessions |
| doc-* commands | Context Store | HTTP | Document operations |
| Dashboard | Agent Coordinator | HTTP | Agent Runs API, Sessions API, Blueprints API |
| Dashboard | Agent Coordinator | HTTP | Runner management |
| Dashboard | Agent Coordinator | SSE | Real-time session updates |
| Dashboard | Context Store | HTTP | Document listing/viewing |
| Agent Runner | Agent Coordinator | HTTP | Long-poll for agent runs, report status |
| Agent Runner | Agent Coordinator | HTTP | Registration, heartbeat |
| Agent Runner | Executors | Subprocess | Spawn executor with proxy URL |
| Executors | Agent Coordinator Proxy | HTTP | Sessions API, Agent Blueprints API (no auth) |
| Agent Coordinator Proxy | Agent Coordinator | HTTP | Forward requests with auth headers |
| Agent Orchestrator MCP (embedded) | Agent Coordinator | HTTP | Agent Runs API (start/resume sessions) |
| Context Store MCP | Context Store | HTTP | Document operations as MCP tools |

## Key Environment Variables

| Variable | Default | Used By |
|----------|---------|---------|
| `AGENT_ORCHESTRATOR_API_URL` | `http://127.0.0.1:8765` | ao-* CLI commands, MCP Server, Agent Runner |
| `VITE_AGENT_ORCHESTRATOR_API_URL` | `http://localhost:8765` | Dashboard |
| `AGENT_ORCHESTRATOR_PROJECT_DIR` | cwd | ao-* CLI commands, MCP Server |
| `AGENT_ORCHESTRATOR_AGENTS_DIR` | `.agent-orchestrator/agents` | Agent Coordinator |
| `AUTH_ENABLED` | `false` | Agent Coordinator (set `true` to enable Auth0 OIDC) |
| `AUTH0_DOMAIN` | (none) | Agent Coordinator, Dashboard (Auth0 tenant domain) |
| `AUTH0_AUDIENCE` | (none) | Agent Coordinator, Dashboard (API identifier) |
| `AUTH0_DASHBOARD_CLIENT_ID` | (none) | Dashboard (SPA client ID) |
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
│         Agent Coordinator           │
│  - Agent Runs API (queue & dispatch)│
│  - Runner registry                  │
│  - Callback processor               │
│  - Sessions API                     │
│  - Agent blueprints API             │
└──────────────┬──────────────────────┘
               │
               │ HTTP (authenticated)
               │
     ┌─────────┴─────────┐
     │                   │
     │ Long-poll         │ Proxy forwards
     │ (Runner)          │ (Executor requests)
     │                   │
     ▼                   │
┌────────────────────────┴────────────┐
│         Agent Runner                │
│  - Polls for pending agent runs     │
│  - Concurrent processing            │
│  - Status reporting                 │
│  - Health monitoring                │
│  ┌────────────────────────────────┐ │
│  │  Agent Coordinator Proxy       │ │
│  │  - Local HTTP (127.0.0.1:port) │ │
│  │  - Adds auth headers           │ │
│  │  - Forwards to Coordinator     │ │
│  └───────────────┬────────────────┘ │
└──────────────────┼──────────────────┘
                   │
                   │ Subprocess + HTTP via proxy
                   ▼
┌─────────────────────────────────────┐
│  Framework-Specific Executors       │
│  ┌───────────────────────────────┐  │
│  │ claude-code/                  │  │
│  │  - ao-claude-code-exec        │  │
│  │  - Uses Claude Agent SDK      │  │
│  │  - Calls Sessions API         │  │
│  │  - Calls Agent Blueprints API │  │
│  │  (via proxy, no auth needed)  │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │ (future: other frameworks)    │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

### Runner Lifecycle

1. **Registration**: Runner calls `POST /runner/register` on startup
2. **Proxy Start**: Starts Agent Coordinator Proxy on dynamic port
3. **Polling**: Long-polls `GET /runner/runs` for pending agent runs or stop commands
4. **Execution**: Spawns executor subprocess with `AGENT_ORCHESTRATOR_API_URL` pointing to proxy
5. **Reporting**: Reports agent run status (started, completed, failed, stopped)
6. **Stop Handling**: Receives stop commands and terminates running processes
7. **Heartbeat**: Sends periodic heartbeat for health monitoring
8. **Deregistration**: Graceful shutdown or auto-exit after connection failures

### Agent Coordinator Proxy

The Agent Coordinator Proxy provides a security boundary between executors and the Agent Coordinator.

**Why a Proxy?**

Executors are spawned as subprocesses and need to call Agent Coordinator APIs (Sessions API, Agent Blueprints API). Without a proxy, executors would need direct access to authentication credentials. The proxy:

- Keeps authentication credentials in the Runner process only
- Forwards executor requests with proper auth headers (Auth0 M2M or API key)
- Makes authentication transparent to executors
- Supports multiple runners on the same machine (each gets a unique port)

**How It Works**

```
Executor                    Agent Runner                 Agent Coordinator
   │                             │                              │
   │ GET /agents/my-agent        │                              │
   │ (no auth header)            │                              │
   │────────────────────────────►│                              │
   │                             │ GET /agents/my-agent         │
   │                             │ Authorization: Bearer <token>│
   │                             │─────────────────────────────►│
   │                             │                              │
   │                             │◄─────────────────────────────│
   │◄────────────────────────────│                              │
   │                             │                              │
```

**Configuration**

The proxy is transparent to executors. The Runner sets `AGENT_ORCHESTRATOR_API_URL` to the proxy URL before spawning executors. Executors use this URL without knowing they're communicating via a proxy.

### Callback Architecture

Parent-child session coordination enables orchestration patterns:

1. Parent agent starts child with `callback=true`
2. Agent Coordinator tracks `parent_session_name` on child session
3. When child completes, Callback Processor checks parent status
4. If parent is idle: immediately resumes the parent session
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
       │     (by resuming session)  │
       │                            │
       ▼
  resumes with child result
```

### Extensibility

The architecture supports multiple agent frameworks:
- **Claude Code**: Currently implemented (`servers/agent-runner/claude-code/`)
- **Future**: LangChain, AutoGen, or other frameworks can add executors

Only the executor directory is framework-specific. The Runner core, Agent Coordinator, Agent Runs API, and all ao-* CLI commands are framework-agnostic.

## Related Architecture Documents

| Document | Description |
|----------|-------------|
| [Agent Types](architecture/agent-types.md) | Autonomous vs procedural agents, unified invocation model, parameter validation |
| [MCP Runner Integration](architecture/mcp-runner-integration.md) | Embedded MCP server in Agent Runner |
| [SSE Sessions](architecture/sse-sessions.md) | Server-sent events for real-time updates |
| [Auth OIDC](architecture/auth-oidc.md) | Authentication with Auth0 |
| [Auth Coordinator](architecture/auth-coordinator.md) | Coordinator authentication architecture |
