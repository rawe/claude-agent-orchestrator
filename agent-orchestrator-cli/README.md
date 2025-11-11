# Agent Orchestrator CLI

A Python-based CLI for managing Claude AI agent sessions with progressive disclosure architecture optimized for LLM workflows.

## Philosophy: Progressive Disclosure for LLM Efficiency

This CLI is designed with a novel approach that prioritizes **token efficiency** and **on-demand context loading** for LLM-driven workflows:

### Why Split Commands?

1. **Token Efficiency**: Instead of loading one monolithic tool with all parameters upfront, each command is a separate script that only loads its specific parameters when called with `--help`
2. **Progressive Disclosure**: LLMs discover functionality gradually - first learning what commands exist, then loading detailed parameters only when needed
3. **Reduced Context Window**: No need to maintain all command signatures in the prompt simultaneously
4. **Better for LLM Development**: Smaller, focused scripts are easier for LLMs to understand and modify
5. **Extensibility**: Adding new commands doesn't increase the baseline context load
6. **Skills Pattern Compatible**: Works naturally with Claude Code's skills pattern - each command can be a skill

### vs. MCP (Model Context Protocol)

This approach complements or replaces MCP in scenarios where:
- You want fine-grained control over context loading
- Token efficiency is critical
- You need simpler, more maintainable tooling
- Progressive discovery is preferred over upfront schema exposure

### Architecture Pattern

```
1. LLM sees: List of available commands (minimal context)
2. LLM selects: A specific command to use
3. LLM calls: `command --help` to load detailed parameters
4. LLM executes: Command with proper arguments
```

This is a **pull-based** model (load on demand) vs MCP's **push-based** model (expose all schemas upfront).

## Project Structure

```
agent-orchestrator-cli/
├── commands/               # Command scripts with shared library
│   ├── ao-new              # Create new session
│   ├── ao-resume           # Resume existing session
│   ├── ao-status           # Check session status
│   ├── ao-get-result       # Extract session result
│   ├── ao-list-sessions    # List all sessions
│   ├── ao-list-agents      # List available agents
│   ├── ao-show-config      # Show session configuration
│   ├── ao-clean            # Clean all sessions
│   └── lib/                # Shared Python modules
│       ├── __init__.py
│       ├── config.py       # Configuration management
│       ├── session.py      # Session operations
│       ├── agent.py        # Agent loading
│       ├── claude_client.py # Claude SDK integration
│       └── utils.py        # Common utilities
├── docs/                   # Documentation
│   ├── architecture.md     # Progressive disclosure pattern
│   └── development.md      # Development guide
└── README.md               # This file
```

## Commands

Each command is a self-contained Python script using `uv` for dependency management:

| Command | Purpose | Example |
|---------|---------|---------|
| `ao-new` | Create a new session | `ao-new mysession -p "Write hello world"` |
| `ao-resume` | Resume existing session | `ao-resume mysession -p "Add tests"` |
| `ao-status` | Check session status | `ao-status mysession` |
| `ao-get-result` | Get session result | `ao-get-result mysession` |
| `ao-list-sessions` | List all sessions | `ao-list-sessions` |
| `ao-list-agents` | List available agents | `ao-list-agents` |
| `ao-show-config` | Show configuration | `ao-show-config mysession` |
| `ao-clean` | Clean all sessions | `ao-clean` |

## Installation

### Using uv (Recommended)

Each command is a standalone `uv` script - no installation needed! Just make them executable:

```bash
chmod +x commands/ao-*
export PATH="$PATH:/path/to/agent-orchestrator-cli/commands"
```

### Dependencies

- Python 3.11+
- `uv` (for running scripts): `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Usage for LLMs

### Discovery Pattern

1. **List available commands**:
   ```bash
   ls commands/ao-*
   ```

2. **Get command help** (load parameters on demand):
   ```bash
   ao-new --help
   ```

3. **Execute command**:
   ```bash
   ao-new mysession -p "Create a REST API"
   ```

### Example: LLM Workflow

```
User: "Create a new agent session to design an API"

LLM thinks: I need to create a session. Let me check what command to use.
LLM runs: ls commands/ao-*
LLM sees: ao-new, ao-resume, ao-status, ao-list-sessions, ao-list-agents...
LLM thinks: I need ao-new. Let me check its parameters.
LLM runs: ao-new --help
LLM sees: Full parameter details for ao-new
LLM executes: ao-new api-design --agent system-architect -p "Design REST API"
```

Only 3 tool calls, minimal context loaded at each step!

## Configuration

Configuration follows the same precedence as the bash version:

```
CLI Flags > Environment Variables > Defaults (PWD)
```

### Environment Variables

- `AGENT_ORCHESTRATOR_PROJECT_DIR` - Project directory
- `AGENT_ORCHESTRATOR_SESSIONS_DIR` - Sessions directory
- `AGENT_ORCHESTRATOR_AGENTS_DIR` - Agents directory
- `AGENT_ORCHESTRATOR_ENABLE_LOGGING` - Enable logging

### Configuration Loading

All commands use shared configuration logic from `lib/config.py` to ensure consistency.

## Development

### Creating a New Command

1. **Copy template** (or create from scratch):
   ```bash
   cp commands/ao-new commands/ao-mycommand
   ```

2. **Add uv shebang**:
   ```python
   #!/usr/commands/env -S uv run --script
   # /// script
   # requires-python = ">=3.11"
   # dependencies = [
   #     "anthropic",
   #     "typer",
   # ]
   # ///
   ```

3. **Import shared modules**:
   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).parent / "lib"))

   from config import load_config
   from utils import validate_session_name
   ```

4. **Implement command logic**

5. **Make executable**:
   ```bash
   chmod +x commands/ao-mycommand
   ```

### Code Reuse Strategy

**Shared logic goes in `lib/`**:
- Configuration loading
- Session validation and operations
- Agent loading and validation
- Claude API integration
- Common utilities

**Command-specific logic stays in `commands/`**:
- Argument parsing
- Command-specific validation
- Output formatting
- Error handling

This balances code reuse with maintainability of individual commands.

## Benefits of This Approach

### For LLMs
- **Minimal upfront context**: Only command names initially
- **On-demand detail loading**: Parameters loaded when needed
- **Clear mental model**: One command = one action
- **Easy to extend**: New commands don't affect existing context

### For Developers
- **Easy to modify**: Small, focused files
- **Clear boundaries**: Each command is independent
- **Simple testing**: Test commands individually
- **Gradual migration**: Can replace bash script command-by-command

### For Users
- **Familiar CLI**: Standard Unix command patterns
- **Discoverable**: `--help` works as expected
- **Composable**: Can pipe and chain commands
- **Fast**: No framework overhead, direct execution

## Migration from Bash

This replaces `/agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh` with:
- Python instead of Bash (better error handling, type safety)
- Split commands instead of monolithic script (progressive disclosure)
- `uv` for dependencies instead of system requirements (self-contained)

### Compatibility

File formats and behavior remain identical to the bash version for seamless migration.

## Integration Patterns

### Claude Code Skills

Each command can be a Claude Code skill:

```markdown
---
command: ao-new
description: Create a new agent orchestrator session
---

Creates a new Claude AI session with optional agent configuration.

Usage: Run `ao-new --help` for parameters.
```

### MCP Alternative

Instead of exposing all tools via MCP server, expose just a skill catalog:
- MCP server provides: `list_agent_commands`
- Each command self-documents via `--help`
- LLM loads details progressively

### Hybrid Approach

Use MCP for high-frequency operations, CLI for specialized/rare operations:
- MCP: Core session management (new, resume, status)
- CLI: Advanced operations (show-config, clean, list-agents)

## Status

**In Active Development**

- [x] Architecture design
- [x] Documentation
- [ ] Shared library modules
- [ ] Individual command scripts
- [ ] Testing framework
- [ ] Migration guide

## Related Projects

- [Agent Orchestrator Bash](../agent-orchestrator/skills/agent-orchestrator/) - Original implementation
- [Agent Orchestrator MCP Server](../agent-orchestrator-mcp-server/) - MCP-based interface
- [Agent Orchestrator Launcher](../agent-orchestrator-launcher/) - TypeScript docs/spec

## Philosophy Quote

> "The best design is the one that reveals itself progressively, showing exactly what you need, exactly when you need it."

This CLI embodies that philosophy for LLM-tool interaction.

---

**Next Steps**: See [docs/development.md](docs/development.md) for implementation guide.
