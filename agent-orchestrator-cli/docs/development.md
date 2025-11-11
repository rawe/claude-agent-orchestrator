# Development Guide

## Getting Started

### Prerequisites

- Python 3.11+
- `uv` installed: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Claude API key in environment: `export ANTHROPIC_API_KEY=your-key`

### Project Structure

```
agent-orchestrator-cli/
├── bin/              # Executable command scripts
│   ├── ao-new
│   ├── ao-resume
│   ├── ao-status
│   ├── ao-get-result
│   ├── ao-list
│   ├── ao-list-agents
│   ├── ao-show-config
│   └── ao-clean
├── lib/              # Shared Python modules
│   ├── config.py       # Configuration management
│   ├── session.py      # Session operations
│   ├── agent.py        # Agent loading
│   ├── claude_client.py # Claude API wrapper
│   └── utils.py        # Common utilities
└── docs/             # Documentation
```

## Implementation Order

Suggested order for implementing functionality:

### Phase 1: Core Infrastructure
1. **lib/config.py** - Configuration loading
2. **lib/utils.py** - Basic utilities (error, read/write)
3. **lib/session.py** - Session name validation

### Phase 2: Session Management
4. **ao-status** - Simplest command (read-only)
5. **ao-list-sessions** - Session discovery
6. **lib/session.py** - State detection algorithm

### Phase 3: Agent System
7. **lib/agent.py** - Agent loading
8. **ao-list-agents** - Agent discovery
9. **ao-show-config** - Display configuration

### Phase 4: Claude Integration
10. **lib/claude_client.py** - Claude SDK wrapper
11. **ao-new** - Session creation
12. **ao-resume** - Session continuation
13. **ao-get-result** - Result extraction

### Phase 5: Polish
14. **ao-clean** - Cleanup operations
15. Error handling and user feedback
16. Testing and validation

## Development Workflow

### Testing a Command

```bash
# Test directly
./bin/ao-new --help

# Test with uv explicitly
uv run --script bin/ao-new --help

# Add to PATH for easier testing
export PATH="$PWD/bin:$PATH"
ao-new --help
```

### Adding a New Command

1. Copy template:
```bash
cp bin/ao-new bin/ao-mycommand
```

2. Update the script:
```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["anthropic", "typer"]
# ///

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

# Your implementation here
```

3. Make executable:
```bash
chmod +x bin/ao-mycommand
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

# Test commands
ao-new testsession -p "Hello world"
ao-status testsession
ao-get-result testsession
ao-list
ao-clean
```

### Unit Testing (TODO)

```python
# tests/test_config.py
from lib.config import load_config

def test_config_precedence():
    # Test CLI > ENV > Default
    pass
```

### Integration Testing (TODO)

```bash
# tests/integration/test_session_lifecycle.sh
#!/bin/bash
# Test full session lifecycle
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

Match the bash script exactly:

**Session Metadata** (`.metadata.json`):
```json
{
  "session_name": "mysession",
  "agent": "researcher",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z",
  "project_dir": "/path/to/project",
  "sessions_dir": "/path/to/sessions",
  "agents_dir": "/path/to/agents"
}
```

**Session File** (`session.txt`):
- Stream of Claude API responses
- First line may contain session ID
- Last assistant message is the result

### State Detection Algorithm

Ported from bash script:

1. If session dir doesn't exist: `not_existent`
2. If session file doesn't exist: `not_existent`
3. Check last line for completion marker
4. If no marker: `running`
5. If has marker: `finished`

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

### Enable Verbose Output

```bash
# Add to any command for debugging
python -u bin/ao-new --help
```

### Check uv Dependencies

```bash
# See what uv would install
uv pip compile bin/ao-new
```

### Test Imports

```bash
# Check if shared modules load
python -c "import sys; sys.path.insert(0, 'lib'); from config import Config; print('OK')"
```

## Migration from Bash

### Behavior Compatibility

All commands should behave identically to bash script:
- Same input/output formats
- Same error messages
- Same file structures
- Same state detection

### Testing Compatibility

```bash
# Test both versions produce same output
bash ../agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh status test
./bin/ao-status test

# Compare results
```

## Tips for LLM-Assisted Development

### Implementing a Module

Prompt template:
```
Implement lib/config.py based on:
1. The function stubs already present
2. The bash script at: ../agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh
3. The precedence rules in docs/architecture.md

Preserve:
- Function signatures
- Error handling patterns
- Documentation style
```

### Implementing a Command

Prompt template:
```
Implement bin/ao-new based on:
1. The TODO comments in the file
2. The bash script 'new' command implementation
3. Using shared modules from lib/

Follow the patterns in other commands.
```

## Next Steps

1. Pick a module from Phase 1
2. Implement based on bash script behavior
3. Test manually
4. Move to next module
5. Iterate until all phases complete

---

**Remember**: Each command is independent. You can implement them in any order, as long as shared dependencies in `lib/` are ready first.
