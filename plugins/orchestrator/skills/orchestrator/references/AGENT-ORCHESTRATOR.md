# Agent Orchestrator

A lightweight orchestration layer for managing multiple Claude Code agent sessions through a simple command-line interface.

## Overview

The Agent Orchestrator provides a simplified abstraction for delegating work to Claude Code. Instead of manually managing session IDs, output files, and JSON parsing, you work with **named sessions** that can be created, resumed, and monitored through intuitive commands. Sessions can optionally use **agent blueprints** to provide specialized behavior and capabilities.

## Architecture

The orchestrator uses a **thin-client architecture**:

```
┌─────────────────┐         ┌───────────────────┐         ┌─────────────────┐
│  ao-* commands  │──HTTP──▶│ Agent Coordinator │◀──────▶│ Claude Agent SDK│
│  (thin clients) │         │   (Port 8765)     │         │                 │
└─────────────────┘         └───────────────────┘         └─────────────────┘
```

**Components:**
- **ao-* commands**: Stateless CLI tools that call backend APIs
- **Agent Coordinator** (port 8765): Unified service for session management, event tracking, and agent blueprint registry

## Core Concepts

### Sessions

A **session** is a named, persistent conversation with Claude Code. Each session:
- Has a unique name (e.g., `architect`, `reviewer`, `dev-agent`)
- Maintains conversation history across multiple interactions
- Can be paused and resumed at any time
- Operates independently from other sessions
- Optionally uses an **agent blueprint** for specialized behavior

Think of sessions as individual workstreams you can delegate tasks to and check back with later.

### Agent Blueprints

An **agent blueprint** is a reusable configuration that defines the behavior, expertise, and capabilities for sessions. Blueprints are optional - you can create generic sessions without them, or use blueprints to create specialized sessions with predefined behavior.

Blueprints are managed by the **Agent Coordinator** and can include:
- **Name**: Unique identifier
- **Description**: Human-readable description
- **System Prompt**: Role definition and behavioral guidelines
- **MCP Configuration**: External tool access via Model Context Protocol

#### Managing Blueprints

Blueprints can be managed via:
1. **Dashboard UI** at http://localhost:3000
2. **Agent Coordinator API** at http://localhost:8765
3. **ao-list-blueprints** command to view available blueprints

### Session States

Sessions can be in one of three states (returned by `ao-status`):
- **`not_existent`** - Session doesn't exist
- **`running`** - Session active, processing or ready for resume
- **`finished`** - Session complete, result available

## Commands

All commands are thin HTTP clients that call the backend APIs.

| Command | Description | API Call |
|---------|-------------|----------|
| `ao-start` | Start new session | POST /sessions |
| `ao-resume` | Resume existing session | POST /sessions/{id}/resume |
| `ao-status` | Check session state | GET /sessions/{id}/status |
| `ao-get-result` | Extract result | GET /sessions/{id}/result |
| `ao-list-sessions` | List all sessions | GET /sessions |
| `ao-list-blueprints` | List blueprints | GET /agents |
| `ao-show-config` | Show session config | GET /sessions/{id} |
| `ao-delete-all` | Delete all sessions | DELETE /sessions |

## Use Cases

### Multi-Session Workflows

Coordinate multiple specialized sessions:
```bash
# List available blueprints
uv run --script commands/ao-list-blueprints

# Architecture session
uv run --script commands/ao-start architect --agent system-architect -p "Design microservices for e-commerce"

# Development session
uv run --script commands/ao-start developer --agent senior-developer -p "Implement the user service"

# Review session
uv run --script commands/ao-start reviewer --agent security-reviewer -p "Review the implementation"
```

### Long-Running Background Tasks

Delegate time-consuming tasks:
- Large codebase analysis
- Documentation generation
- Multi-step refactoring
- Test suite creation

### Iterative Refinement

Resume sessions to continue previous work:
```bash
# Initial work
uv run --script commands/ao-start docs --agent documentation-expert -p "Create API documentation"

# Refinement
uv run --script commands/ao-resume docs -p "Add authentication examples"

# Enhancement
uv run --script commands/ao-resume docs -p "Include error handling section"
```

## Features

### Session Management
- Create sessions with descriptive names
- Resume sessions by name
- List all sessions with status
- Optional blueprint associations

### Flexible Prompting
- Direct prompt via `-p` flag
- File-based prompts via stdin piping
- Large prompt support

### State Tracking
- Session status visibility
- Blueprint association tracking
- Conversation history persistence

### Real-time Observability
- Event streaming via SSE
- Tool call tracking
- Dashboard visualization

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_ORCHESTRATOR_API_URL` | `http://localhost:8765` | Agent Orchestrator API URL (sessions + blueprints) |
| `AGENT_ORCHESTRATOR_OBSERVABILITY` | `true` | Enable event capture |

See `ENV_VARS.md` for complete reference.

## Design Philosophy

**Simplicity First**
Named sessions instead of UUIDs, intuitive commands, sensible defaults.

**Thin Clients**
Commands are stateless HTTP clients. All state lives in backend servers.

**API-First**
All functionality available via REST APIs. CLI, Dashboard, and MCP Server all use the same APIs.

**Composability**
Clean input/output separation enables chaining and automation.

## Related Documentation

- **SKILL.md** - Usage guide
- **ENV_VARS.md** - Environment configuration
