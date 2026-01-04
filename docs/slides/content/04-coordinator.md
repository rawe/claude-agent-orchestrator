---
id: coordinator
title: "Agent Coordinator"
subtitle: "The central brain that knows everything"
accentColor: coordinator
---

## What It Is

The Agent Coordinator is the central server that orchestrates the entire multi-agent system. It runs on port **8765** and maintains all state.

## Internal Components

- **Sessions** - Persistent agent conversations
- **Agent Runs** - Tracking of running and queued work
- **Blueprints** - Agent configuration templates
- **Runners** - Registry of connected execution workers
- **SSE Events** - Real-time event broadcasting
- **SQLite DB** - Persistent storage

## Key Features

### Session Management
Creates and tracks persistent agent conversations. Each session maintains its own history and context.

### Agent Runs Queue
Queues work for runners to pick up and execute. Handles scheduling, prioritization, and status tracking.

### Real-time Events
Broadcasts updates via Server-Sent Events (SSE). Clients can subscribe to live updates for monitoring.

### Authentication
Optional OIDC with Auth0 integration. Can run without auth for development or internal use.
