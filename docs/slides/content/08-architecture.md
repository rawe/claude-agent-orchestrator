---
id: architecture
title: "Architecture Overview"
subtitle: "The core components and their communication"
---

## The Core Components

### Agent Coordinator (Port 8765)

The **central server** and **trust anchor**:
- Manages Sessions, Runs, Blueprints
- Issues **scope badges** (signed tokens) for external service access
- Determines what data each run can access

### Agent Runner

The **work executor** that:
- Polls the Coordinator for pending work
- Receives scope badges with each run assignment
- Reports progress and results back

### Executor (e.g. Claude Code)

The **AI agent process** that:
- Executes tasks using the Claude Agent SDK
- Accesses external services with scoped permissions
- Cannot manipulate scope - it's embedded in the badge

### External Services (via MCP)

**Scoped data access** through MCP servers:
- **Context Store** (Port 8766) - Shared documents
- + other MCP services (extensible pattern)

### Dashboard (Port 3000)

**Real-time UI** for monitoring and interaction.

## Scoped Access Pattern

1. Coordinator generates **scope badge** (signed token) when run is created
2. Badge contains: namespace, filters, permissions
3. Badge travels: Coordinator → Runner → Claude Code → MCP → External Services
4. **External Services trust Coordinator** - validate badge signature
5. Services return only data permitted by the badge scope
6. **LLM cannot escape scope** - embedded in badge, not in tool parameters

## Communication Flow

1. **Dashboard** ↔ Coordinator via HTTP/SSE
2. **Runner** polls Coordinator, receives runs **with scope badge**
3. **Runner** spawns Executor (e.g. Claude Code), passes badge
4. **Executor** accesses external services via MCP, presenting badge
5. **External Services** validate badge, filter data by scope
