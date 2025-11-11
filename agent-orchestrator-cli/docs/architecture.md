# Progressive Disclosure Architecture

## Overview

The Agent Orchestrator CLI uses a **progressive disclosure** architecture specifically designed for LLM-driven workflows. This document explains the pattern, rationale, and implementation details.

## The Problem with Traditional CLIs for LLMs

### Traditional Approach: Monolithic Commands

```bash
# One command, many subcommands
agent-orchestrator <command> [options]

# LLM must understand all commands upfront:
- agent-orchestrator new <session> --agent <agent> -p <prompt> [--project-dir] [--sessions-dir]...
- agent-orchestrator resume <session> -p <prompt> [--project-dir] [--sessions-dir]...
- agent-orchestrator status <session> [--project-dir] [--sessions-dir]...
...and so on
```

**Problems**:
1. **Large upfront context**: All subcommands and parameters loaded at once
2. **Redundant parameters**: Global options repeated for every command
3. **Complex mental model**: One tool with many modes
4. **Token waste**: Most parameters never used in any given interaction
5. **Harder to maintain prompts**: Changes require updating all documentation

### MCP Approach: Schema Exposure

```json
{
  "tools": [
    {
      "name": "create_session",
      "parameters": {...},  // Full schema
    },
    {
      "name": "resume_session",
      "parameters": {...},  // Full schema
    },
    // ... all tools with full schemas
  ]
}
```

**Problems**:
1. **All schemas loaded upfront**: Even for unused tools
2. **Token heavy**: JSON schemas are verbose
3. **Rigid**: Adding tools increases baseline context
4. **Always-on**: Can't progressively discover

## Progressive Disclosure Solution

### Pattern: Discover → Detail → Execute

```
Phase 1: DISCOVER (Minimal Context)
├─ LLM learns command names exist
├─ Brief one-line descriptions
└─ No parameter details yet

Phase 2: DETAIL (On-Demand Context)
├─ LLM calls: command --help
├─ Gets full parameter details
└─ Only for the specific command needed

Phase 3: EXECUTE (Focused Action)
├─ LLM calls command with arguments
└─ Clean, focused operation
```

### Implementation: One Command = One Script

```
commands/
├── ao-new              # Create session (standalone)
├── ao-resume           # Resume session (standalone)
├── ao-status           # Check status (standalone)
└── ...                 # Each command is independent
```

Each script:
- Is independently executable
- Self-documents via `--help`
- Shares code via `lib/` modules
- Has focused responsibility

## Token Efficiency Analysis

### Scenario: Create a new session

#### Traditional Monolithic (500+ tokens)
```
Tool: agent_orchestrator
Description: Manage agent sessions
Commands:
  - new: Create session
    Parameters: session_name (required), agent (optional), prompt (optional),
                project_dir (optional), sessions_dir (optional), agents_dir (optional)
  - resume: Resume session
    Parameters: session_name (required), prompt (optional),
                project_dir (optional), sessions_dir (optional)
  - status: Check session
    Parameters: session_name (required), project_dir (optional), sessions_dir (optional)
  - get-result: Get session result
    Parameters: session_name (required), project_dir (optional), sessions_dir (optional)
  - list: List sessions
    Parameters: project_dir (optional), sessions_dir (optional)
  - list-agents: List agents
    Parameters: project_dir (optional), agents_dir (optional)
  - show-config: Show configuration
    Parameters: session_name (required), project_dir (optional)
  - clean: Clean sessions
    Parameters: project_dir (optional), sessions_dir (optional)
```

#### Progressive Disclosure (~150 tokens total across 3 calls)

**Call 1: Discover** (~50 tokens)
```
Available commands:
- ao-new: Create new session
- ao-resume: Resume existing session
- ao-status: Check session status
- ao-get-result: Get session result
- ao-list-sessions: List all sessions
- ao-list-agents: List available agents
- ao-show-config: Show configuration
- ao-clean: Clean all sessions
```

**Call 2: Detail** (~50 tokens)
```bash
$ ao-new --help

Create a new agent orchestrator session.

Usage: ao-new <session-name> [OPTIONS]

Arguments:
  session-name  Name of the session

Options:
  -p, --prompt TEXT      Session prompt
  --agent TEXT           Agent to use
  --project-dir PATH     Project directory
  --help                 Show this message
```

**Call 3: Execute** (~50 tokens)
```bash
$ ao-new mysession --agent researcher -p "Research topic"
```

**Savings**: 70% reduction in context load!

## Code Reuse Strategy

### Problem: Avoiding Duplication

Each command needs:
- Configuration loading
- Session validation
- Error handling
- Path resolution
- Claude API integration

### Solution: Shared Library

```
lib/
├── config.py           # Configuration precedence & loading
├── session.py          # Session operations & validation
├── agent.py            # Agent loading & validation
├── claude_client.py    # Claude API wrapper
└── utils.py            # Common utilities
```

### Import Pattern

```python
#!/usr/commands/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["anthropic", "typer"]
# ///

import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent / "lib"))

# Import shared modules
from config import load_config
from session import validate_session_name, create_session
from utils import error, success

def main():
    config = load_config()
    # Command-specific logic...
```

### What Goes Where?

**In `lib/` (Shared)**:
- Configuration loading logic
- Session state detection algorithms
- Agent JSON parsing and validation
- Claude SDK integration
- File operations (read/write session files)
- Common validators (session name, paths)
- Error formatting utilities

**In `commands/` (Command-specific)**:
- Argument parsing (via argparse/typer)
- Command-specific validation
- Output formatting for this command
- Command flow orchestration
- Error handling for this command's context

### Example: Session Name Validation

**lib/utils.py** (shared logic):
```python
def validate_session_name(name: str) -> tuple[bool, str]:
    """Validate session name format.

    Returns: (is_valid, error_message)
    """
    if len(name) > 60:
        return False, "Session name too long (max 60 chars)"
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        return False, "Session name must be alphanumeric with - or _"
    return True, ""
```

**commands/ao-new** (uses shared logic):
```python
from utils import validate_session_name, error

session_name = args.session_name
is_valid, err_msg = validate_session_name(session_name)
if not is_valid:
    error(f"Invalid session name: {err_msg}")
    sys.exit(1)
```

## LLM Interaction Patterns

### Pattern 1: Direct Discovery

LLM has been told about `ao-*` commands:

```python
# In system prompt or tools description:
"""
Agent Orchestrator commands are available as ao-* executables.
Run `ls commands/ao-*` to see available commands.
Run `<command> --help` for usage details.
"""
```

Workflow:
1. LLM knows pattern exists
2. Discovers specific commands via `ls`
3. Loads details via `--help`
4. Executes command

### Pattern 2: Skill-Based Discovery

Each command is a Claude Code skill:

```markdown
# .claude/skills/ao-new.md
---
command: ao-new
description: Create a new agent orchestrator session
---

Run `ao-new --help` for usage.
```

Workflow:
1. LLM sees skill in skill list
2. Invokes skill
3. Skill expands to show `--help` output
4. LLM executes with arguments

### Pattern 3: Catalog-Based Discovery

Provide a single catalog tool/command:

```bash
$ ao-help
Available commands:
  ao-new         Create new session
  ao-resume      Resume existing session
  ...

Run <command> --help for details.
```

Workflow:
1. LLM calls `ao-help` once
2. Gets command list
3. Loads details for needed command
4. Executes

## Extensibility

### Adding a New Command

1. **Create script**: `commands/ao-mycommand`
2. **Add uv shebang** (see template)
3. **Import from lib**: `from config import load_config`
4. **Implement logic**
5. **Make executable**: `chmod +x`

**That's it!** No need to:
- Update central registry
- Modify other commands
- Update monolithic help
- Regenerate schemas

### Example: Adding `ao-archive`

```python
#!/usr/commands/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typer"]
# ///

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from config import load_config
from session import archive_session
import typer

def main(session_name: str):
    """Archive a completed session."""
    config = load_config()
    archive_session(session_name, config)
    print(f"Archived: {session_name}")

if __name__ == "__main__":
    typer.run(main)
```

Command immediately available, self-documenting, uses shared infrastructure.

## Comparison Matrix

| Aspect | Monolithic CLI | MCP Server | Progressive CLI |
|--------|---------------|------------|-----------------|
| Upfront context | High | High | Low |
| On-demand detail | No | No | Yes |
| Extensibility | Hard | Medium | Easy |
| Token efficiency | Low | Low | High |
| Discoverability | Medium | High | High |
| Maintenance | Hard | Medium | Easy |
| LLM development | Hard | Medium | Easy |
| Code reuse | Good | Good | Good |

## Best Practices

### 1. Keep Commands Focused

Each command should do **one thing**:
- ✅ `ao-new`: Create session
- ✅ `ao-status`: Check status
- ❌ `ao-manage`: Do everything (avoid!)

### 2. Consistent Help Format

All commands should provide:
```bash
$ command --help
Brief description.

Usage: command <required> [OPTIONS]

Arguments:
  ...

Options:
  ...

Examples:
  command example1
  command example2
```

### 3. Share Aggressively

If code appears in 2+ commands, move to `lib/`:
```python
# Good: Shared in lib/
from config import load_config

# Bad: Copy-pasted in each command
def load_config():
    ...
```

### 4. Fail Fast

Validate early in each command:
```python
def main(session_name: str, ...):
    # Validate immediately
    validate_session_name(session_name)
    validate_paths()

    # Then proceed with logic
    ...
```

### 5. Self-Document

Each command is its own documentation:
```python
def main(session_name: str, prompt: str = None):
    """Create a new agent session.

    Args:
        session_name: Unique identifier for the session
        prompt: Initial prompt (can also read from stdin)
    """
```

## Testing Strategy

### Unit Tests

Test shared modules independently:
```python
# tests/test_config.py
from lib.config import load_config, resolve_precedence

def test_precedence_cli_over_env():
    ...

def test_precedence_env_over_default():
    ...
```

### Integration Tests

Test commands as black boxes:
```bash
# tests/test_ao_new.sh
./commands/ao-new test-session -p "Hello"
assert_session_created "test-session"
```

### LLM Interaction Tests

Simulate LLM workflow:
```python
def test_progressive_discovery():
    # Step 1: Discover
    commands = run("ls commands/ao-*")
    assert "ao-new" in commands

    # Step 2: Detail
    help_text = run("ao-new --help")
    assert "session-name" in help_text

    # Step 3: Execute
    result = run("ao-new test -p 'Hi'")
    assert result.success
```

## Performance Considerations

### Startup Time

Each command should start in <100ms:
- Use `uv` for fast Python execution
- Lazy import heavy dependencies
- Cache configuration where possible

### Shared Module Loading

Modules in `lib/` are loaded per-command:
```python
# Fast: Only load what you need
from config import load_config

# Slower: Load everything
from lib import *
```

### File Operations

Optimize common operations:
- Cache session list
- Stream large session files
- Use efficient JSON parsing

## Future Enhancements

### Potential Additions

1. **Command aliases**: `ao-n` → `ao-new`
2. **Command chaining**: `ao-new | ao-status`
3. **JSON output**: `--json` flag for parsing
4. **Async operations**: Background session execution
5. **Plugin system**: User-defined commands in `~/.ao/plugins/`

### Maintaining Philosophy

Any addition should preserve:
- ✅ Progressive disclosure
- ✅ Token efficiency
- ✅ Simple mental model
- ✅ Easy extensibility

---

**Key Takeaway**: Progressive disclosure trades slight implementation complexity (multiple files) for significant UX improvement (context efficiency). For LLM workflows, this is a winning trade.
