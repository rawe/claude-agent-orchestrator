# Placeholder Reference

Placeholders in agent/capability configurations are resolved before execution. This document provides a quick reference for the placeholder system.

## Placeholder Sources

| Source | Syntax | Resolved At | Description |
|--------|--------|-------------|-------------|
| `params` | `${params.X}` | Coordinator | Run parameters (visible to LLM) |
| `scope` | `${scope.X}` | Coordinator | Run scope (LLM-invisible, inherited by child runs) |
| `env` | `${env.X}` | Coordinator | Environment variables |
| `runtime` | `${runtime.X}` | Coordinator | Runtime values (`run_id`, `session_id`) |
| `runner` | `${runner.X}` | Runner | Runner-specific values (dynamic ports) |

## Runtime Values

| Placeholder | Value |
|-------------|-------|
| `${runtime.run_id}` | Current run ID |
| `${runtime.session_id}` | Current session ID |

## Runner Values

| Placeholder | Value |
|-------------|-------|
| `${runner.orchestrator_mcp_url}` | Orchestrator MCP URL (dynamic port at Runner) |

## Migration from Legacy Syntax

The following legacy environment variable placeholders have been replaced:

| Legacy Syntax | New Syntax | Reason |
|---------------|------------|--------|
| `${AGENT_ORCHESTRATOR_MCP_URL}` | `${runner.orchestrator_mcp_url}` | Dynamic port known only at Runner |
| `${AGENT_SESSION_ID}` | `${runtime.session_id}` | Session ID available at Coordinator |

## Resolution Flow

```
Agent Blueprint (with placeholders)
         │
         ▼
┌─────────────────────────────────────┐
│  Coordinator: PlaceholderResolver   │
│  - ${params.*}                      │
│  - ${scope.*}                       │
│  - ${env.*}                         │
│  - ${runtime.*}                     │
│  - ${runner.*} → preserved          │
└─────────────────────────────────────┘
         │
         ▼
    Run Payload (resolved_agent_blueprint)
         │
         ▼
┌─────────────────────────────────────┐
│  Runner: Final Resolution           │
│  - ${runner.*} → actual values      │
└─────────────────────────────────────┘
         │
         ▼
    Executor (fully resolved config)
```

## MCP Server Configuration

MCP servers are configured using registry references and flat config structures. The config keys map directly to HTTP headers.

### Registry Entry (defines schema and defaults)

```json
{
  "id": "orchestrator",
  "name": "Agent Orchestrator",
  "url": "${runner.orchestrator_mcp_url}",
  "config_schema": {
    "X-Agent-Session-Id": {
      "type": "string",
      "description": "Session ID for the parent agent run",
      "required": true
    },
    "X-Agent-Tags": {
      "type": "string",
      "description": "Comma-separated tags for filtering",
      "required": false
    }
  },
  "default_config": {
    "X-Agent-Session-Id": "${runtime.session_id}"
  }
}
```

### Agent/Capability Config (overrides defaults)

```json
{
  "mcpServers": {
    "orchestrator": {
      "ref": "orchestrator",
      "config": {
        "X-Agent-Tags": "internal"
      }
    }
  }
}
```

Notes:
- `config` keys are flat
- Config keys map directly to HTTP header names
- Registry `default_config` provides common defaults (e.g., `X-Agent-Session-Id`)
- Agent configs only need to specify overrides and to access the `${params.*}` placeholders

