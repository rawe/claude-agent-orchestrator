# Troubleshooting Guide

Comprehensive debugging and troubleshooting guide for the Agent Orchestrator MCP Server.

## Enabling Debug Logging

Debug logging is **disabled by default**. To enable it, set the `MCP_SERVER_DEBUG` environment variable to `"true"`:

```bash
export MCP_SERVER_DEBUG="true"
```

Or add it to your MCP configuration:
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "uv",
      "args": ["run", "/path/to/agent-orchestrator-mcp.py"],
      "env": {
        "AGENT_ORCHESTRATOR_COMMAND_PATH": "/path/to/commands",
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/project",
        "MCP_SERVER_DEBUG": "true"
      }
    }
  }
}
```

## Debug Logs Location

When enabled, all debug logs are written to:
```
interfaces/agent-orchestrator-mcp-server/logs/mcp-server.log
```

## What's Logged

The logs include:
- **Server startup**: Configuration, environment variables, working directory
- **Tool calls**: Which tools are called with what parameters
- **Script execution**: Full command-line arguments, environment, stdout/stderr
- **Errors**: Detailed error messages with stack traces
- **Performance**: Execution duration for long-running operations

## Viewing Logs

### View the entire log file
```bash
cat interfaces/agent-orchestrator-mcp-server/logs/mcp-server.log
```

### View formatted logs
Each line is JSON, so you can use `jq` for formatting:
```bash
cat interfaces/agent-orchestrator-mcp-server/logs/mcp-server.log | jq '.'
```

### Follow logs in real-time
```bash
tail -f interfaces/agent-orchestrator-mcp-server/logs/mcp-server.log | jq '.'
```

### Filter by log level

**Show only errors:**
```bash
cat interfaces/agent-orchestrator-mcp-server/logs/mcp-server.log | jq 'select(.level == "ERROR")'
```

**Show errors and warnings:**
```bash
cat interfaces/agent-orchestrator-mcp-server/logs/mcp-server.log | jq 'select(.level == "ERROR" or .level == "WARN")'
```

### Search for specific operations

**Find all start_agent_session calls:**
```bash
cat interfaces/agent-orchestrator-mcp-server/logs/mcp-server.log | jq 'select(.message | contains("start_agent_session"))'
```

**Find all tool invocations:**
```bash
cat interfaces/agent-orchestrator-mcp-server/logs/mcp-server.log | jq 'select(.message | contains("Tool called"))'
```

## Testing with MCP Inspector

Test the server locally before integrating with Claude Desktop/Code:

```bash
# Set environment variables
export AGENT_ORCHESTRATOR_COMMAND_PATH="/absolute/path/to/commands"
export AGENT_ORCHESTRATOR_PROJECT_DIR="/path/to/your/project"

# Run MCP Inspector
npx @modelcontextprotocol/inspector uv run /path/to/agent-orchestrator-mcp.py
```

This opens a web interface where you can:
- See all 7 available tools
- Test tool calls with different parameters
- View responses in real-time

## Common Issues

### 1. start_agent_session fails but list_agent_blueprints works

**Symptoms:**
- `list_agent_blueprints` returns results successfully
- `start_agent_session` fails with execution errors

**Solutions:**
- Check that the `claude` CLI is installed and in PATH
- Review script execution logs for the exact error
- Verify `AGENT_ORCHESTRATOR_PROJECT_DIR` is set correctly (or omit it to use current directory)
- Ensure the commands in `AGENT_ORCHESTRATOR_COMMAND_PATH` have execute permissions

### 2. Command execution errors

**Symptoms:**
- Tool calls fail with "Command execution error"
- Script execution returns non-zero exit codes

**Solutions:**
- Look for "Command execution error" or "Command execution completed" log entries
- Check the `exitCode`, `stdout`, and `stderr` fields in the logs
- Verify the command path in `AGENT_ORCHESTRATOR_COMMAND_PATH` is correct
- Ensure the command scripts exist and are executable (`chmod +x`)

### 3. Environment variable issues

**Symptoms:**
- MCP server fails to start
- Tools cannot find required paths

**Solutions:**
- Check the "Agent Orchestrator MCP Server starting" log entry
- `AGENT_ORCHESTRATOR_COMMAND_PATH` is auto-discovered (only set to override)
- `AGENT_ORCHESTRATOR_PROJECT_DIR` is required for Claude Desktop only
- Check that `PWD` and `PATH` are what you expect
- For Claude Desktop, ensure `PATH` includes paths to `uv` and `claude` binaries

### 4. UV-related issues

**Symptoms:**
- Server fails to start with import errors
- Dependency resolution errors

**Solutions:**
- Ensure `uv` is installed: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Verify `uv` is in PATH: `which uv`
- Verify Python >= 3.10 is available: `python3 --version`
- Check that dependencies can be resolved (first run may take longer)
- Try running the server directly to see UV output: `uv run agent-orchestrator-mcp.py`

### 5. Session naming errors

**Symptoms:**
- "Invalid session name" errors
- Session creation fails with validation errors

**Solutions:**
- Ensure session names follow the rules:
  - Length: 1-60 characters
  - Characters: Only alphanumeric, dash (`-`), and underscore (`_`)
  - No spaces or special characters
- Examples of valid names: `architect`, `code-reviewer`, `my_agent_123`

### 6. Session already exists

**Symptoms:**
- `start_agent_session` fails with "Session already exists" error

**Solutions:**
- Use `list_agent_sessions` to see all existing sessions
- Use `resume_agent_session` instead of `start_agent_session` to continue an existing session
- Use a different session name
- Use `delete_all_agent_sessions` to remove all sessions (warning: permanent deletion)

### 7. Agent not found

**Symptoms:**
- `start_agent_session` fails with "Agent not found" error

**Solutions:**
- Use `list_agent_blueprints` to see all available agent blueprints
- Check that the agent blueprint exists in `AGENT_ORCHESTRATOR_AGENTS_DIR`
- Verify the agent blueprint name spelling matches exactly
- Ensure agent blueprint files are properly structured

### 8. PATH issues (Claude Desktop)

**Symptoms:**
- Claude Desktop cannot find `uv` or `claude` commands
- Command execution fails with "command not found"

**Solutions:**
- Add `PATH` environment variable to your MCP configuration
- Include directories containing required binaries:
  ```json
  "env": {
    "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
  }
  ```
- Verify paths with `which uv` and `which claude` in terminal
- Common paths:
  - Homebrew (macOS): `/opt/homebrew/bin`
  - User binaries: `/usr/local/bin`
  - Custom installs: `~/.local/bin`

### 9. Async execution issues

**Symptoms:**
- Async sessions don't complete
- `get_agent_session_status` always returns "running"

**Solutions:**
- Check that the underlying agent process is actually running
- Review logs for script execution errors
- Verify the session name is correct
- Use `get_agent_session_status` with `wait_seconds` to poll with delay
- Check system resources (CPU, memory) for long-running tasks

### 10. Permission denied errors

**Symptoms:**
- "Permission denied" errors when executing commands
- Scripts fail to run

**Solutions:**
- Ensure command scripts have execute permissions:
  ```bash
  chmod +x /path/to/commands/ao-*
  ```
- Verify the user running the MCP server has read/write access to:
  - Sessions directory
  - Agents directory
  - Project directory
  - Logs directory

## Getting Help

If you encounter issues not covered here:

1. **Enable debug logging** and review the logs
2. **Check environment variables** are set correctly
3. **Test commands manually** in terminal:
   ```bash
   /path/to/commands/ao-list-blueprints
   ```
4. **Verify file permissions** on command scripts and directories
5. **Check the GitHub issues** for similar problems
6. **Create a new issue** with:
   - Debug logs (sanitize sensitive paths)
   - MCP configuration (sanitize sensitive information)
   - Steps to reproduce
   - Expected vs actual behavior
