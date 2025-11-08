# Agent Orchestrator MCP Server

A Model Context Protocol (MCP) server that provides tools for orchestrating specialized Claude Code agents through the agent-orchestrator.sh script.

## Overview

This MCP server enables LLMs to manage and interact with specialized Claude Code agent sessions. It wraps the `agent-orchestrator.sh` bash script to provide a clean, type-safe interface for:

- Discovering available specialized agent definitions
- Creating new agent sessions (generic or specialized)
- Resuming existing agent sessions
- Listing active sessions
- Cleaning up sessions

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

1. **Install dependencies**:
```bash
npm install
```

2. **Build the TypeScript code**:
```bash
npm run build
```

3. **Set required environment variables**:
```bash
export AGENT_ORCHESTRATOR_SCRIPT_PATH="/absolute/path/to/agent-orchestrator.sh"
export AGENT_ORCHESTRATOR_PROJECT_DIR="/path/to/your/project"  # Recommended: controls where claude runs and where data is stored
```

## Configuration

The MCP server requires the following environment variables:

### Required

- **`AGENT_ORCHESTRATOR_SCRIPT_PATH`**: Absolute path to the `agent-orchestrator.sh` script
  ```bash
  export AGENT_ORCHESTRATOR_SCRIPT_PATH="/Users/yourname/path/to/agent-orchestrator.sh"
  ```

### Agent Orchestrator Script Configuration

These environment variables control how the `agent-orchestrator.sh` script operates:

- **`AGENT_ORCHESTRATOR_PROJECT_DIR`** (recommended): Project directory where the `claude` command runs
  - If not set, defaults to the directory where the script is called from
  - This is where agents will execute and is the base for other defaults
  ```bash
  export AGENT_ORCHESTRATOR_PROJECT_DIR="/Users/yourname/your-project"
  ```

- **`AGENT_ORCHESTRATOR_SESSIONS_DIR`** (optional): Custom location for agent session storage
  - If not set, defaults to `$AGENT_ORCHESTRATOR_PROJECT_DIR/.agent-orchestrator/sessions`
  - Use this for centralized session management across multiple projects
  ```bash
  export AGENT_ORCHESTRATOR_SESSIONS_DIR="/custom/path/to/sessions"
  ```

- **`AGENT_ORCHESTRATOR_AGENTS_DIR`** (optional): Custom location for agent definitions
  - If not set, defaults to `$AGENT_ORCHESTRATOR_PROJECT_DIR/.agent-orchestrator/agents`
  - Use this to share agent definitions across multiple projects
  ```bash
  export AGENT_ORCHESTRATOR_AGENTS_DIR="/custom/path/to/agents"
  ```

## Usage

### Running the Server

**Development mode** (with auto-reload):
```bash
npm run dev
```

**Production mode**:
```bash
npm start
```

### MCP Configuration

Add this server to your MCP settings (e.g., Claude Desktop configuration):

```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "node",
      "args": [
        "/absolute/path/to/agent-orchestrator-mcp-server/dist/index.js"
      ],
      "env": {
        "AGENT_ORCHESTRATOR_SCRIPT_PATH": "/absolute/path/to/agent-orchestrator.sh",
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/your/project"
      }
    }
  }
}
```

For more control over where sessions and agent definitions are stored, you can add:

```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "node",
      "args": [
        "/absolute/path/to/agent-orchestrator-mcp-server/dist/index.js"
      ],
      "env": {
        "AGENT_ORCHESTRATOR_SCRIPT_PATH": "/absolute/path/to/agent-orchestrator.sh",
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/your/project",
        "AGENT_ORCHESTRATOR_SESSIONS_DIR": "/custom/path/to/sessions",
        "AGENT_ORCHESTRATOR_AGENTS_DIR": "/custom/path/to/agents"
      }
    }
  }
}
```

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

### Debug Logs Location

All debug logs are written to:
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
