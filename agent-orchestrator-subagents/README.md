# Agent Orchestrator Subagents

Pre-configured Claude Code subagents for the Agent Orchestrator Framework (AOF).

## Overview

This plugin provides convenient Claude Code subagents that allow you to launch and manage orchestrated agents without directly using the low-level Python `ao-*` commands. It extends the core Agent Orchestrator Framework with a higher-level, more user-friendly interface.

## Requirements

**This plugin requires the `agent-orchestrator` plugin to be installed.**

The subagents in this plugin depend on the core `agent-orchestrator` plugin, which provides:
- Python `ao-*` orchestration commands
- Core orchestration functionality
- Session management
- Agent definition handling

## What's Included

This plugin provides two specialized subagents:

### 1. Orchestrated Agent Launcher
**Location**: `agents/orchestrated-agent-launcher.md`

A Claude Code subagent that simplifies launching new orchestrated agent sessions. Instead of manually using the `ao-*` commands, you can use this subagent to:
- Create new agent sessions with natural language
- Launch specialized agents by name
- Start generic agents for custom tasks
- Handle session naming and configuration automatically

### 2. Orchestrated Agent Lister
**Location**: `agents/orchestrated-agent-lister.md`

A Claude Code subagent for discovering and managing orchestrated agents. Use this subagent to:
- List all available agent definitions
- View active and completed sessions
- Get information about session status
- Manage session lifecycle

## Installation

1. **Install the core plugin first**:
   ```bash
   # Make sure agent-orchestrator plugin is installed
   ```

2. **Install this plugin**:
   ```bash
   # Add this plugin to your Claude Code configuration
   ```

3. **Verify installation**:
   The subagents should appear in your Claude Code session and be available for delegation.

## Usage

### Using the Agent Launcher Subagent

You can delegate tasks to the launcher subagent to create new orchestrated agents:

```
Use the orchestrated-agent-launcher subagent to create a new code review session
```

The subagent will handle:
- Generating an appropriate session name
- Selecting the right agent definition (if available)
- Launching the agent session
- Returning results to you

### Using the Agent Lister Subagent

Delegate to the lister subagent to manage your orchestrated agents:

```
Use the orchestrated-agent-lister subagent to show me all available agents
```

The subagent will:
- Query the Agent Orchestrator Framework
- Format the results in a readable way
- Provide information about sessions and agents

## Benefits

### Level 2 of AOF Usage

This plugin represents **Level 2** of the Agent Orchestrator Framework usage model:

- **Level 1**: Using the core `agent-orchestrator` plugin with slash commands
- **Level 2**: Using the `agent-orchestrator-subagents` extension for delegation-based workflow (this plugin)
- **Level 3**: Using the MCP server abstraction with any MCP-compatible system

### Advantages

- **Simpler workflow**: Delegate tasks instead of running commands
- **Natural language**: Describe what you want instead of crafting command syntax
- **Automatic handling**: Session management and agent selection handled for you
- **Better integration**: Works seamlessly with Claude Code's delegation model

## Related Documentation

- [Agent Orchestrator Framework Documentation](../agent-orchestrator/skills/agent-orchestrator/references/AGENT-ORCHESTRATOR.md)
- [Core Plugin README](../agent-orchestrator/README.md)
- [MCP Server Implementation](../agent-orchestrator-mcp-server/README.md)
