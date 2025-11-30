# Environment Variables Reference

Single source of truth for environment variables used by the Agent Orchestrator MCP Server.

## Quick Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AGENT_ORCHESTRATOR_COMMAND_PATH` | No | **Auto-discovered** | Path to commands directory. Auto-discovered from MCP server location, can be overridden. |
| `AGENT_ORCHESTRATOR_PROJECT_DIR` | **Claude Desktop: Yes**<br>Claude Code: No | Current directory | Project directory where orchestrated agents execute. |
| `MCP_SERVER_DEBUG` | No | `false` | Enable debug logging to `logs/mcp-server.log`. |
| `PATH` | **Claude Desktop only** | - | Must include `uv` and `claude` binaries. Claude Desktop doesn't inherit shell PATH. |

## Variable Details

### `AGENT_ORCHESTRATOR_COMMAND_PATH` (Auto-Discovered)

- Absolute path to the commands directory containing Python scripts
- **Auto-discovered** relative to MCP server location - no configuration needed
- Can be set to override auto-discovery
- The directory should contain: `ao-new`, `ao-resume`, `ao-list-sessions`, `ao-list-agents`, `ao-clean`

### `AGENT_ORCHESTRATOR_PROJECT_DIR` (Conditionally Required)

- Directory where orchestrated agents execute
- **Required for Claude Desktop** (UI apps don't have a current directory context)
- **Optional for Claude Code** - defaults to current directory
- Example: `/Users/yourname/my-project`

### `MCP_SERVER_DEBUG` (Optional)

- Enable debug logging for the MCP server
- Set to `"true"` to write logs to `logs/mcp-server.log`
- Logs include server startup, tool calls, script execution, and errors

### `PATH` (Claude Desktop Only)

- Required for Claude Desktop because UI applications do not inherit shell PATH
- Must include directories containing the `uv` and `claude` binaries
- Common values:
  - macOS with Homebrew: `/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin`
  - macOS with custom install: `/Users/yourname/.local/bin:/usr/local/bin:/usr/bin:/bin`
