# Architecture

## Overview

The Agent Orchestrator MCP server uses UV's inline dependency feature (PEP 723) for zero-setup deployment. Developers only need UV installed to run the MCP server.

## Structure

```
agent-orchestrator-mcp-python/
├── agent-orchestrator-mcp.py    # Main entry point (concise, ~40 lines)
├── libs/                        # Modular library files
│   ├── constants.py            # Constants and configuration values
│   ├── logger.py               # File-based logging
│   ├── schemas.py              # Pydantic validation schemas
│   ├── server.py               # Main MCP server logic
│   ├── types_models.py         # Type definitions
│   └── utils.py                # Utility functions
└── logs/                        # Debug logs (when MCP_SERVER_DEBUG=true)
```

## Invocation Pattern

The server uses a simplified invocation pattern with UV:

```json
{
  "command": "uv",
  "args": [
    "run",
    "/path/to/agent-orchestrator-mcp-python/agent-orchestrator-mcp.py"
  ]
}
```

## Inline Dependencies (PEP 723)

The main script declares dependencies in its header:

```python
#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "mcp>=1.7.0",
#   "pydantic>=2.0.0",
# ]
# ///
```

UV automatically:
- Creates a temporary virtual environment
- Installs dependencies
- Runs the script

## Modular Design

The codebase maintains a modular structure with clear separation of concerns:

- **constants.py** - Environment variables, limits, patterns
- **types_models.py** - Pydantic models for data structures
- **logger.py** - Debug logging to file
- **schemas.py** - Input validation schemas
- **utils.py** - Execution, parsing, formatting utilities
- **server.py** - MCP server implementation and handlers

## No Package Installation Required

The standalone approach eliminates the need for:
- `pip install` commands
- Manual virtual environment setup
- `--directory` parameter in UV invocation
- Package installation step

## Usage

### Standalone Execution

```bash
# Direct execution (UV manages everything)
uv run /path/to/agent-orchestrator-mcp.py
```

For concrete configuration see: [INTEGRATION_SCENARIOS.md](./INTEGRATION_SCENARIOS.md)

## Benefits

1. **Zero Setup** - Only UV required, no package installation
2. **Dependency Isolation** - UV manages dependencies automatically
3. **Single Command** - Simplified invocation pattern
4. **Portable** - Copy the script anywhere, it just works
5. **Maintainable** - Modular code structure in libs/
6. **Clear Entry Point** - Concise main script shows what's happening

## Environment Variables

See [ENV_VARS.md](./ENV_VARS.md) for complete documentation.

Required variables:
- **AGENT_ORCHESTRATOR_COMMAND_PATH** - Path to CLI commands directory
- **AGENT_ORCHESTRATOR_PROJECT_DIR** - Project directory (Claude Desktop only)

Optional variables:
- **AGENT_ORCHESTRATOR_SESSIONS_DIR** - Custom session storage location
- **AGENT_ORCHESTRATOR_AGENTS_DIR** - Custom agent definitions location
- **MCP_SERVER_DEBUG** - Enable debug logging to logs/mcp-server.log

## Technical Details

### Import Resolution

The main script adds `libs/` to `sys.path`:
```python
sys.path.insert(0, str(SCRIPT_DIR / "libs"))
```

All libs modules use absolute imports:
```python
from constants import ENV_COMMAND_PATH
from logger import logger
from types_models import ResponseFormat
```

### Dependency Management

UV handles dependencies via inline metadata:
- First run: Installs dependencies (may take a few seconds)
- Subsequent runs: Reuses cached environment
- Fast startup after initial installation
- Dependencies are isolated per script

### Entry Point

The `agent-orchestrator-mcp.py` script is kept concise (~40 lines) as a thin entry point that:
1. Sets up the Python path for libs/ imports
2. Imports and initializes the server from libs/server.py
3. Runs the MCP server

This design keeps the architecture clear while maintaining modularity.

## Testing

```bash
# Test server starts
AGENT_ORCHESTRATOR_COMMAND_PATH=/path/to/commands uv run agent-orchestrator-mcp.py

# Server should output:
# Agent Orchestrator MCP Server
# Commands path: /path/to/commands
# Agent Orchestrator MCP server running via stdio
```

## Related Documentation

- **Integration Scenarios**: [INTEGRATION_SCENARIOS.md](./INTEGRATION_SCENARIOS.md)
- **Tools API**: [TOOLS_REFERENCE.md](./TOOLS_REFERENCE.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
