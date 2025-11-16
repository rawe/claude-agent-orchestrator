# Integration Scenarios

Choose the right integration pattern for your workflow. This guide explains three scenarios for organizing Agent Orchestrator Framework (AOF) infrastructure:

- **Scenario 1: Local Project** - Everything in one project directory
- **Scenario 2: Remote Project** - Coordinate from separate directory, target project stays clean
- **Scenario 3: Hybrid** - Use target's agents, manage sessions centrally

Each scenario determines where agent definitions and sessions live, and how you configure the MCP server.

---

## Prerequisites

Before configuring, ensure you have UV installed and Python ≥3.10.

---

## MCP Configuration Schema

All MCP configurations follow this structure:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `command` | string | Yes | Must be `"uv"` |
| `args` | array | Yes | `["run", "/absolute/path/to/agent-orchestrator-mcp.py"]` |
| `env` | object | Yes | Environment variables (see Environment Variables Quick Reference below) |

---

## Environment Variables Quick Reference

> 📖 **For complete environment variable documentation**, see [ENV_VARS.md](./ENV_VARS.md)

This table shows **which variables to use for each use case**:

| Variable | Use Case 1<br>(Local) | Use Case 2<br>(Remote) | Use Case 3<br>(Hybrid) | Claude Desktop |
|----------|------------|------------|------------|----------------|
| `AGENT_ORCHESTRATOR_COMMAND_PATH` | ✅ Required | ✅ Required | ✅ Required | ✅ Required |
| `AGENT_ORCHESTRATOR_PROJECT_DIR` | ❌ Omit (defaults to current) | ✅ Set to target | ✅ Set to target | ✅ Required |
| `AGENT_ORCHESTRATOR_SESSIONS_DIR` | ❌ Default | ✅ Set to current | ✅ Set to current | ⚙️ Optional |
| `AGENT_ORCHESTRATOR_AGENTS_DIR` | ❌ Default | ✅ Set to current | ❌ Default (use target's) | ⚙️ Optional |
| `PATH` | ❌ Not needed | ❌ Not needed | ❌ Not needed | ✅ Required |
| `AGENT_ORCHESTRATOR_ENABLE_LOGGING` | ⚙️ Optional | ⚙️ Optional | ⚙️ Optional | ⚙️ Optional |
| `MCP_SERVER_DEBUG` | ⚙️ Optional | ⚙️ Optional | ⚙️ Optional | ⚙️ Optional |

**Legend**: ✅ Required | ❌ Omit/Default | ⚙️ Optional for debugging

---

## Per-Tool Project Directory Override

All MCP tools accept an optional `project_dir` parameter that allows you to override the project directory on a per-tool-call basis:

- **When to use**: Override the environment-configured `AGENT_ORCHESTRATOR_PROJECT_DIR` for specific tool calls
- **Format**: Must be an absolute path (e.g., `/absolute/path/to/project`)
- **Important**: Only set when explicitly instructed to set a project dir!
- **Precedence**: Tool parameter > Environment variable > Current directory (PWD)

**Example**:
```python
{
  "session_name": "architect",
  "project_dir": "/absolute/path/to/different/project",
  "prompt": "Analyze this project's structure"
}
```

This feature is useful when you need to temporarily work with a different project without reconfiguring environment variables.

---

## Claude Code Usage

### Use Case 1: Local Project (Same Directory)

**When to use**: You're working in a single project and want orchestrated agents to assist within that same project.

**What happens**: Agent definitions, sessions, and work all stay in your current Claude Code project directory.

**Configuration**:

Create `simple.mcp.json` in your project root:
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "uv",
      "args": ["run", "/absolute/path/to/agent-orchestrator-mcp.py"],
      "env": {
        "AGENT_ORCHESTRATOR_COMMAND_PATH": "/absolute/path/to/commands"
      }
    }
  }
}
```

**Key Points**:
- **`AGENT_ORCHESTRATOR_PROJECT_DIR` can be omitted** - defaults to current Claude Code project directory
- Session data stored in `.agent-orchestrator/sessions/` within current project
- Agent definitions in `.agent-orchestrator/agents/` within current project
- Replace paths with your actual absolute paths

> 📖 See [ENV_VARS.md](./ENV_VARS.md) for variable details and defaults

### Use Case 2: Remote Project (Different Directory)

**When to use**: Keep the target project completely unaware of the orchestrator framework - manage all orchestration from a separate coordination project.

**What happens**:
- Current project = all AOF infrastructure (agent definitions, sessions)
- Target project = just a working directory where agents execute tasks
- Target project remains clean with no `.agent-orchestrator/` folder

**Configuration**:

Create `simple.mcp.json` in your coordination project:
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "uv",
      "args": ["run", "/absolute/path/to/agent-orchestrator-mcp.py"],
      "env": {
        "AGENT_ORCHESTRATOR_COMMAND_PATH": "/absolute/path/to/commands",
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/target/project",
        "AGENT_ORCHESTRATOR_SESSIONS_DIR": "/absolute/path/to/current/coordination/project/.agent-orchestrator/sessions",
        "AGENT_ORCHESTRATOR_AGENTS_DIR": "/absolute/path/to/current/coordination/project/.agent-orchestrator/agents"
      }
    }
  }
}
```

**Key Points**:
- All AOF infrastructure stays in your coordination project
- Target project has zero knowledge of the orchestrator
- Useful for managing work across multiple unrelated projects from one coordination hub
- All paths must be absolute

> 📖 See [ENV_VARS.md](./ENV_VARS.md) for variable details and defaults

### Use Case 3: Hybrid Approach (Remote Agents, Local Sessions)

**When to use**: Use target project's specialized agent definitions while managing sessions from your coordination project.

**What happens**:
- Current project = session data only
- Target project = agent definitions (`.agent-orchestrator/agents/`)
- Target project is aware of AOF but doesn't track session history
- Best for projects with project-specific agents you want to reuse

**Configuration**:

Create `simple.mcp.json` in your coordination project:
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "uv",
      "args": ["run", "/absolute/path/to/agent-orchestrator-mcp.py"],
      "env": {
        "AGENT_ORCHESTRATOR_COMMAND_PATH": "/absolute/path/to/commands",
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
- Hybrid approach: target project is AOF-aware (has agents) but sessions are external

> 📖 See [ENV_VARS.md](./ENV_VARS.md) for variable details and defaults

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

**Basic Configuration**:
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "uv",
      "args": [
        "run",
        "/absolute/path/to/agent-orchestrator-mcp.py"
      ],
      "env": {
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin",
        "AGENT_ORCHESTRATOR_COMMAND_PATH": "/absolute/path/to/commands",
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/project"
      }
    }
  }
}
```

**Key Points**:
- **`PATH`** is **REQUIRED** - Claude Desktop doesn't inherit shell PATH
- Must include paths to `uv` and `claude` binaries
- **`AGENT_ORCHESTRATOR_COMMAND_PATH`** must point to commands directory
- **`AGENT_ORCHESTRATOR_PROJECT_DIR`** specifies where orchestrated agents run

> 📖 See [ENV_VARS.md](./ENV_VARS.md) for variable details, defaults, and PATH examples

### Optional: Customize Session and Agent Storage

**Default behavior** (all in project directory):
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "uv",
      "args": ["run", "/absolute/path/to/agent-orchestrator-mcp.py"],
      "env": {
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin",
        "AGENT_ORCHESTRATOR_COMMAND_PATH": "/absolute/path/to/commands",
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/project"
      }
    }
  }
}
```

Session and agent data will default to the project directory structure (`.agent-orchestrator/` subdirectories).

**Separate storage locations**:
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "uv",
      "args": ["run", "/absolute/path/to/agent-orchestrator-mcp.py"],
      "env": {
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin",
        "AGENT_ORCHESTRATOR_COMMAND_PATH": "/absolute/path/to/commands",
        "AGENT_ORCHESTRATOR_PROJECT_DIR": "/path/to/project",
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

> 📖 [ENV_VARS.md](./ENV_VARS.md)

---

## Troubleshooting

### "AGENT_ORCHESTRATOR_COMMAND_PATH environment variable is required"

**Solution**: Ensure the environment variable points to the **commands directory** containing Python scripts (`ao-new`, `ao-resume`, etc.).

### Tools not appearing in Claude Desktop

1. Verify PATH includes `uv` and `claude` binary locations
2. Check configuration file is valid JSON
3. Ensure all paths are absolute (not relative)
4. Verify UV is installed: `which uv`
5. Restart Claude Desktop

### UV or dependency errors

1. Ensure Python >= 3.10: `python3 --version`
2. Ensure UV is installed: `uv --version`
3. Test the server directly: `uv run /path/to/agent-orchestrator-mcp.py`
4. Check internet connection for dependency downloads

### Enable Debug Logging

Add to environment configuration:
```json
"env": {
  "MCP_SERVER_DEBUG": "true",
  "AGENT_ORCHESTRATOR_ENABLE_LOGGING": "true"
}
```

View logs at: `agent-orchestrator-mcp-python/logs/mcp-server.log`

For comprehensive debugging instructions, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).

---

## Additional Resources

- **Complete reference**: [README.md](./README.md) - Overview and quick reference
- **Tools API**: [TOOLS_REFERENCE.md](./TOOLS_REFERENCE.md) - Detailed tool documentation
- **Debugging**: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Comprehensive troubleshooting guide
- **Environment variables**: [ENV_VARS.md](./ENV_VARS.md)
- **Architecture**: [ARCHITECTURE.md](./ARCHITECTURE.md) - UV standalone implementation details
