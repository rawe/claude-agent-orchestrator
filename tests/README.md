# Integration Tests

Manual integration tests for the Agent Orchestrator framework.

## Overview

Tests verify the Agent Coordinator and Agent Runner work correctly together. Two profile options:
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
│   └── sse-monitor         # SSE event monitor
├── scripts/
│   ├── reset-db            # Database reset script
│   ├── start-coordinator   # Start Agent Coordinator with .env
│   ├── start-runner        # Start Agent Runner with .env
│   └── start-sse-monitor   # Start SSE monitor with .env
└── README.md              # This file
```

## Test Environment Setup

**All setup commands run from project root** unless otherwise noted.

**Important**: The database can only be reset when services are stopped. The `reset-db` script deletes the SQLite file, and the Agent Coordinator creates tables on startup. If you need a fresh database, you must restart all services.

### 1. Reset Database

Before starting services, reset the database for a clean state:

```bash
./tests/scripts/reset-db
```

### 2. Copy Agent Blueprints (if needed)

For tests that require agent blueprints (test cases 03-07), copy them **before** starting the Agent Coordinator. See [Agent Blueprints](#agent-blueprints) section for details.

### 3. Start Agent Coordinator

In a terminal (or background process). Use the helper script which handles `.env` sourcing and port checks:

```bash
./tests/scripts/start-coordinator
```

Or manually (must run from `servers/agent-coordinator/` directory):

```bash
set -a; source .env; set +a  # Export all .env variables
cd servers/agent-coordinator
uv run python -m main
```

The server runs on `http://localhost:8765`. Verify with:

```bash
curl http://localhost:8765/health
```

### 4. Start Agent Runner

In another terminal (or background process). Use the helper script:

```bash
# With test-executor profile (fast, deterministic)
./tests/scripts/start-runner test-executor

# Or with claude-code profile (real AI)
./tests/scripts/start-runner claude-code
```

Or manually:

```bash
set -a; source .env; set +a
./servers/agent-runner/agent-runner -x test-executor
```

### 5. Start SSE Monitor

In another terminal (or background process). Use the helper script:

```bash
./tests/scripts/start-sse-monitor
```

Or manually:

```bash
set -a; source .env; set +a
./tests/tools/sse-monitor
```

This prints all SSE events as JSON lines to stdout.

## Running Tests

With services running, follow the steps in each test case under `integration/`.

### Slash Commands (for Claude Code)

Commands are located in `.claude/commands/tests/` and provide automated test execution.

| Command | Description |
|---------|-------------|
| `/tests:setup [profile]` | Start core services (Coordinator, Runner, sse-monitor). Optional profile: `test-executor` (default) or `claude-code` |
| `/tests:case <name>` | Run a specific test case. Reads prerequisites, calls setup with correct profile, handles test-specific setup |
| `/tests:run` | Run all tests sequentially with automatic setup and teardown |
| `/tests:teardown` | Stop all services and cleanup |

**Typical usage:**
```bash
# Run a single test case (handles all setup automatically)
/tests:case 7

# Or manual control
/tests:setup claude-code    # Start services with claude-code profile
/tests:teardown             # Stop everything when done
```

### Documentation Scoping

To avoid redundancy and maintain clarity, documentation is organized by scope:

| Scope | Location | Contains |
|-------|----------|----------|
| **README** | `tests/README.md` | Common setup procedures, shared prerequisites (agent blueprints), tool references |
| **Slash Commands** | `.claude/commands/tests/*.md` | Execution flow, which services to start, how to invoke other commands |
| **Test Cases** | `tests/integration/*.md` | Test-specific prerequisites, test steps, expected behavior, verification checklist |

**Principles:**
- **README**: "How to do X" (e.g., how to copy blueprints)
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
- Simple agents: Create via `POST /agents` API (see `docs/components/agent-coordinator/API.md` → Agents API)
- Complex agents (with MCP servers): **Copy** from `config/agents/` to `servers/agent-coordinator/.agent-orchestrator/agents/`

**Important**: Agent blueprints must be copied **before** starting the Agent Coordinator, as blueprints are only discovered on startup.

**Copying agent blueprints (from project root):**

Complex agents that require MCP servers (like `agent-orchestrator`) must be copied from the central config directory to the coordinator's local agents folder. Do NOT create these files manually.

```bash
# From project root - create the agents directory if it doesn't exist
mkdir -p servers/agent-coordinator/.agent-orchestrator/agents

# From project root - copy a specific agent blueprint (e.g., agent-orchestrator)
cp -r config/agents/agent-orchestrator servers/agent-coordinator/.agent-orchestrator/agents/
```

The Agent Coordinator discovers blueprints in `.agent-orchestrator/agents/` (relative to its working directory) on startup. Verify with:

```bash
curl -s http://localhost:8765/agents | grep agent-orchestrator
```

## Test Cases

### Category 1: Basic Session Lifecycle
- `01-basic-session-start.md` - Start a new session, verify events
- `02-session-resume.md` - Resume an existing session
- `03-session-with-agent.md` - Start a session with an agent blueprint
- `04-child-agent-sync.md` - Child agent in sync mode

### Category 2: Callback Feature
- `05-child-agent-callback.md` - Child agent with callback (parent-child relationship)
- `06-concurrent-callbacks.md` - Multiple child agents with concurrent callbacks (race condition detection)
- `07-callback-on-child-failure.md` - Parent receives failure callback when child agent fails

### Category 3: Runner Management
- `08-runner-identity.md` - Deterministic runner ID and reconnection recognition (ADR-012)

### Category 4: Demand Matching (ADR-011)
- `09-demand-matching-success.md` - Runner with matching tags claims run with demands
- `10-demand-matching-timeout.md` - Run times out when no matching runner available

## Tools Reference

### sse-monitor

Connects to `http://localhost:8765/sse/sessions` and prints events as raw JSON lines.

```bash
./tests/tools/sse-monitor
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
- **sse-monitor**: `Ctrl+C` in terminal

## Authentication

Authentication is **disabled** for all integration tests. The helper scripts explicitly set `AUTH_ENABLED=false` when starting the Agent Coordinator.

If you need to test authentication behavior, do so in a separate environment with `AUTH_ENABLED=true` and Auth0 configured.

## Troubleshooting

### "Connection refused" errors
- Ensure Agent Coordinator is running on port 8765
- Check no other process is using the port: `lsof -i :8765`

### Runs not executing
- Verify Agent Runner is registered (check runner logs)
- Ensure using `-x test-executor` profile flag

### No SSE events
- Verify sse-monitor connected successfully
- Check Agent Coordinator logs for errors
