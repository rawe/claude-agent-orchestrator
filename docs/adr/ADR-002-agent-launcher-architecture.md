# ADR-002: Agent Launcher Architecture

**Status:** Accepted
**Date:** 2025-12-12
**Decision Makers:** Architecture Review

## Context

The Agent Orchestrator must execute agent sessions (Claude Code processes), which require:
1. Access to the host filesystem and installed agent frameworks
2. Spawning subprocesses with environment variables
3. Running on machines where AI frameworks (Claude Agent SDK) are installed

These requirements conflict with containerization goals for the Agent Coordinator.

## Decision

**Separate Agent Coordinator (orchestration) from Agent Launcher (execution)** with asynchronous job distribution.

### Component Responsibilities

| Component | Location | Purpose |
|-----------|----------|---------|
| **Agent Coordinator** | Containerizable | Orchestration, job queue, persistence |
| **Agent Launcher** | Host machine | Job polling, subprocess management |
| **Executors** | `claude-code/` | Framework-specific execution (ao-start, ao-resume) |

### Communication Protocol

- **Long-polling HTTP**: Launcher calls `GET /launcher/jobs?launcher_id=xxx`
- **30s poll timeout**: Connection held until job available or timeout
- **Status reporting**: `POST /launcher/jobs/{job_id}/{started|completed|failed}`

## Rationale

### Why Separate Coordinator and Launcher?

**Agent processes cannot run in containers** because they need:
- Host filesystem access (read/write project files)
- Framework binaries (Claude Agent SDK)
- Environment inheritance (PATH, credentials, SSH keys)

**Separating allows:**
- Agent Coordinator to be containerized (Docker, Kubernetes)
- Launchers to run on any host with frameworks installed
- Distributed execution across multiple machines

### Why Long-Polling Over WebSocket?

- Simpler implementation (no WebSocket state management)
- Works through HTTP proxies/firewalls
- Atomic job claiming with `threading.Lock`

## Consequences

### Positive
- Agent Coordinator is containerizable
- Distributed execution across multiple hosts
- Framework-agnostic core (future LangChain, AutoGen support)

### Negative
- Network dependency between Agent Coordinator and launcher
- Two processes to run (Agent Coordinator + launcher)

## References

- [ARCHITECTURE.md](../ARCHITECTURE.md)
- [JOB_EXECUTION_FLOW.md](../agent-coordinator/JOB_EXECUTION_FLOW.md)
