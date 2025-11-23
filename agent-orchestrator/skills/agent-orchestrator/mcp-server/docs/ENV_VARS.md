# Environment Variables Reference

This is the **single source of truth** for all environment variables used by the Agent Orchestrator MCP Server.

## Quick Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AGENT_ORCHESTRATOR_COMMAND_PATH` | No | **Auto-discovered** from MCP server location | Absolute path to the commands directory containing Python scripts. Now auto-discovered, but can be overridden. |
| `AGENT_ORCHESTRATOR_PROJECT_DIR` | **Claude Desktop: Yes**<br>Claude Code: No | Current directory (Claude Code only) | Project directory where orchestrated agents execute. Controls the base for other defaults. |
| `AGENT_ORCHESTRATOR_SESSIONS_DIR` | No | `$PROJECT_DIR/.agent-orchestrator/sessions` | Custom location for agent session storage. Use for centralized session management across projects. |
| `AGENT_ORCHESTRATOR_AGENTS_DIR` | No | `$PROJECT_DIR/.agent-orchestrator/agents` | Custom location for agent definitions. Use to share agent definitions across projects. |
| `AGENT_ORCHESTRATOR_ENABLE_LOGGING` | No | `false` | Set to `"true"` to enable logging of orchestrated agent execution. Used for debugging agent sessions. |
| `MCP_SERVER_DEBUG` | No | `false` | Set to `"true"` to enable debug logging to `logs/mcp-server.log`. Used for troubleshooting MCP server issues. |
| `PATH` | **Claude Desktop only** | - | Must include path to `uv` and `claude` binaries. Claude Desktop does not inherit shell PATH. Example: `/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin` |

## Variable Details

### `AGENT_ORCHESTRATOR_COMMAND_PATH` (Auto-Discovered)

- Absolute path to the commands directory containing Python scripts
- Example (local development): `/Users/yourname/projects/agent-orchestrator-cli/commands`
- Example (production): `/usr/local/lib/agent-orchestrator/commands`
- The directory should contain: `ao-new`, `ao-resume`, `ao-list-sessions`, `ao-list-agents`, `ao-clean`

### `AGENT_ORCHESTRATOR_PROJECT_DIR` (Conditionally Required)

- Directory where orchestrated agents execute
- Required for Claude Desktop
- Optional for Claude Code (defaults to current directory where MCP server is invoked)
- This is the working directory for all agent sessions
- Example: `/Users/yourname/my-project`

### `AGENT_ORCHESTRATOR_SESSIONS_DIR` (Optional)

- Custom path for storing session data
- Defaults to `.agent-orchestrator/sessions/` within the project directory
- Use when you want centralized session management across multiple projects
- Example: `/Users/yourname/.agent-orchestrator-global/sessions`

### `AGENT_ORCHESTRATOR_AGENTS_DIR` (Optional)

- Custom path for agent definition files
- Defaults to `.agent-orchestrator/agents/` within the project directory
- Use when you want to share agent definitions across multiple projects
- Example: `/Users/yourname/.agent-orchestrator-global/agents`

### `AGENT_ORCHESTRATOR_ENABLE_LOGGING` (Optional)

- Enable logging for orchestrated agent sessions
- Set to `"true"` for debugging purposes
- Logs agent execution details

### `MCP_SERVER_DEBUG` (Optional)

- Enable debug logging for the MCP server itself
- Set to `"true"` to write logs to `logs/mcp-server.log`
- Logs include server startup, tool calls, script execution, and errors

### `PATH` (Claude Desktop Only)

- Required for Claude Desktop because UI applications do not inherit shell environment PATH
- Must include directories containing the `uv` and `claude` binaries
- Common values:
  - macOS with Homebrew: `/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin`
  - macOS with custom install: `/Users/yourname/.local/bin:/usr/local/bin:/usr/bin:/bin`
