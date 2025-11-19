---
name: agent-orchestrator
description: Use this skill when you need to orchestrate specialized Claude agents in separate sessions. Perfect for long-running tasks, specialized agents with MCP tools, and resumable workflows.
---

# Agent Orchestrator Skill

## What & When

**What**: Commands for managing specialized Claude AI agent sessions with optional agent definitions and MCP server integration.

**When to use**:
- Delegate tasks to specialized sessions with different MCP configurations
- Run long-running operations that can be resumed later
- Use agent definitions for specialized behavior (research, testing, etc.)
- Manage multiple concurrent agent conversations
- Work with persistent sessions using simple names (no session ID management)

**Key Benefits**:
- Session names instead of session IDs (simpler tracking)
- Automatic session management and persistence
- Built-in result extraction (no manual JSON parsing)
- Optional agent definitions for specialized capabilities
- Sessions can be resumed (even after finished)

---

## Quick Reference

### `ao-new` - Create new session
```bash
uv run commands/ao-new <session-name>
```
**Use when**: Starting a new Claude agent session. Reads prompt from stdin or `-p` flag.

### `ao-resume` - Continue existing session
```bash
uv run commands/ao-resume <session-name>
```
**Use when**: Adding messages to an existing session. Reads prompt from stdin or `-p` flag.

### `ao-status` - Check session state
```bash
uv run commands/ao-status <session-name>
```
**Use when**: Need to know if session is `running`, `finished`, or `not_existent`.

### `ao-get-result` - Extract result from finished session
```bash
uv run commands/ao-get-result <session-name>
```
**Use when**: Session is finished and you need the final result text.

### `ao-list-sessions` - List all sessions
```bash
uv run commands/ao-list-sessions
```
**Use when**: Need to see available sessions with their IDs and project directories.

### `ao-list-agents` - List available agent definitions
```bash
uv run commands/ao-list-agents
```
**Use when**: Need to see what specialized agent definitions are available.

### `ao-show-config` - Display session configuration
```bash
uv run commands/ao-show-config <session-name>
```
**Use when**: Need to see session metadata (project dir, agent used, timestamps, etc.).

### `ao-clean` - Remove all sessions
```bash
uv run commands/ao-clean
```
**Use when**: Need to delete all session data. **Use with caution.**

---

## Command Location

**IMPORTANT**: All commands are located in the `commands/` subdirectory of this skill folder.

Before using commands for the first time:
1. Locate this skill's root folder (same directory as this SKILL.md)
2. Commands are in: `<skill-root>/commands/ao-*`
3. Execute using: `uv run <skill-root>/commands/ao-<command> <args>`

**Example**:
```bash
# If skill is at /path/to/skills/agent-orchestrator
uv run /path/to/skills/agent-orchestrator/commands/ao-new my-session -p "Research topic X"
```

---

## Parameters Reference

### Required
- `<session-name>` - Alphanumeric + dash/underscore, max 60 chars (e.g., `research-task`, `code_review_123`)

### Common Options
- `-p "prompt"` or `--prompt "prompt"` - Provide prompt via CLI instead of stdin
- `--agent <agent-name>` - Use specialized agent definition (only for `ao-new`)
- `--project-dir <path>` - Override project directory (default: current directory)

---

## Typical Workflows

### Basic Session Workflow
```bash
# Create new session
echo "Analyze this codebase structure" | uv run commands/ao-new analysis

# Check status
uv run commands/ao-status analysis  # Output: finished

# Get result
uv run commands/ao-get-result analysis

# Resume with follow-up
echo "Now focus on security patterns" | uv run commands/ao-resume analysis
```

### Using Specialized Agents
```bash
# List available agents
uv run commands/ao-list-agents

# Create session with specific agent
uv run commands/ao-new research-task --agent web-researcher -p "Research Claude AI capabilities"

# View agent configuration
uv run commands/ao-show-config research-task
```

### Managing Sessions
```bash
# List all active sessions
uv run commands/ao-list-sessions

# Check specific session
uv run commands/ao-status my-session

# Clean up all sessions
uv run commands/ao-clean
```

---

## Key Concepts

### Session States
- **`not_existent`** - Session doesn't exist
- **`running`** - Session active, ready to resume
- **`finished`** - Session complete, result available

### Working Directory
- Sessions operate in `--project-dir` (default: current directory)
- All file operations within the session are relative to this directory

### Agents vs Sessions
- **Agent**: Reusable configuration (system prompt + MCP tools)
- **Session**: Running conversation instance
- One agent can be used by multiple sessions
- Sessions can run without agents (general purpose)

---

## Notes for AI Assistants

1. **Always check status** before resuming: `ao-status <name>` → only resume if `running` or `finished`
2. **Session names** must be unique and valid (no spaces, max 60 chars, alphanumeric + dash/underscore)
3. **Prompt input**: Use stdin (pipe) OR `-p` flag, not both (stdin takes precedence)
4. **Get result** only works on `finished` sessions - check status first
5. **Agent definitions** are read-only - list them with `ao-list-agents` before using `--agent`
6. **Sessions are persistent** - they survive between command invocations
7. **Command location** - Always use commands from this skill's `commands/` folder
8. **Async execution** - Sessions run in Claude Code, commands return immediately after submission

---

## Error Handling

Common errors and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| "Session already exists" | Creating duplicate session | Use `ao-resume` or choose different name |
| "Session not found" | Wrong name or doesn't exist | Check `ao-list-sessions` |
| "Session is not finished" | Getting result from running session | Check `ao-status`, wait for `finished` |
| "Invalid session name" | Bad characters or too long | Use alphanumeric + dash/underscore, max 60 chars |
| "No prompt provided" | Missing `-p` and stdin | Provide prompt via stdin or `-p` flag |
| "Agent not found" | Agent definition missing | Check `ao-list-agents` for available agents |

---

## Exit Codes

- `0` - Success
- `1` - Error (invalid input, session not found, etc.)

---

## Quick Decision Tree

**Want to start a new agent conversation?** → `ao-new <name>`
- With specialized agent? → Add `--agent <agent-name>`
- In specific location? → Add `--project-dir <path>`

**Want to continue a conversation?** → `ao-resume <name>`
- Not sure if it exists? → Check with `ao-status <name>` first

**Want to see the result?** → `ao-get-result <name>`
- Must check status first → `ao-status <name>` (must be `finished`)

**Want to see what exists?**
- Sessions → `ao-list-sessions`
- Agents → `ao-list-agents`

**Want session details?** → `ao-show-config <name>`

**Want to clean up?** → `ao-clean` (removes all sessions)

---

## Additional Resources

- **Example Agents**: See `example/agents/` folder for working examples
- **Agent Details & Usage**: See `references/EXAMPLE-AGENTS.md`
- **Architecture & Agent Creation**: See `references/AGENT-ORCHESTRATOR.md`
- **Environment Variables**: See `references/ENV_VARS.md` for configuration options
