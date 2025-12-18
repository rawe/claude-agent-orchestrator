# Integration Tests

Manual integration tests for the Agent Orchestrator framework.

## Overview

Tests verify the Agent Coordinator and Agent Runner work correctly together. Two executor options:
- `test-executor` - Simple echo executor for fast, deterministic tests
- `claude-code` - Real Claude AI executor for end-to-end validation

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) installed
- No other instance of Agent Coordinator running on port 8765

## Directory Structure

```
tests/
├── integration/           # Test scenario documentation
│   ├── 01-basic-session-start.md
│   └── 02-session-resume.md
│   └── ... (more test cases)
├── tools/
│   └── ws-monitor         # WebSocket event monitor
├── scripts/
│   └── reset-db           # Database reset script
└── README.md              # This file
```

## Test Environment Setup

**Important**: The database can only be reset when services are stopped. The `reset-db` script deletes the SQLite file, and the Agent Coordinator creates tables on startup. If you need a fresh database, you must restart all services.

### 1. Reset Database

Before starting services, reset the database for a clean state:

```bash
./tests/scripts/reset-db
```

### 2. Copy Agent Blueprints (if needed)

For tests that require agent blueprints (test cases 03-07), copy them **before** starting the Agent Coordinator. See [Agent Blueprints](#agent-blueprints) section for details.

### 3. Start Agent Coordinator

In a terminal (or background process):

```bash
cd servers/agent-coordinator
uv run python -m main
```

The server runs on `http://localhost:8765`. Verify with:

```bash
curl http://localhost:8765/health
```

### 4. Start Agent Runner

In another terminal (or background process):

```bash
# With test-executor (fast, deterministic)
./servers/agent-runner/agent-runner -x test-executor

# Or with claude-code (real AI)
./servers/agent-runner/agent-runner -x claude-code
```

### 5. Start WebSocket Monitor

In another terminal (or background process):

```bash
./tests/tools/ws-monitor
```

This prints all WebSocket events as JSON lines to stdout.

## Running Tests

With services running, follow the steps in each test case under `integration/`.

### Slash Commands (for Claude Code)

Commands are located in `.claude/commands/tests/` and provide automated test execution.

| Command | Description |
|---------|-------------|
| `/tests:setup [executor]` | Start core services (Coordinator, Runner, ws-monitor). Optional executor: `test-executor` (default) or `claude-code` |
| `/tests:case <name>` | Run a specific test case. Reads prerequisites, calls setup with correct executor, handles test-specific setup |
| `/tests:run` | Run all tests sequentially with automatic setup and teardown |
| `/tests:teardown` | Stop all services and cleanup |

**Typical usage:**
```bash
# Run a single test case (handles all setup automatically)
/tests:case 7

# Or manual control
/tests:setup claude-code    # Start services with claude-code executor
/tests:teardown             # Stop everything when done
```

### Documentation Scoping

To avoid redundancy and maintain clarity, documentation is organized by scope:

| Scope | Location | Contains |
|-------|----------|----------|
| **README** | `tests/README.md` | Common setup procedures, shared prerequisites (agent blueprints, MCP server), tool references |
| **Slash Commands** | `.claude/commands/tests/*.md` | Execution flow, which services to start, how to invoke other commands |
| **Test Cases** | `tests/integration/*.md` | Test-specific prerequisites, test steps, expected behavior, verification checklist |

**Principles:**
- **README**: "How to do X" (e.g., how to copy blueprints, how to start MCP server)
- **Commands**: "What to do and in which order" (orchestration logic)
- **Test Cases**: "What this test needs and verifies" (references README for how-to)

Test cases reference the README for common procedures rather than duplicating instructions. For example:
- Test case says: `agent-orchestrator` blueprint copied (see `tests/README.md` → "Agent Blueprints")
- README explains the copy command and verification

## Agent Blueprints

Agent blueprints define specialized agents with system prompts and MCP servers.

**Storage locations:**
- Dockerized coordinator: `config/agents/`
- Local coordinator: `servers/agent-coordinator/.agent-orchestrator/agents/` (relative to Agent Coordinator's working directory)

**For testing:**
- Simple agents: Create via `POST /agents` API (see `docs/agent-coordinator/API.md` → Agents API)
- Complex agents (with MCP servers): **Copy** from `config/agents/` to `servers/agent-coordinator/.agent-orchestrator/agents/`

**Important**: Agent blueprints must be copied **before** starting the Agent Coordinator, as blueprints are only discovered on startup.

**Copying agent blueprints:**

Complex agents that require MCP servers (like `agent-orchestrator`) must be copied from the central config directory to the coordinator's local agents folder. Do NOT create these files manually.

```bash
# Create the agents directory if it doesn't exist
mkdir -p servers/agent-coordinator/.agent-orchestrator/agents

# Copy a specific agent blueprint (e.g., agent-orchestrator)
cp -r config/agents/agent-orchestrator servers/agent-coordinator/.agent-orchestrator/agents/
```

The Agent Coordinator discovers blueprints in `.agent-orchestrator/agents/` (relative to its working directory) on startup. Verify with:

```bash
curl -s http://localhost:8765/agents | grep agent-orchestrator
```

## Agent Orchestrator MCP Server

Test cases 04-07 require the Agent Orchestrator MCP server for spawning child agents.

**Starting the MCP server:**

```bash
uv run --script mcps/agent-orchestrator/agent-orchestrator-mcp.py --http-mode --port 9500
```

**Verify it's running:**

```bash
curl -s http://localhost:9500/mcp
```

The MCP server must be started **before** running test cases that use the `agent-orchestrator` blueprint.

## Test Case

### Category 1: Basic Session Lifecycle
- `01-basic-session-start.md` - Start a new session, verify events
- `02-session-resume.md` - Resume an existing session
- `03-session-with-agent.md` - Start a session with an agent blueprint
- `04-child-agent-sync.md` - Child agent in sync mode (requires MCP server)

### Category 2: Callback Feature
- `05-child-agent-callback.md` - Child agent with callback (parent-child relationship)
- `06-concurrent-callbacks.md` - Multiple child agents with concurrent callbacks (race condition detection)
- `07-callback-on-child-failure.md` - Parent receives failure callback when child agent fails

## Tools Reference

### ws-monitor

Connects to `ws://localhost:8765/ws` and prints events as raw JSON lines.

```bash
./tests/tools/ws-monitor
```

Outputs raw JSON lines - one event per line.

### reset-db

Removes the SQLite database and test-executor session data:

```bash
./tests/scripts/reset-db
```

## Stopping Services

- **Agent Coordinator**: `Ctrl+C` in terminal or kill process
- **Agent Runner**: `Ctrl+C` in terminal or kill process
- **ws-monitor**: `Ctrl+C` in terminal

## Troubleshooting

### "Connection refused" errors
- Ensure Agent Coordinator is running on port 8765
- Check no other process is using the port: `lsof -i :8765`

### Runs not executing
- Verify Agent Runner is registered (check runner logs)
- Ensure using `-x test-executor` flag

### No WebSocket events
- Verify ws-monitor connected successfully
- Check Agent Coordinator logs for errors
