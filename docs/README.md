# Agent Orchestrator Framework - Architecture Diagrams

This directory contains comprehensive architectural diagrams for the Agent Orchestrator Framework (AOF), visualizing different aspects of the framework's design, structure, and operation.

## Overview

The Agent Orchestrator Framework is a multi-level system for orchestrating specialized Claude Code agent sessions. These diagrams help you understand:
- How the three usage levels work
- Where MCP integration fits
- How agents are defined and used
- How sessions flow through the system
- How data is organized and persisted

## Diagram Index

### 1. [Three Usage Levels](./01-three-usage-levels.md)
**Architectural Focus**: Progressive Enhancement & Integration Scope

Visualizes the three-tier usage model of AOF:
- **Level 1**: Core Framework Plugin (Claude Code only, direct control)
- **Level 2**: Subagents Extension Plugin (Claude Code only, delegation-based)
- **Level 3**: MCP Server Protocol (Any MCP client, universal access)

Shows dependency relationships, user interaction models, and the shared core foundation (`agent-orchestrator.sh` script).

**Key Concepts**: Progressive enhancement, dependency chain, integration scope

---

### 2. [MCP Client Integration](./02-mcp-client-integration.md)
**Architectural Focus**: Level 3 Client Ecosystem & Configuration

Illustrates how different MCP-compatible clients integrate with the Agent Orchestrator:
- Claude Desktop (GUI application)
- Claude Code CLI (command-line)
- Future MCP-compatible tools

Covers client-specific configuration requirements, unified tool interface, and the benefits of protocol abstraction.

**Key Concepts**: Multi-client support, MCP protocol, configuration patterns, tool standardization

---

### 3. [Core Components and Architecture](./03-core-components-architecture.md)
**Architectural Focus**: Layered System Design & Component Relationships

Displays the complete component architecture showing:
- User interface layer (three entry points)
- Interface layer (plugins and MCP server)
- Core orchestration engine (bash script)
- Claude Code integration layer
- Data persistence layer

Maps the flow from user interaction through all layers to data storage.

**Key Concepts**: Layered architecture, separation of concerns, unified backend, component responsibilities

---

### 4. [Session Lifecycle and Data Flow](./04-session-lifecycle-dataflow.md)
**Architectural Focus**: State Management & Execution Flow

Presents the complete lifecycle of an agent session from creation to completion:
- Session request and validation
- Session creation and initialization
- Active execution and processing
- Result extraction and storage
- Resume operations for continued work

Shows state transitions, data flow at each stage, and error handling paths.

**Key Concepts**: State machine, lifecycle management, data flow, resume capability, persistence strategy

---

### 5. [Agent Definition Structure](./05-agent-definition-structure.md)
**Architectural Focus**: Agent Composition & Configuration Model

Details how agents are structured and composed:
- Required files (`agent.json`)
- Optional files (`agent.system-prompt.md`, `agent.mcp.json`)
- Convention-based discovery
- Loading process and session integration

Explains the separation between reusable agent blueprints and specific session instances.

**Key Concepts**: Convention over configuration, agent composition, file structure, separation of concerns

---

### 6. [Directory Structure and File Organization](./06-directory-structure.md)
**Architectural Focus**: File System Layout & Storage Strategy

Visualizes the complete directory structure and file organization:
- Project-relative structure (`.agent-orchestrator/`)
- Agent storage (`agents/` directory)
- Session storage (`sessions/` directory)
- File types, formats, and purposes
- Configuration flexibility via environment variables

Includes detailed file format specifications and lifecycle information.

**Key Concepts**: File-based storage, directory isolation, human-readable formats, backup strategy

---

### 7. [MCP Server Integration and Tool Flow](./07-mcp-server-tool-flow.md)
**Architectural Focus**: Request Flow & MCP Protocol Implementation

Illustrates the complete request flow through the MCP server:
- User interaction to MCP client
- MCP protocol communication
- Zod validation layer
- Script invocation patterns
- Claude CLI integration
- File system operations

Shows sequence diagrams for all 5 MCP tools: `list_agents`, `start_agent`, `resume_agent`, `list_sessions`, and `clean_sessions`.

**Key Concepts**: Multi-layer flow, type safety, tool implementation, validation, response formatting

---

## How to Use These Diagrams

### For New Users
Start with these diagrams in order:
1. **Three Usage Levels** - Understand your options
2. **MCP Client Integration** - See how clients connect
3. **Core Components** - Learn the overall architecture

### For Developers
Focus on these for implementation details:
1. **Core Components** - Understand the layers
2. **Session Lifecycle** - Learn the execution flow
3. **MCP Server Tool Flow** - See the request handling

### For Agent Creators
These diagrams help you create agents:
1. **Agent Definition Structure** - Learn agent composition
2. **Directory Structure** - Understand file organization
3. **Session Lifecycle** - See how agents are used

### For System Integrators
For MCP integration and deployment:
1. **MCP Client Integration** - Configuration patterns
2. **MCP Server Tool Flow** - Request flow details
3. **Directory Structure** - Storage customization

## Architectural Principles

These diagrams reflect the core principles of AOF:

### 1. Progressive Enhancement
Start simple (Level 1), add complexity as needed (Level 2), or use universal protocol (Level 3).

### 2. Separation of Concerns
- **Agents**: Reusable blueprints
- **Sessions**: Specific instances
- **Interface**: User interaction layer
- **Core**: Orchestration logic
- **Storage**: State persistence

### 3. Convention Over Configuration
Standardized naming, predictable structure, discovery by convention, minimal required configuration.

### 4. Unified Core Implementation
All usage levels use the same `agent-orchestrator.sh` script, ensuring consistency across integration modes.

### 5. File-Based Persistence
Human-readable formats (JSON, JSONL, Markdown), no database required, version-control friendly, transparent state.

## Diagram Format

All diagrams use [Mermaid](https://mermaid.js.org/), a text-based diagramming language that renders in:
- GitHub and GitLab
- Most modern markdown viewers
- Documentation sites
- IDEs with Mermaid support

## Additional Resources

- **[Main README](../README.md)**: Framework overview and quick start
- **[Level 1 Documentation](../agent-orchestrator/README.md)**: Core framework plugin
- **[Level 2 Documentation](../agent-orchestrator-subagents/README.md)**: Subagents extension
- **[Level 3 Documentation](../agent-orchestrator-mcp-server/README.md)**: MCP server implementation
- **[Setup Guide](../agent-orchestrator-mcp-server/SETUP_GUIDE.md)**: Integration scenarios
- **[Getting Started](../agent-orchestrator-mcp-server/GETTING_STARTED.md)**: Quick setup

## Contributing

When adding new diagrams:
1. Use Mermaid format for consistency
2. Create a standalone markdown file
3. Include architectural aspects covered
4. Update this index with description
5. Follow the existing naming convention

## Questions?

If these diagrams raise questions or you need clarification on any architectural aspect, please:
- Review the detailed documentation in each component's README
- Check the technical reference documentation
- Open an issue for discussion

---

**Last Updated**: 2025-01-15
**Version**: 1.0
**Diagrams**: 7 comprehensive architectural views
