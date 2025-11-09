# Agent Orchestrator MCP Server

A Model Context Protocol (MCP) server that provides tools for orchestrating specialized Claude Code agents through the agent-orchestrator.sh script.

## Overview

### What is the Agent Orchestrator Framework (AOF)?

The **Agent Orchestrator Framework (AOF)** is the combination of this MCP server and the `agent-orchestrator.sh` script (from the `agent-orchestrator` Claude Code skill). Together they enable creating and managing specialized Claude Code agent sessions that work autonomously on tasks.

**Key components**:
- **This MCP server**: Provides MCP tools for orchestrating agents from any MCP-compatible AI system
- **agent-orchestrator.sh**: The underlying bash script that launches and manages Claude Code sessions
- **Agent definitions**: Specialized agent configurations (`.agent-orchestrator/agents/`)
- **Sessions**: Active or completed agent work sessions (`.agent-orchestrator/sessions/`)

### Relationship to Claude Code Plugin

Previously, the agent orchestrator was available only as a Claude Code skill/plugin installed in `.claude/skills/`. This MCP server **provides an abstraction layer** that:
- Works with any AI agent system supporting MCP (Claude Desktop, Claude Code, etc.)
- No longer requires installing the skill as a Claude Code plugin
- Provides a standardized MCP interface for agent orchestration

### What This MCP Server Does

Provides 5 MCP tools for managing orchestrated agent sessions:
- Discover available specialized agent definitions
- Create new agent sessions (generic or specialized)
- Resume existing agent sessions
- List active sessions
- Clean up sessions

## Features

- **5 MCP Tools**:
  - `list_agents` - Discover available specialized agent definitions
  - `list_sessions` - View all agent sessions and their IDs
  - `start_agent` - Create new agent sessions with optional specialization
  - `resume_agent` - Continue work in existing sessions
  - `clean_sessions` - Remove all sessions

- **Type-Safe**: Full TypeScript implementation with Zod validation
- **Flexible Output**: Support for both Markdown (human-readable) and JSON (machine-readable) formats
- **Comprehensive Error Handling**: Clear, actionable error messages
- **Character Limits**: Automatic truncation for large responses

## Installation

See [GETTING_STARTED.md](./GETTING_STARTED.md) for installation instructions.

## Environment Variables Reference

This is the **single source of truth** for all environment variables used by the Agent Orchestrator MCP Server.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AGENT_ORCHESTRATOR_SCRIPT_PATH` | **Yes** | - | Absolute path to the `agent-orchestrator.sh` script |
| `AGENT_ORCHESTRATOR_PROJECT_DIR` | **Claude Desktop: Yes**<br>Claude Code: No | Current directory (Claude Code only) | Project directory where orchestrated agents execute. Controls the base for other defaults. |
| `AGENT_ORCHESTRATOR_SESSIONS_DIR` | No | `$PROJECT_DIR/.agent-orchestrator/sessions` | Custom location for agent session storage. Use for centralized session management across projects. |
| `AGENT_ORCHESTRATOR_AGENTS_DIR` | No | `$PROJECT_DIR/.agent-orchestrator/agents` | Custom location for agent definitions. Use to share agent definitions across projects. |
| `AGENT_ORCHESTRATOR_ENABLE_LOGGING` | No | `false` | Set to `"true"` to enable logging of orchestrated agent execution. Used for debugging agent sessions. |
| `MCP_SERVER_DEBUG` | No | `false` | Set to `"true"` to enable debug logging to `logs/mcp-server.log`. Used for troubleshooting MCP server issues. |
| `PATH` | **Claude Desktop only** | - | Must include path to Node.js binary. Claude Desktop does not inherit shell PATH. Example: `/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin` |

### Variable Details

**`AGENT_ORCHESTRATOR_SCRIPT_PATH`** (Required)
- Absolute path to the `agent-orchestrator.sh` bash script
- Example: `/Users/yourname/projects/agent-orchestrator-framework/agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh`

**`AGENT_ORCHESTRATOR_PROJECT_DIR`** (Conditionally Required)
- Directory where orchestrated agents execute
- Required for Claude Desktop
- Optional for Claude Code (defaults to current directory where MCP server is invoked)
- This is the working directory for all agent sessions
- Example: `/Users/yourname/my-project`

**`AGENT_ORCHESTRATOR_SESSIONS_DIR`** (Optional)
- Custom path for storing session data
- Defaults to `.agent-orchestrator/sessions/` within the project directory
- Use when you want centralized session management across multiple projects
- Example: `/Users/yourname/.agent-orchestrator-global/sessions`

**`AGENT_ORCHESTRATOR_AGENTS_DIR`** (Optional)
- Custom path for agent definition files
- Defaults to `.agent-orchestrator/agents/` within the project directory
- Use when you want to share agent definitions across multiple projects
- Example: `/Users/yourname/.agent-orchestrator-global/agents`

**`AGENT_ORCHESTRATOR_ENABLE_LOGGING`** (Optional)
- Enable logging for orchestrated agent sessions
- Set to `"true"` for debugging purposes
- Logs agent execution details

**`MCP_SERVER_DEBUG`** (Optional)
- Enable debug logging for the MCP server itself
- Set to `"true"` to write logs to `logs/mcp-server.log`
- Logs include server startup, tool calls, script execution, and errors

**`PATH`** (Claude Desktop Only)
- Required for Claude Desktop because UI applications do not inherit shell environment PATH
- Must include the directory containing the `node` binary
- Common values:
  - macOS with Homebrew: `/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin`
  - macOS with nvm: `/Users/yourname/.nvm/versions/node/v20.x.x/bin:/usr/local/bin:/usr/bin:/bin`

## Configuration Examples

For complete setup instructions and configuration examples for different use cases, see:
- **Quick setup**: [GETTING_STARTED.md](./GETTING_STARTED.md)
- **Advanced configurations**: [SETUP_GUIDE.md](./SETUP_GUIDE.md)

## Tools Reference

### 1. list_agents

Lists all available specialized agent definitions.

**Parameters**:
- `response_format` (optional): `"markdown"` or `"json"` (default: `"markdown"`)

**Example**:
```typescript
{
  "response_format": "json"
}
```

**Response** (JSON format):
```json
{
  "total": 3,
  "agents": [
    {
      "name": "system-architect",
      "description": "Expert in designing scalable system architectures"
    },
    {
      "name": "code-reviewer",
      "description": "Reviews code for best practices and improvements"
    },
    {
      "name": "documentation-writer",
      "description": "Creates comprehensive technical documentation"
    }
  ]
}
```

### 2. list_sessions

Lists all existing agent sessions with their session IDs.

**Parameters**:
- `response_format` (optional): `"markdown"` or `"json"` (default: `"markdown"`)

**Example**:
```typescript
{
  "response_format": "json"
}
```

**Response** (JSON format):
```json
{
  "total": 2,
  "sessions": [
    {
      "name": "architect",
      "session_id": "3db5dca9-6829-4cb7-a645-c64dbd98244d"
    },
    {
      "name": "reviewer",
      "session_id": "initializing"
    }
  ]
}
```

### 3. start_agent

Creates a new orchestrated agent session.

**Parameters**:
- `session_name` (required): Unique session name (alphanumeric, dash, underscore; max 60 chars)
- `agent_name` (optional): Name of agent definition to use
- `prompt` (required): Initial task description

**Example**:
```typescript
{
  "session_name": "architect",
  "agent_name": "system-architect",
  "prompt": "Design a microservices architecture for an e-commerce platform"
}
```

**Response**: The agent's result after completing the task.

### 4. resume_agent

Resumes an existing agent session with a new prompt.

**Parameters**:
- `session_name` (required): Name of existing session to resume
- `prompt` (required): Continuation prompt

**Example**:
```typescript
{
  "session_name": "architect",
  "prompt": "Add security considerations to the architecture design"
}
```

**Response**: The agent's result after processing the new prompt.

### 5. clean_sessions

Removes all agent sessions permanently.

**Parameters**: None

**Example**:
```typescript
{}
```

**Response**: Confirmation message (e.g., "All sessions removed" or "No sessions to remove").

## Session Naming Rules

Session names must follow these constraints:
- **Length**: 1-60 characters
- **Characters**: Only alphanumeric, dash (`-`), and underscore (`_`)
- **Uniqueness**: Cannot create a session with a name that already exists
- **Examples**: `architect`, `code-reviewer`, `my_agent_123`, `dev-session-1`

## Error Handling

The server provides clear, actionable error messages:

- **Session already exists**: Use `resume_agent` or choose a different name
- **Session does not exist**: Use `start_agent` to create it first
- **Invalid session name**: Check naming rules (alphanumeric, dash, underscore; max 60 chars)
- **Agent not found**: Use `list_agents` to see available agents
- **Script execution failed**: Check that the script path and environment variables are configured correctly

## Development

### Project Structure

```
agent-orchestrator-mcp-server/
├── src/
│   ├── index.ts          # Main MCP server with tool implementations
│   ├── types.ts          # TypeScript type definitions
│   ├── schemas.ts        # Zod validation schemas
│   ├── constants.ts      # Constants and configuration
│   └── utils.ts          # Shared utility functions
├── dist/                 # Compiled JavaScript (generated)
├── package.json          # Dependencies and scripts
├── tsconfig.json         # TypeScript configuration
└── README.md             # This file
```

### Building

```bash
# Clean build artifacts
npm run clean

# Build TypeScript to JavaScript
npm run build

# Development with auto-reload
npm run dev
```

### Testing

After building, you can test the server using the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector node dist/index.js
```

Make sure to set the required environment variables before testing.

## Debugging and Troubleshooting

The MCP server includes comprehensive debug logging to help troubleshoot issues.

### Enabling Debug Logging

Debug logging is **disabled by default**. To enable it, set the `MCP_SERVER_DEBUG` environment variable to `"true"`:

```bash
export MCP_SERVER_DEBUG="true"
```

Or add it to your MCP configuration:
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "node",
      "args": ["/path/to/dist/index.js"],
      "env": {
        "AGENT_ORCHESTRATOR_SCRIPT_PATH": "/path/to/agent-orchestrator.sh",
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/project",
        "MCP_SERVER_DEBUG": "true"
      }
    }
  }
}
```

### Debug Logs Location

When enabled, all debug logs are written to:
```
agent-orchestrator-mcp-server/logs/mcp-server.log
```

### What's Logged

The logs include:
- **Server startup**: Configuration, environment variables, working directory
- **Tool calls**: Which tools are called with what parameters
- **Script execution**: Full command-line arguments, environment, stdout/stderr
- **Errors**: Detailed error messages with stack traces
- **Performance**: Execution duration for long-running operations

### Viewing Logs

**View the entire log file**:
```bash
cat agent-orchestrator-mcp-server/logs/mcp-server.log
```

**View formatted logs** (each line is JSON):
```bash
cat agent-orchestrator-mcp-server/logs/mcp-server.log | jq '.'
```

**Follow logs in real-time**:
```bash
tail -f agent-orchestrator-mcp-server/logs/mcp-server.log | jq '.'
```

**Filter by log level**:
```bash
# Show only errors
cat agent-orchestrator-mcp-server/logs/mcp-server.log | jq 'select(.level == "ERROR")'

# Show errors and warnings
cat agent-orchestrator-mcp-server/logs/mcp-server.log | jq 'select(.level == "ERROR" or .level == "WARN")'
```

**Search for specific operations**:
```bash
# Find all start_agent calls
cat agent-orchestrator-mcp-server/logs/mcp-server.log | jq 'select(.message | contains("start_agent"))'
```

### Common Issues

1. **`start_agent` fails but `list_agents` works**:
   - Check that the `claude` CLI is installed and in PATH
   - Review script execution logs for the exact error
   - Verify `AGENT_ORCHESTRATOR_PROJECT_DIR` is set correctly (or omit it to use current directory)

2. **Script execution errors**:
   - Look for "Script execution error" or "Script execution completed" log entries
   - Check the `exitCode`, `stdout`, and `stderr` fields in the logs
   - Verify the script path in `AGENT_ORCHESTRATOR_SCRIPT_PATH` is correct and executable

3. **Environment issues**:
   - Check the "Agent Orchestrator MCP Server starting" log entry
   - Verify all environment variables are set correctly
   - Check that `PWD` and `PATH` are what you expect

## Requirements

- **Node.js**: >= 18
- **TypeScript**: ^5.7.2
- **MCP SDK**: ^1.6.1
- **Zod**: ^3.23.8

## License

MIT

## Related Projects

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)
- Agent Orchestrator Script (referenced by this server)
