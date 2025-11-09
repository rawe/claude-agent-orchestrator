# Agent Orchestrator Framework (AOF)

A comprehensive framework for orchestrating specialized Claude Code agent sessions with multiple usage levels and integration approaches.

## What is the Agent Orchestrator Framework?

The Agent Orchestrator Framework (AOF) enables you to create, manage, and orchestrate specialized Claude Code agent sessions programmatically. Whether you want to delegate tasks to specialized agents, run long-running background processes, or manage multiple concurrent AI workflows, AOF provides the tools and abstractions you need.

**Key Capabilities:**
- Launch specialized Claude Code agent sessions programmatically
- Configure agents with custom system prompts and instructions
- Manage multiple concurrent agent sessions
- Inject different MCP server configurations per agent
- Extract and process results from completed agents
- Create reusable agent definitions for common tasks
- Support for long-running and background tasks

## Three Usage Levels

AOF provides three distinct usage levels, allowing you to choose the integration approach that best fits your needs:

### Level 1: Claude Code Plugin (Core Framework)

**Best for:** Direct, low-level control of agent orchestration within Claude Code

Install the `agent-orchestrator` plugin to get:
- The `agent-orchestrator.sh` script (1,203 lines of orchestration logic)
- 4 slash commands for agent management
- Skills for creating and managing agents
- Complete control over agent lifecycle

**Quick Start:**
```bash
# Install the plugin by adding this repo to Claude Code
# The plugin provides the core framework
```

**Usage Example:**
```
/agent-orchestrator-init
Use the agent-orchestrator skill to create a new session called "code-review"
```

**Documentation:** [agent-orchestrator/README.md](./agent-orchestrator/README.md)

---

### Level 2: Claude Code Plugin + Subagents Extension

**Best for:** Simplified, delegation-based workflow with pre-configured subagents

Install both the `agent-orchestrator` plugin AND the `agent-orchestrator-subagents` extension to get:
- All Level 1 capabilities
- Pre-configured Claude Code subagents for common tasks
- Natural language delegation interface
- Automatic session management

**Quick Start:**
```bash
# Install both plugins:
# 1. agent-orchestrator (core framework)
# 2. agent-orchestrator-subagents (extension)
```

**Usage Example:**
```
Use the orchestrated-agent-launcher subagent to create a new code review session
```

**Documentation:**
- [agent-orchestrator-subagents/README.md](./agent-orchestrator-subagents/README.md)
- [agent-orchestrator/README.md](./agent-orchestrator/README.md)

---

### Level 3: MCP Server (Protocol Abstraction)

**Best for:** Integration with any MCP-compatible AI system (Claude Desktop, other AI tools)

Use the standalone MCP server implementation to get:
- **No Claude Code plugin required!**
- Works with Claude Desktop, Claude Code, or any MCP-compatible system
- 5 MCP tools for agent orchestration
- TypeScript implementation with full type safety
- Works with the same `agent-orchestrator.sh` script

**Quick Start:**
```bash
# 1. Clone this repository
git clone <your-repo-url>

# 2. Build the MCP server
cd agent-orchestrator-mcp-server
npm install
npm run build

# 3. Configure in Claude Desktop or Claude Code
# See GETTING_STARTED.md for configuration examples
```

**Usage Example (from Claude Desktop):**
```
List available agents
Create a new agent session called "code-review" using the code-reviewer agent
```

**Documentation:** [agent-orchestrator-mcp-server/README.md](./agent-orchestrator-mcp-server/README.md)

---

## Which Level Should You Use?

| Usage Level | Use When... | Installation | Integration |
|-------------|-------------|--------------|-------------|
| **Level 1** | You want direct control within Claude Code | Install plugin | Claude Code only |
| **Level 2** | You want simplified delegation workflow | Install 2 plugins | Claude Code only |
| **Level 3** | You want to use with Claude Desktop or other AI systems | Build & configure MCP | Any MCP system |

**Can you use multiple levels?** Yes! Level 3 (MCP) can be used independently or alongside Level 1/2 plugins.

## Repository Structure

```
agent-orchestrator-framework/
├── agent-orchestrator/              # Level 1: Core framework plugin
│   ├── skills/
│   │   └── agent-orchestrator/
│   │       ├── agent-orchestrator.sh    # Core orchestration script (1,203 lines)
│   │       ├── SKILL.md                 # Skill definition
│   │       ├── references/              # Technical documentation
│   │       └── example/                 # Example agent definitions
│   ├── commands/                    # Slash commands
│   └── README.md
│
├── agent-orchestrator-subagents/    # Level 2: Subagents extension plugin
│   ├── agents/
│   │   ├── orchestrated-agent-launcher.md
│   │   └── orchestrated-agent-lister.md
│   └── README.md
│
├── agent-orchestrator-mcp-server/   # Level 3: MCP server implementation
│   ├── src/                         # TypeScript source
│   ├── dist/                        # Compiled output
│   ├── README.md                    # Full documentation
│   ├── GETTING_STARTED.md           # Quick setup guide
│   └── SETUP_GUIDE.md               # Integration scenarios
│
├── cli-agent-runner/                # Earlier/simpler version (kept for compatibility)
│
├── firstspirit-templating/          # Additional plugin: FirstSpirit CMS templating
├── firstspirit-fs-cli/              # Additional plugin: FirstSpirit CLI tools
│
└── README.md                        # This file
```

## Quick Start Guide

### For Claude Code Users (Level 1 or 2)

1. **Add this repository to Claude Code:**
   - Your repository URL will point to this marketplace
   - Claude Code will discover all available plugins

2. **Choose your plugins:**
   - **Level 1**: Install `agent-orchestrator` only
   - **Level 2**: Install both `agent-orchestrator` and `agent-orchestrator-subagents`

3. **Start orchestrating:**
   ```
   /agent-orchestrator-init
   ```

### For Claude Desktop Users (Level 3)

1. **Clone and build:**
   ```bash
   git clone <your-repo-url>
   cd agent-orchestrator-framework/agent-orchestrator-mcp-server
   npm install
   npm run build
   ```

2. **Configure MCP server:**
   See [agent-orchestrator-mcp-server/GETTING_STARTED.md](./agent-orchestrator-mcp-server/GETTING_STARTED.md)

3. **Use from Claude Desktop:**
   ```
   List available agents
   ```

## Core Concepts

### Agent Definitions
Markdown files that define specialized agent configurations with custom system prompts, instructions, and MCP configurations. Stored in `.agent-orchestrator/agents/`.

### Sessions
Isolated Claude Code sessions for individual agents. Each session has a unique ID, configuration, and result storage. Stored in `.agent-orchestrator/sessions/`.

### MCP Configuration
Different agents can have different MCP server configurations, enabling specialized capabilities per agent type.

### Orchestration Script
The `agent-orchestrator.sh` bash script is the foundation of all three usage levels. It handles session lifecycle, agent configuration, and result extraction.

## Additional Plugins

This repository also contains these additional plugins (not part of the core AOF):

### FirstSpirit Templating
Comprehensive knowledge for templating in the FirstSpirit CMS, specifically focused on SiteArchitect development.

### FirstSpirit CLI (fs-cli)
FirstSpirit CMS template development using fs-cli.

### CLI Agent Runner
Earlier/simpler version of agent orchestration (kept for compatibility).

## Documentation

- **[Level 1: Core Framework](./agent-orchestrator/README.md)** - Plugin documentation
- **[Level 2: Subagents Extension](./agent-orchestrator-subagents/README.md)** - Extension plugin
- **[Level 3: MCP Server](./agent-orchestrator-mcp-server/README.md)** - MCP implementation
- **[Technical Architecture](./agent-orchestrator/skills/agent-orchestrator/references/AGENT-ORCHESTRATOR.md)** - Deep dive into how it works

## Contributing

To add a new plugin to this marketplace:

1. Add your plugin directory to the repository root
2. Each plugin can contain multiple skills, commands, and configuration files
3. Update `.claude-plugin/marketplace.json` with your plugin's metadata
4. Submit a pull request
