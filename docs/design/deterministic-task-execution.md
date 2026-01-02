# Deterministic Task Execution

**Status:** Draft
**Date:** 2025-12-31

## Overview

The Agent Orchestrator currently only supports AI agent execution via prompts. Many orchestration scenarios require deterministic tasks alongside AI agents:

| Type | Input | Behavior |
|------|-------|----------|
| AI Agent | Free-form prompt | Non-deterministic, AI interprets |
| Deterministic | Structured parameters | Deterministic, parameter-driven |

Examples: web crawling, database operations, test execution, data pipelines.

**Key requirement:** Deterministic tasks must integrate with the existing run lifecycle and callback system (ADR-003) so orchestrating agents can invoke them uniformly.

## Design

### 1. Runner-Owned Blueprints

Unlike AI agent blueprints (centrally managed on coordinator), deterministic blueprints are **owned by the runner**:

- Deterministic apps are installed on specific runner hosts
- Runner announces its blueprints at registration
- Coordinator binds blueprint to that runner
- Blueprint is deleted when runner disconnects

This couples blueprint availability to executor availability.

### 2. Registration Flow

```
POST /runner/register {
    "hostname": "crawler-host",
    "executor_type": "deterministic",
    "tags": ["python", "playwright"],
    "blueprints": [
        {
            "name": "web-crawler",
            "description": "Crawls websites to specified depth",
            "command": "python -m crawler.main",
            "parameters_schema": { ... }
        }
    ]
}
```

Coordinator:
1. Registers runner, assigns `runner_id`
2. Stores blueprints bound to that `runner_id`
3. Runs for these blueprints route only to this runner

### 3. Naming Collision Handling

When multiple runners register blueprints with the same name:

| Registration | Stored Name |
|--------------|-------------|
| First `web-crawler` | `web-crawler` |
| Second `web-crawler` (runner `lnch_abc123`) | `web-crawler@lnch_abc123` |

Coordinator handles collisions transparently. Runner is unaware of suffix.

### 4. Blueprint Configuration

Runner CLI parameter specifies config directory:

```bash
./agent-runner --config-dir ~/.agent-runner
```

Convention:
```
~/.agent-runner/
└── blueprints/
    ├── web-crawler.json
    └── db-backup.json
```

Blueprint file format:
```json
{
  "name": "web-crawler",
  "description": "Crawls websites to specified depth",
  "command": "python -m crawler.main",
  "parameters_schema": {
    "type": "object",
    "required": ["url"],
    "properties": {
      "url": { "type": "string", "format": "uri" },
      "depth": { "type": "integer", "default": 2 },
      "patterns": { "type": "array", "items": { "type": "string" } }
    }
  }
}
```

No `type` field needed - implied by location in `blueprints/` folder.

### 5. Parameter Passing

Parameters passed as CLI arguments:

```bash
python -m crawler.main --url "https://example.com" --depth 2 --patterns "*.html,*.md"
```

Rules:
- Parameter names passed as-is (no case conversion)
- Arrays serialized as comma-separated values
- Booleans: `--flag` if true, omitted if false

### 6. Result Handling

Generic result model:

```json
{
  "result_text": "...(raw stdout)...",
  "exit_code": 0
}
```

- `exit_code`: 0 = success, non-zero = error
- `result_text`: Raw stdout captured as text
- Executor does not parse or interpret stdout

During execution, stderr lines sent as events to coordinator (line by line, real-time).

### 7. Schema Discovery

Listing endpoint returns type indicator without full schema (token-efficient):

```json
{
  "agents": [
    {"name": "web-researcher", "type": "agent", "description": "..."},
    {"name": "web-crawler", "type": "deterministic", "description": "...", "has_schema": true}
  ]
}
```

Separate endpoint for full schema:
```
GET /agents/{name}/schema
```

Orchestrating agents fetch schema on-demand before invoking deterministic tasks.

### 8. Invocation

Orchestrators use `start_agent_session` with `parameters` instead of `prompt`:

```python
# AI agent
start_agent_session(agent_name="researcher", prompt="Research topic X")

# Deterministic task
start_agent_session(agent_name="web-crawler", parameters={"url": "...", "depth": 2})
```

Coordinator validates parameters against schema before creating run.

### 9. Deterministic Executor

A new executor following the existing pattern:

```
servers/agent-runner/executors/
├── claude-code/                    # AI agent executor (existing)
│   └── ao-claude-code-exec
└── deterministic/                  # Deterministic executor (new)
    └── ao-deterministic-exec
```

**Runner configuration:**
```bash
# AI agent runner
./agent-runner --executor-path executors/claude-code/ao-claude-code-exec

# Deterministic runner
./agent-runner --executor-path executors/deterministic/ao-deterministic-exec --config-dir ~/.agent-runner
```

Each runner type uses its own executor. The runner stays generic - it spawns whichever executor is configured.

**Invocation schema (deterministic):**

The deterministic executor has its own minimal schema, separate from the claude-code executor schema:

```json
{
  "schema_version": "1.0",
  "session_id": "ses_abc123",
  "command": "python -m crawler.main",
  "parameters": {
    "url": "https://example.com",
    "depth": 2,
    "patterns": ["*.html", "*.md"]
  }
}
```

Runner passes this payload via stdin to the executor.

**Executor responsibilities:**

1. Parse invocation payload from stdin
2. Build CLI arguments from parameters
3. Spawn command as subprocess
4. Stream stderr lines as events to coordinator (via proxy)
5. Capture stdout for result
6. Report completion with `result_text` and `exit_code`

**Communication with coordinator:**

Same as claude-code executor - uses the Agent Coordinator Proxy started by the runner:

```
Executor → HTTP → Proxy (localhost) → HTTP + Auth → Coordinator
```

Events endpoint: `POST /sessions/{session_id}/events`

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Runner Registration                                            │
│                                                                 │
│  Runner starts with:                                            │
│    --executor-path executors/deterministic/ao-deterministic-exec│
│    --config-dir ~/.agent-runner                                 │
│                                                                 │
│  Loads blueprints from blueprints/*.json                        │
│  POST /runner/register { blueprints: [...] }                    │
│  Coordinator stores blueprints bound to runner_id               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Run Creation                                                   │
│                                                                 │
│  Orchestrator: start_agent_session("web-crawler", params={...}) │
│  Coordinator: validates params against schema                   │
│  Coordinator: creates run, routes to bound runner only          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Execution                                                      │
│                                                                 │
│  Runner claims run, builds invocation payload:                  │
│  { session_id, command, parameters }                            │
│                                                                 │
│  Runner spawns executor: ao-deterministic-exec < payload        │
│                                                                 │
│  Executor:                                                      │
│    1. Parses payload                                            │
│    2. Builds CLI args from parameters                           │
│    3. Spawns: python -m crawler.main --url "..." --depth 2      │
│    4. Streams stderr → events (via proxy)                       │
│    5. Captures stdout                                           │
│    6. Reports result + exit_code                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Completion                                                     │
│                                                                 │
│  Result: { result_text: "...", exit_code: 0 }                   │
│  Callback triggered if async_callback mode (ADR-003)            │
└─────────────────────────────────────────────────────────────────┘
```

**Comparison: AI Agent vs Deterministic**

```
AI Agent Runner:
  Runner → ao-claude-code-exec → Claude Agent SDK → AI Model

Deterministic Runner:
  Runner → ao-deterministic-exec → subprocess → External App
```

## Out of Scope

- **Deployment of deterministic apps** - Apps must be pre-installed on runner host
- **Orchestrator decision logic** - When/how orchestrators fetch schemas is their concern

## Consequences

### Positive

- Unified orchestration: same `start_agent_session` for both types
- Callback integration: deterministic tasks participate in async callbacks
- Type safety: structured parameters with JSON Schema validation
- No AI overhead: deterministic tasks run without AI interpretation
- Clean lifecycle: blueprint availability tied to executor availability

### Negative

- Runner configuration: need to maintain blueprint configs on runner hosts
- Schema maintenance: blueprints need parameter schema definitions

## References

- [ADR-002](../adr/ADR-002-agent-runner-architecture.md) - Agent Runner Architecture
- [ADR-003](../adr/ADR-003-callback-based-async.md) - Callback-Based Async
- [ADR-011](../adr/ADR-011-runner-capabilities-and-run-demands.md) - Runner Capabilities and Run Demands
