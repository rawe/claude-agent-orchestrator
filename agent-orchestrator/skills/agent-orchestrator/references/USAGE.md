# Agent Orchestrator Script Usage Guide

The `agent-orchestrator.sh` script is a command-line tool for managing Claude Code agent sessions with support for specialized agent configurations, custom directory locations, and session persistence.

## Table of Contents

- [Quick Start](#quick-start)
- [Commands](#commands)
- [Global Options](#global-options)
- [Command Options](#command-options)
- [Environment Variables](#environment-variables)
- [Directory Structure](#directory-structure)
- [Session Lifecycle](#session-lifecycle)
- [Common Use Cases](#common-use-cases)
- [Advanced Usage](#advanced-usage)
- [Error Handling](#error-handling)

---

## Quick Start

```bash
# Basic usage - create a new session
./agent-orchestrator.sh new my-session -p "Design a user authentication system"

# Use a specialized agent
./agent-orchestrator.sh new my-session --agent system-architect -p "Design a user authentication system"

# Resume an existing session
./agent-orchestrator.sh resume my-session -p "Continue with API design"

# Check session status
./agent-orchestrator.sh status my-session

# List all sessions
./agent-orchestrator.sh list
```

---

## Commands

### `new`

Create a new agent session.

**Syntax:**
```bash
agent-orchestrator.sh [global-options] new <session-name> [--agent <agent-name>] [-p <prompt>]
```

**Arguments:**
- `<session-name>` (required): Unique name for the session
  - Must be alphanumeric, dash, or underscore only
  - Maximum 60 characters
  - Must not already exist

**Options:**
- `--agent <agent-name>` (optional): Use a specific agent configuration
- `-p <prompt>` (optional): Session prompt (can be combined with stdin)

**Examples:**
```bash
# Generic session without a specialized agent
./agent-orchestrator.sh new architect -p "Design user auth system"

# Session with a specialized agent
./agent-orchestrator.sh new architect --agent system-architect -p "Design user auth system"

# Prompt from stdin
cat requirements.md | ./agent-orchestrator.sh new architect --agent system-architect

# Combine -p and stdin
cat requirements.md | ./agent-orchestrator.sh new architect -p "Create architecture based on:"
```

**Behavior:**
- Creates a new session file: `<session-name>.jsonl`
- Creates metadata file: `<session-name>.meta.json`
- If `--agent` is specified, loads the agent's system prompt and MCP configuration
- Executes Claude CLI with the provided prompt
- Returns the result of the agent execution

---

### `resume`

Resume an existing agent session with a new prompt.

**Syntax:**
```bash
agent-orchestrator.sh [global-options] resume <session-name> [-p <prompt>]
```

**Arguments:**
- `<session-name>` (required): Name of existing session to resume

**Options:**
- `-p <prompt>` (optional): New prompt to continue the session (can be combined with stdin)

**Examples:**
```bash
# Resume with a prompt
./agent-orchestrator.sh resume architect -p "Continue with API design"

# Resume with stdin
cat continue.md | ./agent-orchestrator.sh resume architect

# Combine -p and stdin
cat additional-context.md | ./agent-orchestrator.sh resume architect -p "Also consider:"
```

**Behavior:**
- Checks if session exists (errors if not found)
- Loads session metadata to retrieve associated agent (if any)
- Extracts `session_id` from the first line of the session file
- Executes Claude CLI with `-r` (resume) flag
- Appends results to existing session file
- Updates `last_resumed_at` timestamp in metadata

---

### `status`

Check the status of an agent session.

**Syntax:**
```bash
agent-orchestrator.sh [global-options] status <session-name>
```

**Arguments:**
- `<session-name>` (required): Name of session to check

**Returns:**
- `not_existent` - Session doesn't exist (no meta.json file)
- `running` - Session exists but hasn't completed yet
- `finished` - Session completed successfully (last line has `type=result`)

**Examples:**
```bash
# Check if session is complete
./agent-orchestrator.sh status architect
# Output: finished

# Check non-existent session
./agent-orchestrator.sh status nonexistent
# Output: not_existent
```

**Status Detection Logic:**
1. If `<session-name>.meta.json` doesn't exist → `not_existent`
2. If `<session-name>.jsonl` doesn't exist or is empty → `running` (initializing)
3. If last line of JSONL has `type=result` → `finished`
4. Otherwise → `running`

---

### `list`

List all agent sessions with metadata.

**Syntax:**
```bash
agent-orchestrator.sh [global-options] list
```

**Examples:**
```bash
./agent-orchestrator.sh list
# Output:
# architect (session: abc123-def456)
# researcher (session: xyz789-uvw012)
```

**Behavior:**
- Lists all `.jsonl` files in the sessions directory
- Extracts and displays session ID from each file
- Shows "initializing" for empty session files
- Shows "No sessions found" if no sessions exist

---

### `list-agents`

List all available agent definitions.

**Syntax:**
```bash
agent-orchestrator.sh [global-options] list-agents
```

**Examples:**
```bash
./agent-orchestrator.sh list-agents
# Output:
# system-architect:
# Expert system architect for designing scalable systems
#
# ---
#
# web-researcher:
# Specialized agent for web research and information gathering
```

**Behavior:**
- Scans the agents directory for subdirectories containing `agent.json`
- Displays agent name and description
- Shows "No agent definitions found" if none exist

---

### `clean`

Remove all agent sessions.

**Syntax:**
```bash
agent-orchestrator.sh [global-options] clean
```

**Examples:**
```bash
./agent-orchestrator.sh clean
# Output: All sessions removed
```

**Behavior:**
- Removes the entire `agent-sessions` directory
- Deletes all session files (`.jsonl`) and metadata files (`.meta.json`)
- **Warning:** This is destructive and cannot be undone

---

## Global Options

Global options must be specified **before** the command name.

### `--project-dir <path>`

Set the project directory where `.agent-orchestrator` structure will be created.

**Default:** Current working directory (`$PWD`)

**Examples:**
```bash
# Use a different project directory
./agent-orchestrator.sh --project-dir /path/to/project new session -p "prompt"

# All subsequent directories derive from this
# Sessions: /path/to/project/.agent-orchestrator/agent-sessions
# Agents:   /path/to/project/.agent-orchestrator/agents
```

**Use Cases:**
- Run orchestrator from any location but target a specific project
- Manage sessions for multiple projects from a central location
- CI/CD pipelines with custom workspace directories

---

### `--sessions-dir <path>`

Override the default sessions directory location.

**Default:** `<project-dir>/.agent-orchestrator/agent-sessions`

**Examples:**
```bash
# Store sessions in temporary directory
./agent-orchestrator.sh --sessions-dir /tmp/agent-sessions new session -p "prompt"

# Use a completely custom location
./agent-orchestrator.sh --sessions-dir ~/my-sessions new session -p "prompt"
```

**Use Cases:**
- Store sessions in temporary storage for CI/CD
- Share sessions across multiple projects
- Separate concerns (code vs. sessions)

---

### `--agents-dir <path>`

Override the default agents directory location.

**Default:** `<project-dir>/.agent-orchestrator/agents`

**Examples:**
```bash
# Share agent definitions across projects
./agent-orchestrator.sh --agents-dir ~/shared/agents new session --agent my-agent -p "prompt"

# Use organization-wide agent repository
./agent-orchestrator.sh --agents-dir /shared/company/agents new session --agent system-architect -p "prompt"
```

**Use Cases:**
- Share agent definitions across multiple projects
- Centralized agent repository for teams
- Version-controlled agent definitions in separate repo

---

### Combining Global Options

All three global options can be used together:

```bash
./agent-orchestrator.sh \
  --project-dir /path/to/project \
  --sessions-dir /tmp/sessions \
  --agents-dir ~/shared/agents \
  new session --agent my-agent -p "prompt"
```

---

## Command Options

### `-p <prompt>`

Provide the prompt for the agent session.

**Can be used with:** `new`, `resume`

**Behavior:**
- Can be combined with stdin
- When both `-p` and stdin are provided, `-p` content comes first
- Separated by a newline

**Examples:**
```bash
# Just -p flag
./agent-orchestrator.sh new session -p "Design authentication system"

# Just stdin
cat requirements.md | ./agent-orchestrator.sh new session

# Both (concatenated with newline)
cat requirements.md | ./agent-orchestrator.sh new session -p "Create architecture based on:"
# Result: "-p content\n<stdin content>"
```

---

### `--agent <agent-name>`

Use a specific agent configuration.

**Can be used with:** `new` only

**Behavior:**
- Agent name must match a directory in `<agents-dir>/<agent-name>/`
- Loads `agent.json` for configuration
- Loads `agent.system-prompt.md` if present (prepended to user prompt)
- Loads `agent.mcp.json` if present (passed to Claude CLI)
- Agent association is remembered for `resume` commands

**Examples:**
```bash
# Use system architect agent
./agent-orchestrator.sh new session --agent system-architect -p "Design auth system"

# Resume automatically uses the same agent
./agent-orchestrator.sh resume session -p "Continue"
```

---

## Environment Variables

Environment variables provide a convenient way to set default directories without specifying global options every time.

### `AGENT_ORCHESTRATOR_PROJECT_DIR`

Set the default project directory.

**Examples:**
```bash
# Set for current session
export AGENT_ORCHESTRATOR_PROJECT_DIR=/path/to/project
./agent-orchestrator.sh new session -p "prompt"

# Set temporarily for one command
AGENT_ORCHESTRATOR_PROJECT_DIR=/tmp/project ./agent-orchestrator.sh list
```

---

### `AGENT_ORCHESTRATOR_SESSIONS_DIR`

Set the default sessions directory.

**Examples:**
```bash
# Set for current session
export AGENT_ORCHESTRATOR_SESSIONS_DIR=/tmp/sessions
./agent-orchestrator.sh new session -p "prompt"
```

---

### `AGENT_ORCHESTRATOR_AGENTS_DIR`

Set the default agents directory.

**Examples:**
```bash
# Share agents across projects
export AGENT_ORCHESTRATOR_AGENTS_DIR=~/shared/agents
./agent-orchestrator.sh new session --agent my-agent -p "prompt"
```

---

### Precedence Order

Configuration values are resolved in the following order (highest to lowest priority):

1. **CLI Flags** (highest priority)
   - `--project-dir`, `--sessions-dir`, `--agents-dir`
2. **Environment Variables**
   - `AGENT_ORCHESTRATOR_PROJECT_DIR`, etc.
3. **Default Values** (lowest priority)
   - Current working directory (`$PWD`)

**Example:**
```bash
# ENV says /tmp/env-project, CLI says /tmp/cli-project
export AGENT_ORCHESTRATOR_PROJECT_DIR=/tmp/env-project
./agent-orchestrator.sh --project-dir /tmp/cli-project new session -p "prompt"

# Result: Uses /tmp/cli-project (CLI flag wins)
```

---

## Directory Structure

### Default Structure

When using default settings (no custom directories):

```
/path/to/project/
└── .agent-orchestrator/
    ├── agent-sessions/
    │   ├── session-1.jsonl
    │   ├── session-1.meta.json
    │   ├── session-2.jsonl
    │   └── session-2.meta.json
    └── agents/
        ├── system-architect/
        │   ├── agent.json
        │   ├── agent.system-prompt.md
        │   └── agent.mcp.json
        └── web-researcher/
            ├── agent.json
            └── agent.system-prompt.md
```

### File Descriptions

#### Session Files (`.jsonl`)

JSONL (JSON Lines) files containing the complete session execution log:
- First line: Contains `session_id` (required for resume)
- Subsequent lines: Streaming events from Claude CLI
- Last line: Contains `type=result` when session completes

**Example:**
```jsonl
{"session_id": "abc123-def456", "type": "start"}
{"type": "chunk", "data": "Processing..."}
{"type": "chunk", "data": "More output..."}
{"type": "result", "result": "Task completed successfully"}
```

#### Metadata Files (`.meta.json`)

JSON files containing session metadata:

**Structure:**
```json
{
  "session_name": "architect",
  "agent": "system-architect",
  "created_at": "2025-01-08T10:00:00Z",
  "last_resumed_at": "2025-01-08T12:30:00Z"
}
```

**Fields:**
- `session_name`: Name of the session
- `agent`: Associated agent name (or `null` for generic sessions)
- `created_at`: ISO 8601 timestamp of creation
- `last_resumed_at`: ISO 8601 timestamp of last resume

#### Agent Configuration Files

Each agent is a directory containing:

**`agent.json`** (required):
```json
{
  "name": "system-architect",
  "description": "Expert system architect for designing scalable systems"
}
```

**`agent.system-prompt.md`** (optional):
- Markdown file with system prompt
- Prepended to user prompts with `---` separator

**`agent.mcp.json`** (optional):
- MCP (Model Context Protocol) configuration
- Passed to Claude CLI via `--mcp-config` flag

---

## Session Lifecycle

### 1. Creation (`new`)

```bash
./agent-orchestrator.sh new architect --agent system-architect -p "Design auth system"
```

**What happens:**
1. Validates session name doesn't already exist
2. Loads agent configuration (if `--agent` specified)
3. Loads system prompt (if available)
4. Creates `architect.meta.json` with creation timestamp
5. Executes Claude CLI with combined prompt
6. Creates `architect.jsonl` with execution log
7. Returns result to stdout

**Files created:**
- `architect.jsonl` (session execution log)
- `architect.meta.json` (metadata)

---

### 2. Resumption (`resume`)

```bash
./agent-orchestrator.sh resume architect -p "Continue with API design"
```

**What happens:**
1. Checks if `architect.jsonl` exists
2. Loads `architect.meta.json` to get agent association
3. Extracts `session_id` from first line of JSONL
4. Loads agent configuration (if session had an agent)
5. Executes Claude CLI with `-r <session_id>` and new prompt
6. Appends results to `architect.jsonl`
7. Updates `last_resumed_at` in `architect.meta.json`
8. Returns result to stdout

**Files modified:**
- `architect.jsonl` (appended)
- `architect.meta.json` (timestamp updated)

---

### 3. Status Check (`status`)

```bash
./agent-orchestrator.sh status architect
```

**What happens:**
1. Checks if `architect.meta.json` exists
   - If no → returns `not_existent`
2. Checks if `architect.jsonl` exists and is non-empty
   - If empty → returns `running`
3. Reads last line of JSONL
4. Checks if last line has `type=result`
   - If yes → returns `finished`
   - If no → returns `running`

**No files modified**

---

### 4. Cleanup (`clean`)

```bash
./agent-orchestrator.sh clean
```

**What happens:**
1. Removes entire `agent-sessions` directory
2. Deletes all `.jsonl` and `.meta.json` files

**Files deleted:**
- All session files
- All metadata files
- Sessions directory itself

---

## Common Use Cases

### Use Case 1: Basic Session Management

**Scenario:** Simple agent sessions in current project

```bash
# Create session
./agent-orchestrator.sh new task1 -p "Analyze codebase"

# Check status
./agent-orchestrator.sh status task1

# Resume if needed
./agent-orchestrator.sh resume task1 -p "Continue analysis"

# List all sessions
./agent-orchestrator.sh list
```

---

### Use Case 2: Multi-Project Management

**Scenario:** Manage sessions for multiple projects from one location

```bash
# Project A sessions
./agent-orchestrator.sh --project-dir ~/projects/project-a new session1 -p "Task for A"

# Project B sessions
./agent-orchestrator.sh --project-dir ~/projects/project-b new session1 -p "Task for B"

# List project A sessions
./agent-orchestrator.sh --project-dir ~/projects/project-a list

# List project B sessions
./agent-orchestrator.sh --project-dir ~/projects/project-b list
```

---

### Use Case 3: Shared Agent Definitions

**Scenario:** Team sharing agent configurations across projects

```bash
# Setup: Create shared agents directory
mkdir -p ~/company/agents

# Project 1 uses shared agents
./agent-orchestrator.sh \
  --project-dir ~/projects/project1 \
  --agents-dir ~/company/agents \
  new session --agent system-architect -p "Design system"

# Project 2 uses same shared agents
./agent-orchestrator.sh \
  --project-dir ~/projects/project2 \
  --agents-dir ~/company/agents \
  new session --agent system-architect -p "Design system"
```

---

### Use Case 4: CI/CD Pipeline

**Scenario:** Automated testing in CI/CD with temporary session storage

```bash
# In CI pipeline script
export AGENT_ORCHESTRATOR_PROJECT_DIR="${CI_PROJECT_DIR}"
export AGENT_ORCHESTRATOR_SESSIONS_DIR="${CI_PROJECT_DIR}/tmp/sessions"

# Run automated agent session
./agent-orchestrator.sh new ci-test --agent test-agent -p "Run tests"

# Check result
STATUS=$(./agent-orchestrator.sh status ci-test)
if [ "$STATUS" = "finished" ]; then
  echo "Tests completed successfully"
else
  echo "Tests still running or failed"
  exit 1
fi
```

---

### Use Case 5: Environment-Based Configuration

**Scenario:** Different configurations for dev, staging, prod

```bash
# .env.development
export AGENT_ORCHESTRATOR_PROJECT_DIR="${HOME}/dev/myproject"
export AGENT_ORCHESTRATOR_AGENTS_DIR="${HOME}/dev/agents"

# .env.production
export AGENT_ORCHESTRATOR_PROJECT_DIR="/var/app/myproject"
export AGENT_ORCHESTRATOR_AGENTS_DIR="/etc/agent-orchestrator/agents"

# Load appropriate env file
source .env.development

# Run command (uses dev configuration)
./agent-orchestrator.sh new session --agent my-agent -p "prompt"
```

---

### Use Case 6: Prompts from Files

**Scenario:** Long prompts stored in files

```bash
# Simple file input
cat detailed-requirements.md | ./agent-orchestrator.sh new architect --agent system-architect

# Combine instruction with file content
cat user-stories.md | ./agent-orchestrator.sh new architect -p "Design a system based on these user stories:"

# Multiple files
cat requirements.md context.md | ./agent-orchestrator.sh new architect -p "Analyze:"
```

---

### Use Case 7: Session Status Monitoring

**Scenario:** Wait for session completion in scripts

```bash
#!/bin/bash
# Start session
./agent-orchestrator.sh new long-task --agent researcher -p "Research topic"

# Poll for completion
while [ "$(./agent-orchestrator.sh status long-task)" = "running" ]; do
  echo "Session still running..."
  sleep 10
done

echo "Session completed!"
```

---

## Advanced Usage

### Custom Directory Hierarchies

Create sophisticated directory structures for complex scenarios:

```bash
# Separate concerns completely
./agent-orchestrator.sh \
  --project-dir ~/projects/main-project \
  --sessions-dir /mnt/fast-storage/sessions \
  --agents-dir /shared/team/agents \
  new session --agent my-agent -p "prompt"

# Organize by environment
./agent-orchestrator.sh \
  --project-dir ~/projects/myapp \
  --sessions-dir ~/projects/myapp/.orchestrator/dev/sessions \
  --agents-dir ~/projects/myapp/.orchestrator/agents \
  new dev-session -p "prompt"
```

---

### Workspace Switching

Use shell functions to quickly switch between workspaces:

```bash
# In your .bashrc or .zshrc
ao_dev() {
  export AGENT_ORCHESTRATOR_PROJECT_DIR=~/dev/myproject
  export AGENT_ORCHESTRATOR_AGENTS_DIR=~/dev/agents
}

ao_prod() {
  export AGENT_ORCHESTRATOR_PROJECT_DIR=/var/app/myproject
  export AGENT_ORCHESTRATOR_AGENTS_DIR=/etc/agents
}

# Usage
ao_dev
./agent-orchestrator.sh list  # Lists dev sessions

ao_prod
./agent-orchestrator.sh list  # Lists prod sessions
```

---

### Session Result Extraction

Extract results from completed sessions:

```bash
# Get the result from a completed session
./agent-orchestrator.sh status my-session | grep -q "finished" && \
  tail -n 1 ~/.agent-orchestrator/agent-sessions/my-session.jsonl | \
  jq -r '.result'
```

---

### Batch Operations

Process multiple sessions:

```bash
# List all sessions and their statuses
for session in $(./agent-orchestrator.sh list | awk '{print $1}'); do
  status=$(./agent-orchestrator.sh status "$session")
  echo "$session: $status"
done

# Resume all running sessions
for session in $(./agent-orchestrator.sh list | awk '{print $1}'); do
  status=$(./agent-orchestrator.sh status "$session")
  if [ "$status" = "running" ]; then
    ./agent-orchestrator.sh resume "$session" -p "Continue processing"
  fi
done
```

---

## Error Handling

### Common Errors

#### Error: Project directory does not exist

```bash
./agent-orchestrator.sh --project-dir /nonexistent/path new session -p "prompt"
# Error: Project directory does not exist: /nonexistent/path
```

**Solution:** Ensure the project directory exists before running the command:
```bash
mkdir -p /path/to/project
./agent-orchestrator.sh --project-dir /path/to/project new session -p "prompt"
```

---

#### Error: Session already exists

```bash
./agent-orchestrator.sh new existing-session -p "prompt"
# Error: Session 'existing-session' already exists. Use 'resume' command to continue or choose a different name
```

**Solution:** Use `resume` instead of `new`, or choose a different session name:
```bash
./agent-orchestrator.sh resume existing-session -p "prompt"
# Or
./agent-orchestrator.sh new existing-session-2 -p "prompt"
```

---

#### Error: Session does not exist

```bash
./agent-orchestrator.sh resume nonexistent -p "prompt"
# Error: Session 'nonexistent' does not exist. Use 'new' command to create it
```

**Solution:** Create the session first:
```bash
./agent-orchestrator.sh new nonexistent -p "prompt"
```

---

#### Error: Agent not found

```bash
./agent-orchestrator.sh new session --agent nonexistent -p "prompt"
# Error: Agent not found: nonexistent (expected directory: /path/.agent-orchestrator/agents/nonexistent)
```

**Solution:** Check available agents and use a valid one:
```bash
./agent-orchestrator.sh list-agents
./agent-orchestrator.sh new session --agent system-architect -p "prompt"
```

---

#### Error: No prompt provided

```bash
./agent-orchestrator.sh new session
# Error: No prompt provided. Use -p flag or pipe prompt via stdin
```

**Solution:** Provide a prompt via `-p` flag or stdin:
```bash
./agent-orchestrator.sh new session -p "My prompt"
# Or
echo "My prompt" | ./agent-orchestrator.sh new session
```

---

#### Error: Invalid session name

```bash
./agent-orchestrator.sh new "invalid session!" -p "prompt"
# Error: Session name contains invalid characters. Only alphanumeric, dash (-), and underscore (_) are allowed: invalid session!
```

**Solution:** Use only alphanumeric characters, dashes, and underscores:
```bash
./agent-orchestrator.sh new "invalid-session" -p "prompt"
```

---

#### Error: Parent directory not writable

```bash
./agent-orchestrator.sh --sessions-dir /readonly/path/sessions new session -p "prompt"
# Error: Cannot create sessions directory (parent not writable): /readonly/path/sessions
```

**Solution:** Use a writable directory:
```bash
./agent-orchestrator.sh --sessions-dir ~/sessions new session -p "prompt"
```

---

## Best Practices

### 1. Session Naming

- Use descriptive names: `auth-system-design` instead of `session1`
- Include dates for temporal tracking: `2025-01-08-refactor`
- Use consistent naming conventions across projects

### 2. Directory Management

- Keep agent definitions in version control
- Use environment variables for team-shared configurations
- Document custom directory structures in project README

### 3. Session Lifecycle

- Check status before resuming long-running sessions
- Clean up old sessions regularly
- Back up important session results before running `clean`

### 4. Agent Configuration

- Version control agent definitions separately
- Use descriptive agent names and documentation
- Test agents with small sessions before production use

### 5. Error Handling in Scripts

Always check exit codes and status:
```bash
if ! ./agent-orchestrator.sh new session -p "prompt"; then
  echo "Failed to create session"
  exit 1
fi

STATUS=$(./agent-orchestrator.sh status session)
if [ "$STATUS" != "finished" ]; then
  echo "Session not completed: $STATUS"
  exit 1
fi
```

---

## Troubleshooting

### Sessions Not Appearing

**Check directory configuration:**
```bash
# Verify you're looking in the right place
echo "PROJECT_DIR: $AGENT_ORCHESTRATOR_PROJECT_DIR"
echo "SESSIONS_DIR: $AGENT_ORCHESTRATOR_SESSIONS_DIR"

# List sessions with explicit directory
./agent-orchestrator.sh --project-dir /path/to/project list
```

### Session Stuck in "running" State

**Check session file:**
```bash
# Look at the last few lines
tail -n 5 .agent-orchestrator/agent-sessions/session-name.jsonl

# Check if result line exists
tail -n 1 .agent-orchestrator/agent-sessions/session-name.jsonl | jq '.type'
```

### Permission Issues

**Check directory permissions:**
```bash
# Check if parent directory is writable
ls -la /path/to/parent

# Fix permissions if needed
chmod 755 /path/to/parent
```

---

## Additional Resources

- Agent configuration format: See `AGENT-ORCHESTRATOR.md`
- MCP configuration: See Claude CLI documentation
- Session file format: JSONL (JSON Lines) with Claude CLI streaming format
- Metadata format: Standard JSON with ISO 8601 timestamps