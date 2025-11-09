# Setup Guide - Integration Scenarios

This guide explains how to configure the Agent Orchestrator MCP Server for different use cases with Claude Code and Claude Desktop.

> 📖 **What is OAF?** See [README.md - Overview](./README.md#overview) for an explanation of the Orchestrated Agent Framework and how this MCP server works.

This guide helps you configure where OAF infrastructure (agent definitions and sessions) lives - in your current project, a remote project, or a combination of both.

---

## Prerequisites

Before configuring, ensure you have installed and built the MCP server:

**See [GETTING_STARTED.md](./GETTING_STARTED.md) for installation instructions.**

---

## Environment Variables Quick Reference

> 📖 **For complete environment variable documentation**, see [README.md - Environment Variables Reference](./README.md#environment-variables-reference)

This table shows **which variables to use for each use case**:

| Variable | Use Case 1<br>(Local) | Use Case 2<br>(Remote) | Use Case 3<br>(Hybrid) | Claude Desktop |
|----------|------------|------------|------------|----------------|
| `AGENT_ORCHESTRATOR_SCRIPT_PATH` | ✅ Required | ✅ Required | ✅ Required | ✅ Required |
| `AGENT_ORCHESTRATOR_PROJECT_DIR` | ❌ Omit (defaults to current) | ✅ Set to target | ✅ Set to target | ✅ Required |
| `AGENT_ORCHESTRATOR_SESSIONS_DIR` | ❌ Default | ✅ Set to current | ✅ Set to current | ⚙️ Optional |
| `AGENT_ORCHESTRATOR_AGENTS_DIR` | ❌ Default | ✅ Set to current | ❌ Default (use target's) | ⚙️ Optional |
| `PATH` | ❌ Not needed | ❌ Not needed | ❌ Not needed | ✅ Required |
| `AGENT_ORCHESTRATOR_ENABLE_LOGGING` | ⚙️ Optional | ⚙️ Optional | ⚙️ Optional | ⚙️ Optional |
| `MCP_SERVER_DEBUG` | ⚙️ Optional | ⚙️ Optional | ⚙️ Optional | ⚙️ Optional |

**Legend**: ✅ Required | ❌ Omit/Default | ⚙️ Optional for debugging

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

> 📖 See [README.md - Environment Variables Reference](./README.md#environment-variables-reference) for variable details and defaults

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

> 📖 See [README.md - Environment Variables Reference](./README.md#environment-variables-reference) for variable details and defaults

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

> 📖 See [README.md - Environment Variables Reference](./README.md#environment-variables-reference) for variable details and defaults

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

> 📖 See [README.md - Environment Variables Reference](./README.md#environment-variables-reference) for variable details, defaults, and PATH examples

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

For complete environment variable documentation including descriptions, defaults, and common PATH values:

> 📖 [README.md - Environment Variables Reference](./README.md#environment-variables-reference)

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

For comprehensive debugging instructions, see [README.md - Debugging and Troubleshooting](./README.md#debugging-and-troubleshooting).

---

## Additional Resources

- **Quick setup**: [GETTING_STARTED.md](./GETTING_STARTED.md) - Fast path to get running
- **Complete reference**: [README.md](./README.md) - Full documentation and API reference
- **Environment variables**: [README.md - Environment Variables Reference](./README.md#environment-variables-reference)