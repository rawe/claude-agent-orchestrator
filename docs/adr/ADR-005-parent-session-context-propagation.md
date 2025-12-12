# ADR-005: Parent Session Context Propagation

**Status:** Accepted
**Date:** 2025-12-12
**Decision Makers:** Architecture Review

## Context

Callback mechanism requires child agents to know their parent's identity. Two execution modes need different propagation:
1. **stdio-based**: MCP servers as subprocesses
2. **HTTP-based**: MCP servers as separate services

## Decision

**Two-mechanism approach:**

1. **Environment Variable** (`AGENT_SESSION_NAME`): For stdio execution
2. **HTTP Header** (`X-Agent-Session-Name`): For HTTP MCP servers
3. **Placeholder** (`${AGENT_SESSION_NAME}`): Template pattern in config

### Flow

**stdio**: Launcher sets env var → subprocess inherits → ao-start reads it

**HTTP**: Config has placeholder → ao-start replaces → Claude sends header → MCP extracts

## Rationale

### Why Two Mechanisms?

- Environment variables alone insufficient for HTTP MCP servers
- HTTP headers alone insufficient for stdio MCP servers
- Transparent to agents (no explicit parameter passing)

## Affected Components

| Component | Responsibility |
|-----------|---------------|
| **Agent Launcher** | Sets `AGENT_SESSION_NAME` env var |
| **ao-start/ao-resume** | Reads env, passes to Sessions API, replaces placeholders |
| **MCP Servers (stdio)** | Propagates env to child subprocess |
| **MCP Servers (HTTP)** | Extracts header, sets env for subprocess |
| **Sessions API** | Stores `parent_session_name` |

## Consequences

### Positive
- Transparent to agents
- Works for both execution modes
- Declarative config

### Negative
- Two propagation paths to understand
- Magic strings require documentation

## References

- [agent-callback-architecture.md](../features/agent-callback-architecture.md)
