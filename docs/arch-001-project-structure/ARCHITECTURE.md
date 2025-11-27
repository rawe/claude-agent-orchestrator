# Agent Orchestrator Framework - Architecture

## Overview

The **Agent Orchestrator Framework** enables orchestration of specialized Claude AI agents in separate sessions. It provides infrastructure for spawning, managing, and monitoring agents with different capabilities, along with mechanisms for sharing context between them.

**Key Capabilities:**
- Spawn specialized agents with custom system prompts and MCP tool configurations
- Manage agent session lifecycle (create, resume, monitor, complete)
- Share documents and context between agents
- Real-time observability via WebSocket
- Multiple interfaces: CLI commands, MCP server, Web dashboard

---

## Terminology

| Term | Short Form | Definition |
|------|------------|------------|
| **Agent Blueprint** | blueprint | A reusable configuration template that defines how an agent should behave. Includes system prompt, allowed MCP tools, permissions, and model settings. Stored in the Agent Registry. |
| **Agent** | agent | A running Claude instance performing work. Created from a blueprint (or generic). |
| **Agent Session** | session | The "hull" or container where an agent runs. Manages lifecycle, stores conversation history, and captures events. An agent lives inside a session. |
| **Agent Registry** | registry | Server component that stores and manages agent blueprints. |
| **Agent Runtime** | runtime | Server component that spawns agents, manages sessions, handles events, and provides real-time updates. |
| **Context Store** | - | Server component for storing and sharing documents between agents. |

### Conceptual Flow

```
Agent Blueprint  ──defines──▶  Agent  ──runs inside──▶  Agent Session
    (plan)                   (worker)                     (hull)
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INTERFACES                                      │
├─────────────────┬─────────────────────────┬─────────────────────────────────┤
│   Dashboard     │      MCP Server         │         CLI Commands            │
│   (Web UI)      │  (MCP Protocol)         │      (ao-*, doc-*)              │
│   Port 3000     │                         │                                 │
└────────┬────────┴────────────┬────────────┴──────────────┬──────────────────┘
         │                     │                           │
         │ HTTP/WS             │ HTTP                      │ HTTP
         │                     │                           │
┌────────▼─────────────────────▼───────────────────────────▼──────────────────┐
│                              SERVERS                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────┐  ┌───────────────────┐  ┌───────────────────────┐ │
│  │   Agent Runtime      │  │  Agent Registry   │  │    Context Store      │ │
│  │   (Port 8765)        │  │  (Port 8767)      │  │    (Port 8766)        │ │
│  │                      │  │                   │  │                       │ │
│  │ • Session management │  │ • Blueprint CRUD  │  │ • Document storage    │ │
│  │ • Agent spawning     │◀─┤ • List blueprints │  │ • Tag-based queries   │ │
│  │ • Event capture      │  │ • Enable/disable  │  │ • File serving        │ │
│  │ • WebSocket updates  │  │                   │  │                       │ │
│  │ • Result extraction  │  │                   │  │                       │ │
│  └──────────┬───────────┘  └───────────────────┘  └───────────────────────┘ │
│             │                                                                │
│             │ spawns                                                         │
│             ▼                                                                │
│  ┌──────────────────────┐                                                   │
│  │   Claude Agent SDK   │                                                   │
│  │   (Claude Code)      │                                                   │
│  └──────────────────────┘                                                   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Components

### Servers

#### Agent Runtime
**Port:** 8765
**Purpose:** Core orchestration server - spawns agents, manages sessions, captures events, provides real-time updates.

**Responsibilities:**
- Create and manage agent sessions
- Spawn Claude agents using the Claude Agent SDK
- Capture and persist session events (tool calls, messages, errors)
- Broadcast real-time updates via WebSocket
- Extract results from completed sessions
- Query Agent Registry for blueprint configurations

**Key Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/sessions` | Create new session, spawn agent |
| POST | `/sessions/{id}/resume` | Resume session with new prompt |
| GET | `/sessions` | List all sessions |
| GET | `/sessions/{id}` | Get session details |
| GET | `/sessions/{id}/status` | Get session status (running/finished/not_existent) |
| GET | `/sessions/{id}/result` | Get result from finished session |
| GET | `/sessions/{id}/events` | Get session events |
| DELETE | `/sessions/{id}` | Delete session |
| WS | `/ws` | Real-time session updates |

---

#### Agent Registry
**Port:** 8767
**Purpose:** Stores and manages agent blueprints (configuration templates).

**Responsibilities:**
- CRUD operations for agent blueprints
- List available blueprints
- Enable/disable blueprints
- Validate blueprint configurations

**Key Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/agents` | List all blueprints |
| GET | `/agents/{name}` | Get blueprint by name |
| POST | `/agents` | Create new blueprint |
| PATCH | `/agents/{name}` | Update blueprint |
| DELETE | `/agents/{name}` | Delete blueprint |
| PATCH | `/agents/{name}/status` | Enable/disable blueprint |

---

#### Context Store
**Port:** 8766
**Purpose:** Document storage and sharing between agents.

**Responsibilities:**
- Store documents with metadata
- Tag-based document organization
- Query documents by filename or tags
- Serve document content
- Enable context sharing between agent sessions

**Key Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/documents` | Upload document |
| GET | `/documents` | List/query documents |
| GET | `/documents/{id}` | Download document |
| GET | `/documents/{id}/metadata` | Get document metadata |
| DELETE | `/documents/{id}` | Delete document |

---

### Interfaces

#### Dashboard (Web UI)
**Port:** 3000
**Technology:** React + Vite + TailwindCSS

**Features:**
- View all agent sessions with real-time status
- Monitor session events as they occur
- Manage agent blueprints (create, edit, enable/disable)
- Browse and manage shared documents
- View session results and conversation history

---

#### MCP Server
**Location:** `/interfaces/agent-orchestrator-mcp-server/`
**Protocol:** Model Context Protocol (MCP)

**Purpose:** Exposes orchestration capabilities to MCP-compatible clients (e.g., Claude Desktop).

**Tools Provided:**
| Tool | Description |
|------|-------------|
| `list_agent_definitions` | List available blueprints |
| `list_agent_sessions` | List all sessions |
| `start_agent_session` | Create and start new session |
| `resume_agent_session` | Resume existing session |
| `get_agent_session_status` | Check session status |
| `get_agent_session_result` | Get result from finished session |
| `delete_all_agent_sessions` | Clean up all sessions |

---

#### CLI Commands (Thin Clients)
**Location:** `/plugins/orchestrator/skills/orchestrator/commands/`

**Purpose:** Command-line interface for agent orchestration. Thin HTTP clients that call the Agent Runtime.

| Command | Description | Calls |
|---------|-------------|-------|
| `ao-new` | Create new agent session | POST /sessions |
| `ao-resume` | Resume existing session | POST /sessions/{id}/resume |
| `ao-status` | Check session status | GET /sessions/{id}/status |
| `ao-get-result` | Get session result | GET /sessions/{id}/result |
| `ao-list-sessions` | List all sessions | GET /sessions |
| `ao-list-agents` | List blueprints | GET /agents (via Registry) |
| `ao-show-config` | Show session config | GET /sessions/{id} |
| `ao-clean` | Delete all sessions | DELETE /sessions |

---

### Plugins (Claude Code)

#### Orchestrator Plugin
**Location:** `/plugins/orchestrator/`

**Contents:**
- `skills/orchestrator/` - CLI commands (ao-*) and skill documentation
- `manifest.json` - Claude Code plugin configuration

**Purpose:** Provides Claude Code with agent orchestration capabilities via skill commands.

---

#### Context Store Plugin
**Location:** `/plugins/context-store/`

**Contents:**
- `skills/context-store/` - CLI commands (doc-*) and skill documentation
- `manifest.json` - Claude Code plugin configuration

**Purpose:** Provides Claude Code with document management capabilities.

| Command | Description |
|---------|-------------|
| `doc-push` | Upload document to Context Store |
| `doc-pull` | Download document |
| `doc-read` | Read document content |
| `doc-info` | Get document metadata |
| `doc-query` | Search documents |
| `doc-delete` | Delete document |

---

## Project Structure

```
claude-agent-orchestrator/
│
├── README.md                          # Quick start guide
├── Makefile                           # Build, run, deploy commands
├── docker-compose.yml                 # Container orchestration
│
├── docs/                              # Documentation
│   ├── ARCHITECTURE.md                # This document
│   ├── guides/                        # User guides
│   └── api/                           # API documentation
│
├── servers/
│   ├── agent-runtime/                 # Session management + agent spawning
│   │   ├── main.py                    # FastAPI application
│   │   ├── database.py                # SQLite persistence
│   │   ├── models.py                  # Pydantic models
│   │   ├── spawner.py                 # Claude Agent SDK integration
│   │   └── pyproject.toml
│   │
│   ├── agent-registry/                # Blueprint management
│   │   ├── main.py
│   │   ├── agent_storage.py
│   │   ├── models.py
│   │   └── pyproject.toml
│   │
│   └── context-store/                 # Document storage
│       ├── src/
│       │   ├── main.py
│       │   ├── database.py
│       │   ├── models.py
│       │   └── storage.py
│       └── pyproject.toml
│
├── interfaces/
│   └── agent-orchestrator-mcp-server/ # MCP protocol interface
│       ├── agent-orchestrator-mcp.py
│       └── libs/
│
├── dashboard/                         # Web UI
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   ├── pages/
│   │   └── utils/
│   ├── package.json
│   └── vite.config.ts
│
├── plugins/                           # Claude Code plugins
│   ├── orchestrator/
│   │   ├── manifest.json
│   │   └── skills/
│   │       └── orchestrator/
│   │           ├── skill.md
│   │           └── commands/
│   │               ├── ao-new
│   │               ├── ao-resume
│   │               ├── ao-status
│   │               ├── ao-get-result
│   │               ├── ao-list-sessions
│   │               ├── ao-list-agents
│   │               ├── ao-show-config
│   │               ├── ao-clean
│   │               └── lib/
│   │
│   └── context-store/
│       ├── manifest.json
│       └── skills/
│           └── context-store/
│               ├── skill.md
│               └── commands/
│                   ├── doc-push
│                   ├── doc-pull
│                   ├── doc-read
│                   ├── doc-info
│                   ├── doc-query
│                   ├── doc-delete
│                   └── lib/
│
└── config/
    └── agents/                        # Example agent blueprints
```

---

## Component Interactions

### Session Lifecycle

```
1. User invokes: ao-new my-agent --agent web-researcher -p "Research topic X"
                        │
                        ▼
2. CLI Command (ao-new) ──HTTP POST──▶ Agent Runtime /sessions
                                              │
                                              ▼
3. Agent Runtime ──HTTP GET──▶ Agent Registry /agents/web-researcher
                                              │
                                              ▼
4. Agent Runtime receives blueprint, spawns agent via Claude Agent SDK
                                              │
                                              ▼
5. Agent runs, events flow to Runtime ──WebSocket──▶ Dashboard (real-time)
                                              │
                                              ▼
6. Agent completes, Runtime stores result
                                              │
                                              ▼
7. User invokes: ao-get-result my-agent ──HTTP GET──▶ Agent Runtime /sessions/{id}/result
```

### Context Sharing Between Agents

```
Agent A (researcher)                    Agent B (writer)
        │                                      │
        │ doc-push research.md                 │
        ▼                                      │
   Context Store ◀─────────────────────────────┤ doc-pull research.md
        │                                      │
        │ Returns document ID/URL              │
        ▼                                      ▼
   Agent A shares ID ──────────────────▶ Agent B retrieves content
```

---

## Data Flow

### Event Flow (Real-time Observability)

```
Claude Agent (running)
        │
        │ generates events (tool_call, message, error)
        ▼
Agent Runtime
        │
        ├──▶ Persist to SQLite database
        │
        └──▶ Broadcast via WebSocket ──▶ Dashboard (live updates)
                                    ──▶ Other subscribers
```

### Blueprint Resolution

```
ao-new session-name --agent my-blueprint
        │
        ▼
Agent Runtime
        │
        ├── 1. Check Agent Registry for "my-blueprint"
        │         GET /agents/my-blueprint
        │
        ├── 2. If found: merge blueprint config with session
        │
        ├── 3. If not found: return error "Blueprint not found"
        │
        └── 4. Spawn agent with resolved configuration
```

---

## Design Principles

1. **Servers are stateful, clients are stateless**
   All business logic and state lives in servers. CLI commands and MCP server are thin HTTP clients.

2. **Single responsibility per server**
   - Agent Runtime: session lifecycle and agent execution
   - Agent Registry: blueprint management
   - Context Store: document management

3. **Framework agnostic potential**
   Agent Runtime abstracts the Claude Agent SDK. Future adapters could support other agent frameworks.

4. **Real-time by default**
   WebSocket provides live updates. No polling required for status changes.

5. **Graceful degradation**
   Dashboard and CLI work independently. Server crashes don't lose session data (SQLite persistence).

---

## Port Summary

| Component | Port | Protocol |
|-----------|------|----------|
| Agent Runtime | 8765 | HTTP + WebSocket |
| Context Store | 8766 | HTTP |
| Agent Registry | 8767 | HTTP |
| Dashboard | 3000 | HTTP |

---

## Future Considerations

- **Multi-framework support**: Adapter pattern in Agent Runtime for OpenAI, LangChain, etc.
- **Authentication**: Add auth layer for production deployments
- **Horizontal scaling**: Stateless command layer already supports this; servers need shared storage
- **Session persistence**: Consider PostgreSQL for production scale
- **Blueprint versioning**: Version control for blueprints in Agent Registry
