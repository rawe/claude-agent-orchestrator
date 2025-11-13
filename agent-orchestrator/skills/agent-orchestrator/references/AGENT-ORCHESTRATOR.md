# Agent Orchestrator

A lightweight orchestration layer for managing multiple Claude Code agent sessions through a simple command-line interface.

## Overview

The Agent Orchestrator provides a simplified abstraction for delegating work to Claude Code. Instead of manually managing session IDs, output files, and JSON parsing, you work with **named sessions** that can be created, resumed, and monitored through intuitive commands. Sessions can optionally use **agent definitions** to provide specialized behavior and capabilities.

## Core Concepts

### Sessions

A **session** is a named, persistent conversation with Claude Code. Each session:
- Has a unique name (e.g., `architect`, `reviewer`, `dev-agent`)
- Maintains conversation history across multiple interactions
- Can be paused and resumed at any time
- Operates independently from other sessions
- Optionally uses an **agent** definition for specialized behavior

Think of sessions as individual workstreams or conversations you can delegate tasks to and check back with later.

### Agents (Definitions)

An **agent** is a reusable configuration that defines the behavior, expertise, and capabilities for sessions. Agents are optional - you can create generic sessions without them, or use agents to create specialized sessions with predefined behavior.

#### Agent Structure

Each agent is organized in its own directory within `.agent-orchestrator/agents/`. Each agent directory must match the agent name and contains:

```
.agent-orchestrator/agents/
└── <agent-name>/
    ├── agent.json                 # Required: Agent configuration
    ├── agent.system-prompt.md     # Optional: System prompt by convention
    └── agent.mcp.json             # Optional: MCP configuration by convention
```

**1. agent.json** (Required)
```json
{
  "name": "browser-tester",
  "description": "Specialist in browser automation and end-to-end testing using Playwright"
}
```
- `name`: Agent identifier (must match folder name)
- `description`: Human-readable description

**2. agent.system-prompt.md** (Optional)
Markdown file containing the agent's role definition, expertise areas, and behavioral guidelines. When present, this prompt is automatically prepended to user prompts. Discovered by convention - no need to reference in agent.json.

**3. agent.mcp.json** (Optional)
Standard MCP server configuration enabling the agent to access external tools and capabilities. Passed to Claude CLI via `--mcp-config` flag. Discovered by convention - no need to reference in agent.json.

#### Agent Workflow

When creating a session with an agent:
1. Agent JSON config is loaded and validated
2. System prompt (if specified) is prepended to user's prompt
3. MCP config (if specified) is passed to Claude CLI
4. Agent association is stored with session metadata
5. When resuming, the session automatically uses its associated agent

### Session Management

The tool abstracts away Claude Code's internal session ID management. You interact with sessions using memorable names rather than UUIDs, while the tool handles:
- Session file storage and organization (`.jsonl` + `.meta.json` files)
- Session ID extraction and tracking
- Agent association and configuration
- Result retrieval and formatting
- State management

#### Session States

Sessions can be in one of three states (returned by `ao-status`):
- **`not_existent`** - Session doesn't exist yet (never created or was cleaned up)
- **`running`** - Session created but hasn't returned a result yet (actively processing or ready for resume)
- **`finished`** - Session completed with result available (use `ao-get-result` to retrieve)

#### Session Storage

Each session is stored as:
- `{session-name}.jsonl` - Complete conversation history in JSONL format
- `{session-name}.meta.json` - Session metadata (agent association, project directory, timestamps, session ID)

Location: `{sessions-dir}/` (default: `.agent-orchestrator/agent-sessions/`)

#### Working Directory Context

- Sessions operate in a `project-dir` (default: current working directory when command is invoked)
- All file operations within the session are relative to this directory
- The project directory is stored in session metadata and preserved across resumes

## Use Cases

### Multi-Session Workflows

Coordinate multiple specialized sessions working on different aspects of a project:
```bash
# First, discover available agent definitions
uv run commands/ao-list-agents

# Architecture session using system-architect agent
uv run commands/ao-new architect --agent system-architect -p "Design microservices architecture for e-commerce"

# Development session implements based on architecture
cat architecture.md | uv run commands/ao-new developer --agent senior-developer -p "Implement based on this design:"

# Reviewer session provides feedback
uv run commands/ao-new reviewer --agent security-reviewer -p "Review the implementation for best practices"
```

### Long-Running Background Tasks

Delegate time-consuming tasks to background sessions while you continue working:
- Large codebase analysis
- Comprehensive documentation generation
- Multi-step refactoring operations
- Complex test suite creation

### Iterative Refinement

Resume sessions to continue and refine their previous work:
```bash
# Initial work
uv run commands/ao-new technical-writer --agent documentation-expert -p "Create API documentation"

# Later refinement
uv run commands/ao-resume technical-writer -p "Add authentication examples"

# Further enhancement
uv run commands/ao-resume technical-writer -p "Include error handling section"
```

### Stateful Conversations

Maintain context across multiple prompts without re-explaining background:
- Each session retains full conversation history
- No need to repeat requirements or context
- Build on previous responses naturally

## Features

### Current Capabilities

**Session Management**
- Create new sessions with descriptive names
- Resume existing sessions by name
- List all active sessions with status
- List all available agent definitions
- Clean up all sessions in one command
- Optional agent associations for specialized behavior

**Flexible Prompting**
- Direct prompt input via `-p` flag
- File-based prompts via stdin piping
- Combined prompts (prefix + file content)
- Large prompt support without character limits

**Execution Modes**
- Synchronous execution (wait for completion)
- Background execution with polling support
- Automatic result extraction
- Clean stdout/stderr separation

**State Tracking**
- Session status visibility (active, initializing, completed)
- Session ID management (hidden from user)
- Agent association tracking
- Conversation history persistence
- Cross-session identification

### Companion Skill

The `agent-orchestrator` skill provides integration guidance for Claude Code agents to use this tool within their own workflows. The skill documents:
- Synchronous and asynchronous usage patterns
- Background execution with polling logic
- Result extraction and error handling
- Best practices for agent orchestration

## Future Directions

### Agent Definitions (Current Implementation)

The tool now supports **agent definitions** - reusable configurations that define behavior, capabilities, and constraints for sessions:

**System Prompt Templates**
- Predefined role-based system prompts (architect, developer, reviewer, etc.)
- Consistent behavior across multiple sessions using the same agent
- Custom agent definitions for specialized workflows
- Markdown format for natural prompt editing

**Configuration Profiles**
- MCP (Model Context Protocol) server configurations per agent
- Tool access through MCP integration
- Hybrid JSON + Markdown format for easy editing

**Agent-Based Sessions**
```bash
# Create session with agent
uv run commands/ao-new architect --agent system-architect -p "Design e-commerce system"

# Create generic session (no agent)
uv run commands/ao-new quick-task -p "Simple task"

# Resume remembers agent association
uv run commands/ao-resume architect -p "Add security layer"
```

**Separation of Concerns**
- **Agent**: Blueprint/configuration (reusable definition)
- **Session**: Running conversation (specific instance)
- Agents are reusable; sessions are unique conversations

### Additional Planned Features

**Advanced Orchestration**
- Session-to-session communication patterns
- Dependency chains between sessions
- Parallel session execution coordination
- Result aggregation and synthesis

**Enhanced State Management**
- Session snapshots and rollback
- Conversation branching
- Selective history pruning
- Export/import of sessions

**Observability**
- Detailed execution logs per session
- Token usage tracking
- Performance metrics
- Conversation visualization

**Workflow Automation**
- Declarative multi-session workflows
- Event-driven session triggering
- Conditional execution paths
- Workflow templates

## Architecture

### Components

**`ao-*` Commands**
Collection of Python-based CLI commands providing the command-line interface and orchestration logic. Handles session management, Claude Code SDK invocation, and result extraction. Commands include:
- `ao-new` - Create new sessions
- `ao-resume` - Resume existing sessions
- `ao-status` - Check session state
- `ao-get-result` - Extract results
- `ao-list-sessions` - List all sessions
- `ao-list-agents` - List available agents
- `ao-show-config` - Display session configuration
- `ao-clean` - Remove all sessions

### Directory Structure

The Agent Orchestrator uses a project-relative directory structure located at `.agent-orchestrator/` in the current working directory where the script is invoked.

**`.agent-orchestrator/agent-sessions/`**
Storage directory for session files (JSONL format). Each file contains the complete conversation history and session metadata for one session. Companion `.meta.json` files track agent associations and timestamps.

**`.agent-orchestrator/agents/`**
Storage directory for agent definitions specific to the current project. Each agent is organized in its own subdirectory named after the agent, containing:
- `agent.json` - Required configuration file with agent metadata
- `agent.system-prompt.md` - Optional system prompt (discovered by convention)
- `agent.mcp.json` - Optional MCP configuration for tool access (discovered by convention)

All sessions and agent definitions are stored relative to the project directory (`$PWD`) where the script is invoked, ensuring each project maintains its own isolated agent environment.

### Design Philosophy

**Simplicity First**
Minimize cognitive overhead for users. Named sessions instead of UUIDs, intuitive commands, sensible defaults.

**Progressive Enhancement**
Start simple, add complexity only when needed. Basic usage is straightforward; advanced features are opt-in.

**Composability**
Tool plays well with Unix pipes, scripts, and other CLI tools. Clean input/output separation enables chaining and automation.

**Transparency**
Clear feedback, meaningful error messages, visible state. Users always know what's happening.

## Integration

The Agent Orchestrator is designed to work within the Claude Code ecosystem:

**Slash Commands**
Create custom slash commands that delegate to sessions via the runner.

**Skills**
Skills can orchestrate multiple sessions for complex, multi-step operations.

**MCP Servers**
Agents support MCP server configurations for enhanced capabilities.
The MCP configuration is passed to the Claude CLI when starting or resuming sessions.

**Workflows** _(Future)_
Declarative workflow definitions will coordinate multiple sessions.

## Status

**Current Version**: Initial Release
**Status**: Production Ready

The core functionality is stable and tested. Agent type system and advanced features are in design phase.

## Related Documentation

- **Command Help**: Run `uv run commands/ao-<command> --help` for command-specific syntax and options (e.g., `uv run commands/ao-new --help`)
- **Skill Documentation**: See the main `SKILL.md` file for comprehensive usage guide and examples
- **Example Agents**: See `EXAMPLE-AGENTS.md` for detailed agent definition examples
- **Claude Code SDK**: The commands use the Claude Code SDK for agent orchestration 