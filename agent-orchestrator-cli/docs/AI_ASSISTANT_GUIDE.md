# Agent Orchestrator Commands - AI Assistant Guide

**What**: CLI commands for managing Claude AI agent sessions with optional agent definitions and MCP server integration.

**When to use**: Creating, resuming, and managing persistent Claude conversation sessions with working directory context.

---

## Quick Reference

### `ao-new` - Create new session
```bash
uv run commands/ao-new <session-name>
```
**Use when**: Starting a new Claude conversation session. Reads prompt from stdin or `-p` flag.

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

### `ao-list-agents` - List available specialized agent definitions
```bash
uv run commands/ao-list-agents
```
**Use when**: Need to see what agent definitions are available (agents provide specialized behavior).

### `ao-show-config` - Display session configuration
```bash
uv run commands/ao-show-config <session-name>
```
**Use when**: Need to see session metadata (project dir, agent, timestamps, etc.).

### `ao-clean` - Remove all sessions
```bash
uv run commands/ao-clean
```
**Use when**: Need to delete all session data. Use with caution.

---

## Parameters Reference

### Required
- `<session-name>` - Alphanumeric + dash/underscore, max 60 chars (e.g., `research-task`, `code_review_123`)

### Common Options
- `-p "prompt text"` or `--prompt "prompt text"` - Provide prompt via CLI instead of stdin
- `--agent <agent-name>` - Use specialized agent definition (only for `ao-new`)
- `--project-dir <path>` - Override project directory (determines default paths for sessions-dir and agents-dir)
  - **Available in ALL commands**
- `--sessions-dir <path>` - Override session storage location
  - **Available**: All commands that work with sessions (except `ao-list-agents`)
- `--agents-dir <path>` - Override agent definitions location
  - **Available**: `ao-new`, `ao-resume`, `ao-list-agents`

### Environment Variables (Alternative to CLI flags)
```bash
export AGENT_ORCHESTRATOR_PROJECT_DIR=/path/to/project
export AGENT_ORCHESTRATOR_SESSIONS_DIR=/path/to/sessions
export AGENT_ORCHESTRATOR_AGENTS_DIR=/path/to/agents
export AGENT_ORCHESTRATOR_ENABLE_LOGGING=true
```

**Precedence**: CLI flags > Environment variables > Defaults

**Why `--project-dir` on read-only commands?**
- Default paths for `sessions-dir` and `agents-dir` are relative to `project-dir`
- Example: `project-dir=/my/project` → default `sessions-dir=/my/project/.agent-orchestrator/agent-sessions`
- Commands need to know project-dir to resolve default paths correctly

---

## Typical Workflows

### Basic Session
```bash
# Create
echo "Analyze this code" | uv run commands/ao-new code-review

# Resume
echo "Now add tests" | uv run commands/ao-resume code-review

# Check status
uv run commands/ao-status code-review  # Output: finished

# Get result
uv run commands/ao-get-result code-review
```

### With Agent
```bash
# List available agents first
uv run commands/ao-list-agents

# Create session with agent - assuming "researcher" is one of the listed agents
uv run commands/ao-new research-task --agent researcher -p "Research topic X"
```

### Custom Directories
```bash
# List agents from custom location
uv run commands/ao-list-agents --agents-dir /custom/agents

# Create session with custom paths
uv run commands/ao-new task --sessions-dir /tmp/sessions --agents-dir /custom/agents --project-dir /my/project

# Using environment variables (applies to all commands)
export AGENT_ORCHESTRATOR_SESSIONS_DIR=/tmp/sessions
export AGENT_ORCHESTRATOR_AGENTS_DIR=/custom/agents
uv run commands/ao-new task
uv run commands/ao-list-agents  # Uses env var
```

---

## Agent Definitions

**Location**: `{agents-dir}/{agent-name}/`

**Structure**:
```
agents/researcher/
├── agent.json              # Required: {"name": "...", "description": "..."}
├── agent.system-prompt.md  # Optional: system prompt prepended to user prompts
└── agent.mcp.json          # Optional: MCP server configuration
```

**Use**: Agents provide specialized behavior (system prompts) and tool access (MCP servers).

---

## Key Concepts

### Sessions
- Each session = persistent Claude conversation
- Sessions store: messages, metadata, session ID
- Sessions continue across multiple `resume` calls
- Location: `{sessions-dir}/{session-name}.jsonl` + `.meta.json`

### States
- `not_existent` - Session doesn't exist
- `running` - Session created but no result yet
- `finished` - Session completed with result

### Working Directory
- Claude operates in `--project-dir` (default: current directory)
- All file operations relative to this directory
- Project dir stored in session metadata

---

## Exit Codes

- `0` - Success
- `1` - Error (invalid input, session not found, etc.)

---

## Notes for AI Assistants

1. **Always check status** before resuming: `ao-status <name>` → only resume if `running`
2. **Session names** must be unique and valid (no spaces, max 60 chars)
3. **Prompt input**: Use stdin (pipe) OR `-p` flag, not both (stdin takes precedence if both provided)
4. **Get result** only works on `finished` sessions - check status first
5. **Agent definitions** are read-only - list them with `ao-list-agents` before using `--agent`
6. **Sessions are persistent** - they survive between command invocations
7. **No cross-tool compatibility** - sessions created by Python commands cannot be used by bash script

---

## Error Handling

Common errors and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| "Session already exists" | Creating duplicate session | Use `ao-resume` or choose different name |
| "Session not found" | Wrong name or doesn't exist | Check `ao-list-sessions` |
| "Session is not finished" | Getting result from running session | Wait or check `ao-status` |
| "Invalid session name" | Bad characters or too long | Use alphanumeric + dash/underscore, max 60 chars |
| "No prompt provided" | Missing `-p` and stdin | Provide prompt via stdin or `-p` flag |
| "Agent not found" | Agent definition missing | Check `ao-list-agents` |

---

## Quick Decision Tree

**Want to start a conversation?** → `ao-new <name>`
- With specialized behavior? → Add `--agent <agent-name>`
- Different location? → Add `--sessions-dir <path>`

**Want to continue a conversation?** → `ao-resume <name>`
- Need to check if it exists first? → `ao-status <name>`

**Want to see the result?** → `ao-get-result <name>`
- Check if finished first? → `ao-status <name>` (must be `finished`)

**Want to see what exists?** → `ao-list-sessions` (sessions) or `ao-list-agents` (agents)

**Want to clean up?** → `ao-clean` (removes all sessions)

**Want to see session details?** → `ao-show-config <name>`
