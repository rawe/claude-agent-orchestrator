# Agent Orchestrator Framework - Terminology Decisions

This document tracks terminology decisions for the framework. Each term has a dedicated section with the old name, new name, and rationale. Detailed renaming analysis for each term is in separate `terminology_<term>_renaming.md` files.

---

## 1. Agent Runtime → Agent Coordinator

**Old Term:** Agent Runtime
**New Term:** Agent Coordinator
**Decision Date:** 2025-12-17

### Definition

The central FastAPI server (port 8765) that:
- Manages agent sessions (CRUD, lifecycle, persistence)
- Queues and dispatches runs to Agent Runners
- Maintains the launcher/runner registry with health monitoring
- Processes callbacks for parent-child session coordination
- Stores and serves agent blueprints
- Broadcasts real-time events via WebSocket
- Persists all data to SQLite

### Rationale

"Runtime" implies an execution environment where code runs. This component doesn't execute agents—it **coordinates** them. It's a control plane that orchestrates communication between:
- CLI commands (ao-*)
- Agent Runners (formerly Launchers)
- Dashboard
- MCP servers

"Coordinator" accurately describes its role: coordinating sessions, runs, runners, and callbacks.

### Renaming Analysis

See: [terminology_agent_runtime_renaming.md](./terminology_agent_runtime_renaming.md)

---

## 2. Agent Launcher → Agent Runner

**Old Term:** Agent Launcher
**New Term:** Agent Runner
**Decision Date:** 2025-12-17

### Definition

Standalone process that:
- Polls Agent Coordinator for pending runs
- Claims runs atomically (prevents duplicate execution)
- Executes runs via framework-specific adapters (spawning subprocesses)
- Reports run status (started, completed, failed, stopped)
- Handles stop commands by terminating running processes
- Maintains heartbeat for health monitoring
- Supports concurrent run execution

### Rationale

"Launcher" implies only starting things, but this component does much more—it runs, monitors, and reports. The GitLab Runner analogy is apt: runners poll for work, execute it, and report back.

"Runner" is industry-standard terminology (GitLab Runner, GitHub Actions Runner) and pairs naturally with "Runs" (the renamed Jobs).

### Renaming Analysis

See: [terminology_agent_launcher_renaming.md](./terminology_agent_launcher_renaming.md)

---

## 3. Jobs / Jobs API → Agent Runs / Runs API

**Old Term:** Jobs, Jobs API
**New Term:** Agent Runs, Runs API
**Decision Date:** 2025-12-17

### Definition

An Agent Run is a single execution of a session. Types:
- `start` - First run, creates a new session
- `resume` - Subsequent run, continues existing session
- `stop` - Termination signal for a running session

The Runs API queues, dispatches, and tracks these executions.

### Relationship

```
Session (persistent entity)
├── Agent Run 1 (start)
├── Agent Run 2 (resume)
├── Agent Run 3 (resume)
└── ...
```

Sessions are persistent conversations with state and history. Agent Runs are discrete executions within a session.

### Rationale

"Job" is a generic term that doesn't capture the relationship between sessions and their executions. A session can have multiple runs over its lifetime.

"Agent Run" clarifies:
- What is being run (an agent session)
- The transient nature (one execution vs persistent session)
- Pairs naturally with "Agent Runner" (runners execute runs)

### Renaming Analysis

See: [terminology_jobs_renaming.md](./terminology_jobs_renaming.md)

---

## 4. Blueprints (Keep)

**Term:** Blueprints, Agent Blueprints
**Decision:** Keep as-is
**Decision Date:** 2025-12-17

### Definition

Reusable agent configurations stored in `config/agents/{name}/`. A blueprint defines:
- `agent.json` - Metadata (name, description, tags)
- `agent.system-prompt.md` - Role definition, expertise, behavior instructions
- `agent.mcp.json` - MCP server configuration for agent capabilities
- `README.md` - Setup instructions (optional)

Blueprints are registered in the Agent Coordinator and can be instantiated into sessions.

### Relationship

```
Blueprint (template)
    ↓ instantiate
Session (instance)
    ↓ execute
Agent Run (execution)
```

### Rationale for Keeping

"Blueprint" accurately conveys:
- A design/template that gets instantiated
- Reusability across multiple sessions
- The distinction between definition (blueprint) and instance (session)

No rename needed.

---

## 5. Executors (Keep)

**Term:** Executors
**Decision:** Keep as-is
**Decision Date:** 2025-12-17

### Definition

Framework-specific code that spawns the actual agent process. Located in `servers/agent-runner/executors/{framework}/`. Each executor:
- Receives run parameters from the Agent Runner
- Spawns the framework-specific subprocess (e.g., Claude Code via `ao-start`, `ao-resume`)
- Returns execution results to the Runner

Current implementation: `executors/claude-code/` (uses Claude Agent SDK)

### Relationship

```
Agent Runner (framework-agnostic)
    ↓ delegates to
Executor (framework-specific)
    ↓ spawns
Claude Code / Other AI Framework
```

### Rationale for Keeping

"Executor" is standard terminology for the component that actually executes work. The architecture intentionally separates:
- **Runner**: Framework-agnostic job management
- **Executor**: Framework-specific execution

This enables future support for other AI frameworks (LangChain, AutoGen, etc.) by adding new executors.

No rename needed.

---

## 6. Sessions (Keep)

**Term:** Sessions, Agent Sessions
**Decision:** Keep as-is
**Decision Date:** 2025-12-17

### Definition

Named, persistent agent conversations. A session:
- Has a unique `session_name` identifier
- Maintains conversation history and state
- Can be started, paused, resumed, and stopped
- Is instantiated from a Blueprint
- Can have multiple Agent Runs over its lifetime

### Relationship

```
Blueprint (template)
    ↓ instantiate
Session (persistent instance)
    ├── Run 1 (start)
    ├── Run 2 (resume)
    └── Run 3 (resume)
```

### Key Properties

- **Persistence**: Sessions survive across runs; state is maintained
- **Identity**: Each session has a unique name
- **Lifecycle**: created → running → idle → resumed → completed
- **Parent-child**: Sessions can spawn child sessions with callbacks

### Rationale for Keeping

"Session" is industry-standard terminology for persistent conversations. It clearly conveys:
- Continuity across multiple interactions
- State management
- The distinction from transient "runs"

No rename needed.

---

## 7. Context Store (Keep)

**Term:** Context Store
**Decision:** Keep as-is
**Decision Date:** 2025-12-17

### Definition

Separate FastAPI server (port 8766) for document management. Provides:
- Document storage and retrieval
- Tag-based document organization and queries
- Document relations (parent-child, peer)
- Optional semantic search via embeddings
- Two-phase document creation (placeholder → content)

### Purpose

Enables agents to share context across sessions. An orchestrating agent can:
1. Store research results, findings, or artifacts
2. Query documents by tags or semantic similarity
3. Pass context to child agents via document references

### Components

- **Server**: `servers/context-store/`
- **Plugin**: `plugins/context-store/` (doc-* CLI commands)
- **MCP Server**: `mcps/context-store/` (MCP tools for agents)

### Rationale for Keeping

"Context Store" emphasizes the purpose: providing relevant context to AI agents. While "Document Store" would be more technically precise, "Context Store" better conveys:
- The AI/agent-centric purpose
- Documents as context for agent operations
- Integration with the orchestration framework

No rename needed.

---

## Summary

### Decision Overview

| # | Old Term | New Term | Action | Renaming Doc |
|---|----------|----------|--------|--------------|
| 1 | Agent Runtime | **Agent Coordinator** | RENAME | [terminology_agent_runtime_renaming.md](./terminology_agent_runtime_renaming.md) |
| 2 | Agent Launcher | **Agent Runner** | RENAME | [terminology_agent_launcher_renaming.md](./terminology_agent_launcher_renaming.md) |
| 3 | Jobs / Jobs API | **Agent Runs / Runs API** | RENAME | [terminology_jobs_renaming.md](./terminology_jobs_renaming.md) |
| 4 | Blueprints | Blueprints | KEEP | - |
| 5 | Executors | Executors | KEEP | - |
| 6 | Sessions | Sessions | KEEP | - |
| 7 | Context Store | Context Store | KEEP | - |

### Complete Terminology Glossary

| Term | Definition |
|------|------------|
| **Agent Coordinator** | Central server (port 8765) managing sessions, runs, runners, blueprints, and callbacks |
| **Agent Runner** | Standalone process polling for runs, executing them via executors, reporting status |
| **Agent Run** | Single execution of a session (start, resume, or stop) |
| **Blueprint** | Reusable agent configuration (system prompt, MCP config, metadata) |
| **Session** | Named, persistent agent conversation with state and history |
| **Executor** | Framework-specific code that spawns the actual agent process |
| **Context Store** | Document management server for sharing context between agents |
| **Runs API** | API for creating, querying, and managing agent runs |

### Conceptual Hierarchy

```
Blueprint (template)
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

### Estimated Renaming Effort

| Component | Changes | Priority |
|-----------|---------|----------|
| Agent Runtime → Coordinator | ~150-200 | High |
| Agent Launcher → Runner | ~111 | High |
| Jobs → Runs | ~182 | High |
| **Total** | **~450+** | - |

---
