---
id: architecture
title: "Architecture Overview"
subtitle: "How the four components work together"
---

## The Four Components

### Agent Coordinator (Port 8765)

The **central server** that manages everything:
- Sessions
- Runs
- Blueprints

### Agent Runner

The **work executor** that:
- Polls the Coordinator for pending work
- Reports progress and results back

### Context Store (Port 8766)

**Shared documents** storage that agents can store to and retrieve from.

### Dashboard (Port 3000)

**Real-time UI** for monitoring and interaction.

## Communication Flow

1. **Dashboard** communicates with Coordinator via HTTP, receives updates via SSE (Server-Sent Events)
2. **Runner** polls Coordinator for work, Coordinator dispatches runs to Runner
3. **Runner** spawns Claude Code as a subprocess using the Agent SDK
4. **Claude Code** stores and retrieves documents from Context Store
