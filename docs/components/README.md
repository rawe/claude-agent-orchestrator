# Component Documentation

Technical reference documentation for individual services and applications in the Agent Orchestrator framework.

## Server Components

### [agent-coordinator/](./agent-coordinator/README.md)
The central coordination server (port 8765) that manages sessions, runs, blueprints, and agent communication. Includes REST/SSE API reference, data models, and database schema.

### Agent Runner
Execution bridge that polls for runs and spawns agent processes. See [ARCHITECTURE.md](../ARCHITECTURE.md#agent-runner-architecture) for architecture details and the main [servers/agent-runner/README.md](../../servers/agent-runner/README.md) for usage.

### [context-store/](./context-store/README.md)
Document management system (port 8766) for persistent context sharing between agent sessions. Includes server architecture, CLI commands reference, and MCP server integration.

## Client Components

### Dashboard
React web UI for monitoring sessions, runners, and agents. See [apps/dashboard/README.md](../../apps/dashboard/README.md).

## Note on Component Docs

Detailed component documentation lives closest to the source code. This folder contains deep-dive technical references for the Agent Coordinator specifically, as it is the core backend service. Other components have README files in their respective directories.
