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

## Files Updated

The following configuration files use placeholders for the Orchestrator MCP server:

- `config/agents/agent-orchestrator/agent.mcp.json`
- `config/agents/agent-orchestrator-external/agent.mcp.json`
- `config/agents/agent-orchestrator-internal/agent.mcp.json`
- `config/agents/knowledge-coordinator/agent.mcp.json`
- `config/agents/module-research-coordinator/agent.mcp.json`
- `config/agents/self-improving-agent/agent.mcp.json`
- `config/capabilities/agent-orchestrator/capability.mcp.json`

Each uses:
```json
{
  "mcpServers": {
    "agent-orchestrator-http": {
      "type": "http",
      "url": "${runner.orchestrator_mcp_url}",
      "headers": {
        "X-Agent-Session-Id": "${runtime.session_id}"
      }
    }
  }
}
```
