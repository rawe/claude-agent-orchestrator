# Integration Tests

Manual integration tests for the Agent Orchestrator framework.

## Overview

Tests verify the Agent Runtime and Agent Launcher work correctly together. Two executor options:
- `test-executor` - Simple echo executor for fast, deterministic tests
- `claude-code` - Real Claude AI executor for end-to-end validation

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) installed
- No other instance of Agent Runtime running on port 8765

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

**Important**: The database can only be reset when services are stopped. The `reset-db` script deletes the SQLite file, and the Agent Runtime creates tables on startup. If you need a fresh database, you must restart all services.

### 1. Reset Database

Before starting services, reset the database for a clean state:

```bash
./tests/scripts/reset-db
```

### 2. Start Agent Runtime

In a terminal (or background process):

```bash
cd servers/agent-runtime
uv run python -m main
```

The server runs on `http://localhost:8765`. Verify with:

```bash
curl http://localhost:8765/health
```

### 3. Start Agent Launcher

In another terminal (or background process):

```bash
# With test-executor (fast, deterministic)
./servers/agent-launcher/agent-launcher -x test-executor

# Or with claude-code (real AI)
./servers/agent-launcher/agent-launcher -x claude-code
```

### 4. Start WebSocket Monitor

In another terminal (or background process):

```bash
./tests/tools/ws-monitor
```

This prints all WebSocket events as JSON lines to stdout.

## Running Tests

With services running, follow the steps in each test case under `integration/`.

### Slash Commands (for Claude Code)

- `/tests/setup` - Start all services
- `/tests/case <name>` - Run a specific test case
- `/tests/run` - Run all tests with setup/teardown
- `/tests/teardown` - Stop all services

## Agent Blueprints

Agent blueprints define specialized agents with system prompts and MCP servers.

**Storage locations:**
- Dockerized runtime: `config/agents/`
- Local runtime: `.agent-orchestrator/agents/`

**For testing:**
- Simple agents: Create via `POST /agents` API (see `docs/agent-runtime/API.md` → Agents API)
- Complex agents (with MCP servers): Copy the needed agent directory from `config/agents/<agent-name>/` to `.agent-orchestrator/agents/`

## Test Categories

### Category 1: Basic Session Lifecycle
- `01-basic-session-start.md` - Start a new session, verify events
- `02-session-resume.md` - Resume an existing session
- `03-session-with-agent.md` - Start a session with an agent blueprint
- `04-child-agent-sync.md` - Child agent in sync mode (requires MCP server)
- `05-child-agent-callback.md` - Child agent with callback (parent-child relationship)

### Category 2: Event Ordering & Content
- Verify timestamps are sequential
- Verify session_id/session_name consistency
- Verify message content matches expected format

### Category 3: Callback Feature (Future)
- Parent-child session coordination
- Callback notifications on child completion

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

- **Agent Runtime**: `Ctrl+C` in terminal or kill process
- **Agent Launcher**: `Ctrl+C` in terminal or kill process
- **ws-monitor**: `Ctrl+C` in terminal

## Troubleshooting

### "Connection refused" errors
- Ensure Agent Runtime is running on port 8765
- Check no other process is using the port: `lsof -i :8765`

### Jobs not executing
- Verify Agent Launcher is registered (check launcher logs)
- Ensure using `-x test-executor` flag

### No WebSocket events
- Verify ws-monitor connected successfully
- Check Agent Runtime logs for errors
