# Design: Optional External MCP Server for Agent Runner

## Status

**In Progress** - Implementation phase

## Summary

Add a CLI parameter `--external-mcp-url` to the Agent Runner that allows disabling the embedded MCP server and using an external one instead. This enables multiple Agent Runners on the same host to share a single MCP server instance.

## Problem Statement

### Current State

Each Agent Runner starts an embedded Agent Orchestrator MCP server (see [mcp-runner-integration.md](../architecture/mcp-runner-integration.md)):

```
Host Machine
├── Agent Runner A (port 8001) ─── Embedded MCP Server (port 9001)
├── Agent Runner B (port 8002) ─── Embedded MCP Server (port 9002)
├── Agent Runner C (port 8003) ─── Embedded MCP Server (port 9003)
└── ...
```

### Issues

1. **Resource Waste**: Running N Agent Runners means N MCP server instances, each consuming memory and CPU
2. **Port Management**: Multiple dynamic ports for MCP servers increase complexity
3. **Redundancy**: All MCP servers perform identical functions - they're stateless facades to the Agent Coordinator

### Proposed Solution

Allow Agent Runners to share a single MCP server:

```
Host Machine
├── Agent Runner A (primary)   ─── Embedded MCP Server (port 9001)
├── Agent Runner B (secondary) ───┐
├── Agent Runner C (secondary) ───┼── Use external MCP: http://127.0.0.1:9001/mcp
└── Agent Runner D (secondary) ───┘
```

## Design

### New CLI Parameter

Add `--external-mcp-url` (short: `-e`) to accept a complete MCP server URL:

```bash
# Primary runner: starts embedded MCP server on fixed port
./agent-runner --mcp-port 9001

# Secondary runners: use external MCP server
./agent-runner --external-mcp-url http://127.0.0.1:9001/mcp
./agent-runner --external-mcp-url http://127.0.0.1:9001/mcp
```

### Parameter Semantics

| Scenario | `--mcp-port` | `--external-mcp-url` | Behavior |
|----------|--------------|----------------------|----------|
| Default | (none) | (none) | Start embedded MCP on random port |
| Fixed port | 9001 | (none) | Start embedded MCP on port 9001 |
| External MCP | (none) | `http://...` | Do NOT start embedded MCP, use external URL |
| Invalid | 9001 | `http://...` | Error: mutually exclusive |

### URL Format

The `--external-mcp-url` parameter accepts a complete URL including:
- Protocol: `http://` or `https://`
- Host: `127.0.0.1`, `localhost`, or any hostname
- Port: Required (e.g., `:9001`)
- Path: Required (typically `/mcp` for FastMCP servers)

Examples:
```
http://127.0.0.1:9001/mcp        # Local MCP server
http://localhost:9001/mcp        # Alternative local
http://mcp-server.local:9001/mcp # Network MCP server
```

### Configuration Flow

```
┌─────────────────────────────────────────────────────────┐
│                     CLI Parameters                       │
│  --external-mcp-url http://127.0.0.1:9001/mcp           │
└─────────────────────────────────┬───────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────┐
│                     RunnerConfig                         │
│  external_mcp_url: str | None                           │
│  mcp_port: int | None  (mutually exclusive)             │
└─────────────────────────────────┬───────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────┐
│                       Runner                             │
│                                                          │
│  if external_mcp_url:                                    │
│      # Skip starting embedded MCP server                 │
│      # Use external_mcp_url for placeholder resolution   │
│      executor.mcp_server_url = external_mcp_url         │
│  else:                                                   │
│      # Start embedded MCP server (existing behavior)     │
│      mcp_server.start()                                  │
│      executor.mcp_server_url = mcp_server.url           │
└─────────────────────────────────┬───────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────┐
│               Blueprint Placeholder Resolution           │
│                                                          │
│  ${AGENT_ORCHESTRATOR_MCP_URL} → executor.mcp_server_url│
│                                                          │
│  Result: http://127.0.0.1:9001/mcp (external or local)  │
└─────────────────────────────────────────────────────────┘
```

### Implementation Changes

#### 1. RunnerConfig (`lib/config.py`)

Add new field:

```python
@dataclass
class RunnerConfig:
    # ... existing fields ...
    mcp_port: int | None  # Optional fixed port for embedded MCP server
    external_mcp_url: str | None  # Optional external MCP server URL (disables embedded)
```

#### 2. CLI Parameter (`agent-runner`)

Add mutually exclusive parameter:

```python
external_mcp_url: str = typer.Option(
    None,
    "--external-mcp-url",
    "-e",
    help="External MCP server URL (disables embedded MCP server). "
         "Use when sharing MCP server across multiple runners. "
         "Example: http://127.0.0.1:9001/mcp",
)

# Validation
if external_mcp_url and mcp_port:
    raise typer.BadParameter(
        "--external-mcp-url and --mcp-port are mutually exclusive"
    )
```

#### 3. Runner Class (`agent-runner`)

Conditional MCP server startup:

```python
class Runner:
    def __init__(self, config: RunnerConfig):
        # ...

        # Create embedded MCP server only if not using external
        if config.external_mcp_url:
            self.mcp_server = None
            self._external_mcp_url = config.external_mcp_url
        else:
            self.mcp_server = MCPServer(
                coordinator_url=config.agent_coordinator_url,
                auth0_client=self.auth0_client,
                port=config.mcp_port,
            )
            self._external_mcp_url = None

    def start(self) -> None:
        # ... gateway start ...

        # Start embedded MCP server only if not using external
        if self.mcp_server:
            self.mcp_server.start()
            logger.info(f"Embedded MCP server on port {self.mcp_server.port}")
            self.executor.mcp_server_url = self.mcp_server.url
        else:
            logger.info(f"Using external MCP server: {self._external_mcp_url}")
            self.executor.mcp_server_url = self._external_mcp_url

        # ... rest of start ...

    def stop(self) -> None:
        # ... existing stops ...

        # Stop embedded MCP server only if it exists
        if self.mcp_server:
            self.mcp_server.stop()
```

## Usage Patterns

### Pattern 1: Single Runner (Default)

Standard single-runner deployment, embedded MCP server:

```bash
./agent-runner --profile coding
# Starts embedded MCP on random port
```

### Pattern 2: Single Runner with Fixed Port

For external clients that need to connect to the MCP server:

```bash
./agent-runner --profile coding --mcp-port 9001
# Starts embedded MCP on port 9001
# External clients can connect to http://127.0.0.1:9001/mcp
```

### Pattern 3: Multiple Runners Sharing MCP

First runner hosts the MCP server, others connect to it:

```bash
# Terminal 1: Primary runner with MCP server
./agent-runner --profile coding --mcp-port 9001 --project-dir /project/a

# Terminal 2: Secondary runner using external MCP
./agent-runner --profile testing --external-mcp-url http://127.0.0.1:9001/mcp --project-dir /project/b

# Terminal 3: Another secondary runner
./agent-runner --profile docs --external-mcp-url http://127.0.0.1:9001/mcp --project-dir /project/c
```

### Pattern 4: Centralized MCP Server

Dedicated MCP server process (future enhancement):

```bash
# Terminal 1: Standalone MCP server (if implemented)
./mcp-server --port 9001

# Terminal 2-4: All runners use external
./agent-runner --external-mcp-url http://127.0.0.1:9001/mcp --project-dir /project/a
./agent-runner --external-mcp-url http://127.0.0.1:9001/mcp --project-dir /project/b
./agent-runner --external-mcp-url http://127.0.0.1:9001/mcp --project-dir /project/c
```

## Considerations

### Auth0 Token Sharing

When using external MCP server, tokens are NOT shared between runners. The primary runner's MCP server uses its own Auth0 client. This is acceptable because:
- MCP server caches its own tokens
- Token refresh is handled independently
- No additional security concerns

### Failure Modes

| Scenario | Behavior |
|----------|----------|
| External MCP unreachable | Executor fails to connect, run fails |
| Primary runner stops | Secondary runners lose MCP access |
| Invalid URL format | CLI validation error |

### Health Checking

The runner does NOT validate the external MCP URL at startup. If the URL is invalid or unreachable, errors occur when executors attempt to use the MCP tools.

Future enhancement: Add optional startup health check with `--validate-external-mcp` flag.

## Alternatives Considered

### 1. Environment Variable Only

Could use `AGENT_ORCHESTRATOR_MCP_URL` environment variable instead of CLI parameter.

**Rejected**: CLI parameters are more explicit and follow the pattern of other runner options. Environment variables are used for defaults, not overrides.

### 2. Auto-Discovery

Runners could discover existing MCP servers via mDNS or similar.

**Rejected**: Over-engineering for the use case. Explicit URL is simpler and more predictable.

### 3. Coordinator-Hosted MCP

Agent Coordinator could host the MCP server centrally.

**Rejected**: This would centralize MCP traffic, creating a bottleneck. The current distributed model (MCP per runner or shared among local runners) is more scalable.

## Related Documents

- [MCP Runner Integration](../architecture/mcp-runner-integration.md) - Embedded MCP server architecture
- [ADR-002: Agent Runner Architecture](../adr/ADR-002-agent-runner-architecture.md) - Runner design decisions
