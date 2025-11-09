# Agent Orchestrator MCP Server - Usage Guide

This guide provides concise instructions for using the Agent Orchestrator MCP Server with Claude Code and Claude Desktop.

## What is the Orchestrated Agent Framework (OAF)?

The **Orchestrated Agent Framework (OAF)** enables you to create and manage specialized Claude Code agent sessions that work autonomously on specific tasks. The MCP server provides tools to orchestrate these agents from Claude Code or Claude Desktop.

**OAF infrastructure consists of**:
- **Agent definitions**: Specialized agent configurations stored in `.agent-orchestrator/agents/`
- **Sessions**: Active or completed agent work sessions stored in `.agent-orchestrator/sessions/`

This guide will help you configure where this infrastructure lives - in your current project, a remote project, or a combination of both.

---

## Build and Preparation

### 1. Install Dependencies and Build

```bash
cd agent-orchestrator-mcp-server
npm install
npm run build
```

The build process creates a `dist/` folder containing the compiled MCP server. The main entry point is `dist/index.js` - this is the file that **AGENT_ORCHESTRATOR_SCRIPT_PATH** in your MCP configuration should point to.

### 2. Verify Build Output

Ensure the following file exists:
```
agent-orchestrator-mcp-server/dist/index.js
```

This is the compiled MCP server script that will be invoked by Claude Code or Claude Desktop.

---

## General MCP Configuration

All configurations require the following environment variables:

### Required Environment Variables

- **`AGENT_ORCHESTRATOR_SCRIPT_PATH`**: Absolute path to the **agent-orchestrator.sh** script (not the MCP server)
  - Example: `/Users/yourname/projects/claude-dev-skills/agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh`

### Optional Environment Variables

- **`AGENT_ORCHESTRATOR_PROJECT_DIR`**: Directory where orchestrated agents should be started
  - If omitted, defaults to the current directory where the MCP server is invoked

- **`AGENT_ORCHESTRATOR_SESSIONS_DIR`**: Custom location for session data storage
  - If omitted, defaults to `$AGENT_ORCHESTRATOR_PROJECT_DIR/.agent-orchestrator/sessions`

- **`AGENT_ORCHESTRATOR_AGENTS_DIR`**: Custom location for agent definitions
  - If omitted, defaults to `$AGENT_ORCHESTRATOR_PROJECT_DIR/.agent-orchestrator/agents`

- **`AGENT_ORCHESTRATOR_ENABLE_LOGGING=true`**: Enable logging for debugging purposes (optional)

- **`MCP_SERVER_DEBUG=true`**: Enable debug logging for the MCP server itself (optional)

### Important Note for Claude Desktop

**Claude Desktop does not inherit the PATH environment variable from your shell.** You must explicitly set the `PATH` variable in the Claude Desktop configuration to include the path to your Node.js binary.

Example PATH value for macOS with Homebrew:
```
/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin
```

---

## Claude Code Usage

### Configuration Files

Claude Code uses two configuration files for MCP servers:

1. **`.mcp.json`**: Project-level MCP configuration (can be committed to repo)
2. **`.claude/settings.local.json`**: Local settings with machine-specific paths (should NOT be committed)

### Use Case 1: Local Project (Same Directory)

**When to use**: You're working in a single project and want orchestrated agents to assist within that same project.

**What happens**: Agent definitions, sessions, and work all stay in your current Claude Code project directory.

**Configuration**:

Create or update `.mcp.json`:
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "node",
      "args": ["${AGENT_ORCHESTRATOR_MCP_DIST_PATH}"]
    }
  }
}
```

Create or update `.claude/settings.local.json`:
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "env": {
        "AGENT_ORCHESTRATOR_MCP_DIST_PATH": "/absolute/path/to/agent-orchestrator-mcp-server/dist/index.js",
        "AGENT_ORCHESTRATOR_SCRIPT_PATH": "/absolute/path/to/agent-orchestrator.sh"
      }
    }
  }
}
```

**Key Points**:
- **`AGENT_ORCHESTRATOR_PROJECT_DIR` can be omitted** - defaults to current Claude Code project directory
- Session data stored in `.agent-orchestrator/sessions/` within current project
- Agent definitions in `.agent-orchestrator/agents/` within current project
- `.mcp.json` contains only placeholders (safe to commit)
- `.claude/settings.local.json` contains actual paths (do NOT commit)

### Use Case 2: Remote Project (Different Directory)

**When to use**: Keep the target project completely unaware of the orchestrator framework - manage all orchestration from a separate coordination project.

**What happens**:
- Current project = all OAF infrastructure (agent definitions, sessions)
- Target project = just a working directory where agents execute tasks
- Target project remains clean with no `.agent-orchestrator/` folder

**Configuration**:

Create or update `.mcp.json`:
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "node",
      "args": ["${AGENT_ORCHESTRATOR_MCP_DIST_PATH}"]
    }
  }
}
```

Create or update `.claude/settings.local.json`:
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "env": {
        "AGENT_ORCHESTRATOR_MCP_DIST_PATH": "/absolute/path/to/agent-orchestrator-mcp-server/dist/index.js",
        "AGENT_ORCHESTRATOR_SCRIPT_PATH": "/absolute/path/to/agent-orchestrator.sh",
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/target/project",
        "AGENT_ORCHESTRATOR_SESSIONS_DIR": "/absolute/path/to/current/coordination/project/.agent-orchestrator/sessions",
        "AGENT_ORCHESTRATOR_AGENTS_DIR": "/absolute/path/to/current/coordination/project/.agent-orchestrator/agents"
      }
    }
  }
}
```

**Key Points**:
- **Requires manual absolute paths** - Claude Code doesn't support directory variables
- All OAF infrastructure stays in your coordination project
- Target project has zero knowledge of the orchestrator
- Useful for managing work across multiple unrelated projects from one coordination hub

### Use Case 3: Hybrid Approach (Remote Agents, Local Sessions)

**When to use**: Use target project's specialized agent definitions while managing sessions from your coordination project.

**What happens**:
- Current project = session data only
- Target project = agent definitions (`.agent-orchestrator/agents/`)
- Target project is aware of OAF but doesn't track session history
- Best for projects with project-specific agents you want to reuse

**Configuration**:

Create or update `.mcp.json`:
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "node",
      "args": ["${AGENT_ORCHESTRATOR_MCP_DIST_PATH}"]
    }
  }
}
```

Create or update `.claude/settings.local.json`:
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "env": {
        "AGENT_ORCHESTRATOR_MCP_DIST_PATH": "/absolute/path/to/agent-orchestrator-mcp-server/dist/index.js",
        "AGENT_ORCHESTRATOR_SCRIPT_PATH": "/absolute/path/to/agent-orchestrator.sh",
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/target/project",
        "AGENT_ORCHESTRATOR_SESSIONS_DIR": "/absolute/path/to/current/coordination/project/.agent-orchestrator/sessions"
      }
    }
  }
}
```

**Key Points**:
- **`AGENT_ORCHESTRATOR_AGENTS_DIR` is omitted** - defaults to `$AGENT_ORCHESTRATOR_PROJECT_DIR/.agent-orchestrator/agents`
- Target project provides specialized agent definitions for its domain
- Session tracking stays in your coordination project for centralized management
- Hybrid approach: target project is OAF-aware (has agents) but sessions are external

---

## Claude Desktop Usage

### Use Case: Control Orchestrated Agents from Claude Desktop

**Scenario**: Manage orchestrated agents in a Claude Code project from Claude Desktop.

### Configuration

1. **Locate Claude Desktop configuration file**:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. **Add MCP server configuration**:

```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "node",
      "args": [
        "/absolute/path/to/agent-orchestrator-mcp-server/dist/index.js"
      ],
      "env": {
        "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin",
        "AGENT_ORCHESTRATOR_SCRIPT_PATH": "/absolute/path/to/agent-orchestrator.sh",
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/claude/code/project"
      }
    }
  }
}
```

**Key Points**:
- **`PATH`** is **REQUIRED** - Claude Desktop doesn't inherit shell PATH
- **`AGENT_ORCHESTRATOR_SCRIPT_PATH`** must point to **agent-orchestrator.sh** (not the MCP server dist)
- **`AGENT_ORCHESTRATOR_PROJECT_DIR`** specifies where orchestrated agents run

### Optional: Customize Session and Agent Storage

If you want session data and agent definitions in the same project:
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "node",
      "args": ["/absolute/path/to/agent-orchestrator-mcp-server/dist/index.js"],
      "env": {
        "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin",
        "AGENT_ORCHESTRATOR_SCRIPT_PATH": "/absolute/path/to/agent-orchestrator.sh",
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/claude/code/project"
      }
    }
  }
}
```

Session and agent data will default to the project directory structure.

If you want to separate storage locations:
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "node",
      "args": ["/absolute/path/to/agent-orchestrator-mcp-server/dist/index.js"],
      "env": {
        "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin",
        "AGENT_ORCHESTRATOR_SCRIPT_PATH": "/absolute/path/to/agent-orchestrator.sh",
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/claude/code/project",
        "AGENT_ORCHESTRATOR_SESSIONS_DIR": "/custom/path/to/sessions",
        "AGENT_ORCHESTRATOR_AGENTS_DIR": "/custom/path/to/agents"
      }
    }
  }
}
```

### 3. Restart Claude Desktop

After updating the configuration, restart Claude Desktop for changes to take effect.

---

## Quick Reference

### Environment Variables Summary

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `AGENT_ORCHESTRATOR_SCRIPT_PATH` | Yes | Path to agent-orchestrator.sh script | - |
| `AGENT_ORCHESTRATOR_PROJECT_DIR` | No (Yes for Claude Desktop) | Where agents execute | Current directory (Claude Code only) |
| `AGENT_ORCHESTRATOR_SESSIONS_DIR` | No | Session data storage | `$PROJECT_DIR/.agent-orchestrator/sessions` |
| `AGENT_ORCHESTRATOR_AGENTS_DIR` | No | Agent definitions location | `$PROJECT_DIR/.agent-orchestrator/agents` |
| `PATH` | Claude Desktop only | Path to Node.js binary | - |
| `AGENT_ORCHESTRATOR_ENABLE_LOGGING` | No | Enable agent logging | false |
| `MCP_SERVER_DEBUG` | No | Enable MCP server debug logs | false |

### Common Paths

**macOS with Homebrew Node.js**:
```bash
PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin
```

**macOS with nvm**:
```bash
PATH=/Users/yourname/.nvm/versions/node/v20.x.x/bin:/usr/local/bin:/usr/bin:/bin
```

---

## Troubleshooting

### "AGENT_ORCHESTRATOR_SCRIPT_PATH environment variable is required"

**Solution**: Ensure the environment variable points to the **agent-orchestrator.sh** bash script, NOT the MCP server's dist/index.js.

### Tools not appearing in Claude Desktop

1. Verify PATH includes Node.js binary location
2. Check configuration file is valid JSON
3. Ensure all paths are absolute (not relative)
4. Restart Claude Desktop

### Enable Debug Logging

Add to environment configuration:
```json
"env": {
  "MCP_SERVER_DEBUG": "true",
  "AGENT_ORCHESTRATOR_ENABLE_LOGGING": "true"
}
```

View logs at: `agent-orchestrator-mcp-server/logs/mcp-server.log`

---

For more details, see [README.md](./README.md) and [QUICKSTART.md](./QUICKSTART.md).