# Agent Orchestrator - Core Framework

The core Agent Orchestrator Framework (AOF) plugin for Claude Code. Provides the foundational `agent-orchestrator.sh` script, slash commands, and skills for orchestrating specialized Claude Code agent sessions.

## Overview

The Agent Orchestrator is a framework for creating and managing specialized Claude Code agent sessions. It allows you to:
- Launch multiple Claude Code sessions programmatically
- Configure agents with custom system prompts and MCP server configurations
- Manage long-running tasks in isolated sessions
- Extract and process results from completed agents
- Create reusable agent definitions for common tasks

This is the **core framework** that provides the low-level orchestration functionality.

## What's Included

### 1. Core Script
**Location**: `skills/agent-orchestrator/agent-orchestrator.sh`

The foundational bash script (1,203 lines) that handles:
- Agent session lifecycle management
- Agent definition loading
- MCP server configuration injection
- Session state persistence
- Result extraction and formatting

### 2. Slash Commands

Four slash commands for interacting with the framework:

- **`/agent-orchestrator-init`**: Initialize the agent orchestrator in your conversation
- **`/agent-orchestrator-create-agent`**: Create new agent definitions
- **`/agent-orchestrator-create-runtime-report`**: Generate runtime analysis reports
- **`/agent-orchestrator-extract-token-usage`**: Extract token usage statistics from sessions

### 3. Skill Documentation
**Location**: `skills/agent-orchestrator/SKILL.md`

Comprehensive skill definition with usage instructions and examples.

### 4. Reference Documentation
**Location**: `skills/agent-orchestrator/references/AGENT-ORCHESTRATOR.md`

Detailed technical documentation of the framework architecture, including:
- How agent sessions work
- Agent definition format
- MCP server configuration
- Session directory structure
- Advanced usage patterns

### 5. Examples
**Location**: `skills/agent-orchestrator/example/`

Example agent definitions and usage scenarios to help you get started.

## Installation

Install this plugin by adding it to your Claude Code configuration. The plugin will be available in your Claude Code sessions.

## Usage

### Level 1: Direct Usage (Command-Line Style)

Use the slash commands and skills directly:

1. Initialize in your conversation:
   ```
   /agent-orchestrator-init
   ```

2. Use the skill to launch agents:
   ```
   Use the agent-orchestrator skill to create a new session called "code-review" and review the changes in src/
   ```

3. Create custom agent definitions:
   ```
   /agent-orchestrator-create-agent
   ```

### Key Concepts

**Agent Definitions**:
Agent definitions are markdown files in `.agent-orchestrator/agents/` that define specialized agent configurations. They can include:
- Custom system prompts
- Specialized instructions
- MCP server configurations
- Capability restrictions

**Sessions**:
Sessions are stored in `.agent-orchestrator/sessions/` and contain:
- Unique session ID
- Agent configuration
- Execution state
- Results and metadata

**MCP Configuration**:
The framework allows you to configure different MCP servers for different agent types, enabling specialized capabilities per agent.

## Extensions

For a higher-level, delegation-based interface, install the **agent-orchestrator-subagents** plugin. It provides pre-configured Claude Code subagents that simplify common orchestration tasks.

## Architecture

The Agent Orchestrator Framework consists of three layers:

1. **This plugin (Level 1)**: Core framework with direct CLI-style access
2. **Subagents plugin (Level 2)**: Higher-level delegation-based interface
3. **MCP Server (Level 3)**: Protocol-level abstraction for any MCP-compatible system

See the [main repository README](../README.md) for details on all three usage levels.

## Technical Details

### Directory Structure

```
.agent-orchestrator/
├── agents/                    # Agent definition files (.md)
│   └── my-agent.md           # Custom agent configurations
└── sessions/                  # Session data
    └── session-name/         # Individual session directory
        ├── session-id.txt    # Unique session identifier
        ├── config.json       # Session configuration
        └── result.md         # Agent execution results
```

### Agent Definition Format

Agent definitions are markdown files with frontmatter:

```markdown
---
name: code-reviewer
description: Reviews code for best practices and improvements
---

# System Prompt

You are a code review expert...

# Instructions

1. Review the code
2. Identify issues
3. Suggest improvements
```

### Script API

The `agent-orchestrator.sh` script provides several commands:

- `start`: Create a new agent session
- `resume`: Continue an existing session
- `list-agents`: Show available agent definitions
- `list-sessions`: Show active sessions
- `clean`: Remove all sessions

## Related Components

- **[agent-orchestrator-subagents](../agent-orchestrator-subagents/README.md)**: Extension plugin with pre-configured subagents
- **[agent-orchestrator-mcp-server](../agent-orchestrator-mcp-server/README.md)**: MCP server implementation
- **[Framework Documentation](skills/agent-orchestrator/references/AGENT-ORCHESTRATOR.md)**: Technical architecture documentation
