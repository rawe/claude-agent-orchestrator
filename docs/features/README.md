# Features

Documentation for implemented features of the Agent Orchestrator. Each document explains what a feature does, why it exists, and how it works.

## Core Features

### [Executor Profiles](./executor-profiles.md)
Named executor configurations that specify permission modes, model selection, and setting sources. Enables demand-based routing to runners with matching profiles.

### [Runner Gateway](./runner-gateway.md)
Local HTTP server within the Agent Runner that decouples executors from the Coordinator. Handles authentication, enriches requests with runner-owned data, and maintains a security boundary.

### [Capabilities System](./capabilities-system.md)
Reusable knowledge packages that bundle MCP server configurations with domain documentation. Allows multiple agents to share external system access and ontology definitions.

### [Agent Management](./agent-management.md)
System for defining and managing agent blueprints with tag-based filtering. Tags enable discovery and categorization for both end-user and orchestrator use cases.

### [Agent Callback Architecture](./agent-callback-architecture.md)
Callback-driven orchestration where child agents notify parents upon completion. Enables resource-efficient multi-agent coordination without polling.

### [Session Stop Command](./session-stop-command.md)
Immediate termination of running agent sessions with SIGTERM/SIGKILL escalation. Propagated from Coordinator to Runner via event signaling.

## Work in Progress

### [Unified Session-Run View](./unified-session-run-view.md)
Design exploration for consolidating Sessions and Runs into a unified dashboard view. Documents six architectural approaches under consideration.

### [Session Stop Integration](./session-stop-integration-todo.md)
Remaining dashboard integration tasks for the session stop feature.
