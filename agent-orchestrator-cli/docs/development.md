# Development Guide

## Getting Started

### Prerequisites

- Python 3.10+
- `uv` installed: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Claude API key: `export ANTHROPIC_API_KEY=your-key`

### Project Structure

```
agent-orchestrator-cli/
├── commands/                   # Executable command scripts
│   ├── ao-new                  # Create new session
│   ├── ao-resume               # Resume existing session
│   ├── ao-status               # Check session status
│   ├── ao-get-result           # Get session result
│   ├── ao-list-sessions        # List all sessions
│   ├── ao-list-agents          # List available agents
│   ├── ao-show-config          # Show configuration
│   ├── ao-clean                # Clean all sessions
│   └── lib/                    # Shared Python modules (co-located)
│       ├── __init__.py
│       ├── config.py           # Configuration management
│       ├── session.py          # Session operations
│       ├── agent.py            # Agent loading
│       ├── claude_client.py    # Claude SDK wrapper
│       └── utils.py            # Common utilities
└── docs/                       # Documentation
```

## Development Workflow

### Testing a Command

All commands must be run with `uv run`:

```bash
# Test help output
uv run commands/ao-new --help

# Test command execution
uv run commands/ao-status test-session

# Test with stdin
echo "Hello" | uv run commands/ao-new test-session
```

### Adding a New Command

1. Copy an existing command as template:
```bash
cp commands/ao-status commands/ao-mycommand
```

2. Update the script header and logic:
```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "claude-agent-sdk",  # If using Claude SDK
# ]
# ///

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from config import load_config
# Import other shared modules as needed

# Your implementation here
```

3. Make executable:
```bash
chmod +x commands/ao-mycommand
```

4. Test with `uv run`:
```bash
uv run commands/ao-mycommand --help
```

### Adding Shared Functionality

If functionality is used by 2+ commands:

1. Add to appropriate module in `lib/`
2. Import in commands that need it
3. Document the function
4. Add TODO markers for implementation

## Testing Strategy

### Manual Testing

```bash
# Create test environment
mkdir -p /tmp/test-ao
cd /tmp/test-ao

# Test commands (all require 'uv run')
uv run /path/to/commands/ao-new testsession -p "Hello world"
uv run /path/to/commands/ao-status testsession
uv run /path/to/commands/ao-get-result testsession
uv run /path/to/commands/ao-list-sessions
uv run /path/to/commands/ao-clean
```

### Unit Testing (TODO)

```python
# tests/test_config.py
from lib.config import load_config

def test_config_precedence():
    # Test CLI > ENV > Default
    pass
```

### Integration Testing

```bash
# tests/integration/test_session_lifecycle.sh
#!/bin/bash
# Test full session lifecycle
uv run commands/ao-new test-session -p "Hello"
uv run commands/ao-status test-session
uv run commands/ao-resume test-session -p "Continue"
uv run commands/ao-get-result test-session
uv run commands/ao-clean
```

## Common Patterns

### Error Handling

```python
from utils import error

try:
    # operation
except Exception as e:
    error(f"Failed to do thing: {e}")
```

### Configuration Loading

```python
from config import load_config

config = load_config(
    project_dir=project_dir,
    sessions_dir=sessions_dir,
    agents_dir=agents_dir,
)
```

### Session Operations

```python
from session import (
    validate_session_name,
    get_session_state,
    load_session_metadata,
)

# Validate
is_valid, err = validate_session_name(name)
if not is_valid:
    error(err)

# Check state
state = get_session_state(name, config.sessions_dir)
```

## Implementation Notes

### File Formats

**Session Metadata** (`.meta.json`):
```json
{
  "session_name": "mysession",
  "session_id": "session_abc123",
  "agent": "researcher",
  "created_at": "2024-01-01T12:00:00Z",
  "last_resumed_at": "2024-01-01T12:00:00Z",
  "project_dir": "/path/to/project",
  "agents_dir": "/path/to/agents",
  "schema_version": "1.0"
}
```

**Session Messages** (`.jsonl`):
- JSONL format with one message per line
- Contains SDK-native dataclass serialization
- User messages and agent responses
- Last message contains the result

### State Detection Algorithm

1. Check if `.meta.json` exists → if not: `not_existent`
2. Check if `.jsonl` exists → if not: `running`
3. Check if `.jsonl` size > 0 → if empty: `running`
4. Read last line of `.jsonl` and check for `type: "result"` → if found: `finished`, else: `running`

### Configuration Precedence

```
CLI flags (highest)
  ↓
Environment variables
  ↓
Defaults (PWD) (lowest)
```

### Agent Loading

Structure:
```
.agent-orchestrator/agents/
  agent-name/
    agent.json              # Required: {"name": "...", "description": "..."}
    agent.system-prompt.md  # Optional: system prompt content
    agent.mcp.json         # Optional: MCP configuration
```

## Debugging

### Check Command Help

```bash
# Verify command loads correctly
uv run commands/ao-new --help
```

### Test Shared Module Imports

```bash
# Check if shared modules load
python -c "import sys; sys.path.insert(0, 'commands/lib'); from config import Config; print('OK')"
```

### Enable Logging

```bash
# Enable session logging
export AGENT_ORCHESTRATOR_ENABLE_LOGGING=true
uv run commands/ao-new test -p "Hello"

# Check log file
cat .agent-orchestrator/agent-sessions/test.log
```

## Tips for LLM-Assisted Development

### Implementing a Module

Prompt template:
```
Implement lib/config.py based on:
1. The function stubs already present
2. The requirements in ARCHITECTURE_PLAN.md
3. The precedence rules in docs/architecture.md

Preserve:
- Function signatures
- Error handling patterns
- Documentation style
- Type hints
```

### Implementing a Command

Prompt template:
```
Implement commands/ao-new based on:
1. The requirements in IMPLEMENTATION_CHECKLIST.md
2. Using shared modules from lib/
3. Following patterns in existing commands

Ensure:
- Proper error handling
- Type hints throughout
- Clear user-facing messages
```

## Reference Documentation

For implementation details, see:
- `ARCHITECTURE_PLAN.md` - Detailed implementation guidance
- `IMPLEMENTATION_CHECKLIST.md` - Step-by-step implementation plan
- `PROJECT_CONTEXT.md` - Project goals and architecture decisions
- `CLAUDE_SDK_INVESTIGATION.md` - SDK usage patterns

---

**Remember**: Each command is independent and uses shared modules from `lib/` for common functionality.
