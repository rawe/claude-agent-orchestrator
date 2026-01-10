# Architecture: Agent Types

## Status

**Implemented** - The framework supports two agent types: autonomous (AI-powered) and procedural (deterministic CLI execution).

## Overview

The Agent Orchestrator Framework uses a **unified task model** that treats AI agents and deterministic tasks uniformly. Both agent types share the same invocation interface, lifecycle management, and result handling, but differ in their execution semantics.

| Aspect | Autonomous | Procedural |
|--------|------------|------------|
| **Executor** | `ao-claude-code-exec` | `ao-procedural-exec` |
| **Processing** | AI interprets prompt | CLI command with arguments |
| **Input** | `{"prompt": "..."}` | Custom parameters schema |
| **Output** | Text (AI-generated) | JSON or structured fallback |
| **Resumption** | Supported (conversation history) | Not supported (stateless) |
| **Blueprint Storage** | Coordinator (file-based) | Runner (bundled with executor) |

## Design Philosophy

**Core Principle: "Prompt is just a parameter"**

The framework unifies AI agents and deterministic tasks through a single invocation model:

- All tasks are invoked with `parameters: dict` validated against `parameters_schema`
- All tasks produce results (via `result` events)
- AI agents use an implicit schema: `{"prompt": string}`
- Procedural tasks use custom schemas matching their requirements
- The executor type is hidden from callers

This design provides:
- **Uniform API**: Callers don't need to know whether a task is AI or deterministic
- **Type safety**: Parameters validated before execution
- **AI self-correction**: Schema included in validation errors enables AI callers to retry

## Invocation Model

### Unified Parameters

All agent invocations use the same structure:

```
POST /runs
{
  "agent_name": "my-agent",
  "parameters": {
    "key": "value",
    ...
  }
}
```

For autonomous agents, a convenience shorthand exists:

```
POST /runs
{
  "agent_name": "researcher",
  "prompt": "Research topic X"
}
```

This is internally converted to `{"parameters": {"prompt": "Research topic X"}}`.

### Executor Invocation Schema (v2.2)

The Runner passes invocations to executors via stdin as JSON:

```json
{
  "schema_version": "2.2",
  "mode": "start",
  "session_id": "ses_abc123",
  "parameters": {
    "prompt": "Hello"
  },
  "project_dir": "/path/to/project",
  "agent_name": "researcher",
  "agent_blueprint": {
    "name": "researcher",
    "system_prompt": "You are a research assistant...",
    "mcp_servers": { ... }
  }
}
```

Key fields:
- `schema_version`: Always "2.2" (enforced)
- `mode`: Either "start" (new session) or "resume" (continue existing)
- `parameters`: The task input (validated against schema before reaching executor)
- `agent_blueprint`: Resolved configuration for the agent

## Parameter Validation

### Schema-Based Validation

Parameters are validated at the Coordinator before run creation using JSON Schema (Draft 7).

**Autonomous agents** use an implicit schema:

```json
{
  "type": "object",
  "required": ["prompt"],
  "properties": {
    "prompt": {
      "type": "string",
      "minLength": 1
    }
  },
  "additionalProperties": false
}
```

**Procedural agents** define explicit schemas in their agent definition:

```json
{
  "name": "web-crawler",
  "type": "procedural",
  "command": "./crawl.sh",
  "parameters_schema": {
    "type": "object",
    "required": ["url"],
    "properties": {
      "url": { "type": "string", "format": "uri" },
      "depth": { "type": "integer", "default": 2 },
      "follow_external": { "type": "boolean", "default": false }
    }
  }
}
```

### Validation Flow

```
1. Request arrives: POST /runs with parameters
2. Coordinator fetches agent blueprint
3. Get parameters_schema (explicit or implicit)
4. Validate parameters against schema
5. If invalid: Return 400 with detailed errors + schema
6. If valid: Create run and queue for execution
```

### Validation Error Response

When validation fails, the response includes the full schema to enable AI self-correction:

```json
{
  "error": "parameter_validation_failed",
  "message": "Parameters do not match agent's parameters_schema",
  "agent_name": "web-crawler",
  "validation_errors": [
    {
      "path": "$.url",
      "message": "'not-a-url' is not a valid URI",
      "schema_path": "properties.url.format"
    }
  ],
  "parameters_schema": { ... }
}
```

## Agent Types

### Autonomous Agents

Autonomous agents are AI-powered sessions using Claude or other LLMs.

**Characteristics:**
- Execute via Claude Agent SDK or similar AI frameworks
- Support session resumption (conversation history preserved)
- Output is unpredictable (AI-generated)
- Blueprint stored in Coordinator's agents directory

**Executor:** `ao-claude-code-exec`
- Reads invocation from stdin
- Uses Claude Agent SDK to run sessions
- Reports events via session client
- Supports both `start` and `resume` modes

**Blueprint Location:** `config/agents/` (or configured `AGENT_ORCHESTRATOR_AGENTS_DIR`)

**Example Blueprint:**
```json
{
  "name": "researcher",
  "type": "autonomous",
  "description": "Research assistant with web access",
  "system_prompt": "You are a research assistant...",
  "mcp_servers": {
    "orchestrator": {
      "type": "http",
      "url": "${AGENT_ORCHESTRATOR_MCP_URL}"
    }
  }
}
```

### Procedural Agents

Procedural agents execute deterministic CLI commands with structured input/output.

**Characteristics:**
- Execute shell commands or scripts
- No resumption (stateless function calls)
- Output is predictable (programmed)
- Blueprint bundled with the executor on the Runner

**Executor:** `ao-procedural-exec`
- Reads invocation from stdin
- Fetches command from agent registration
- Converts parameters to CLI arguments
- Executes subprocess with 5-minute timeout
- Parses output as JSON (or wraps in structured fallback)
- Sends result event to Coordinator

**Blueprint Location:** Runner's `agents_dir` (defined in executor profile)

**Example Blueprint:**
```json
{
  "name": "echo",
  "description": "Echoes parameters as JSON",
  "command": "./scripts/echo/echo",
  "parameters_schema": {
    "type": "object",
    "required": ["message"],
    "properties": {
      "message": { "type": "string" },
      "uppercase": { "type": "boolean", "default": false }
    }
  }
}
```

### Parameter to CLI Conversion

The procedural executor converts parameters to CLI arguments:

| Parameter Type | CLI Format |
|----------------|------------|
| String/Number | `--key value` |
| Boolean `true` | `--flag` |
| Boolean `false` | (omitted) |
| Array | `--key item1,item2,item3` |

Example:
```json
{
  "url": "https://example.com",
  "depth": 3,
  "verbose": true,
  "quiet": false,
  "tags": ["news", "tech"]
}
```

Becomes:
```bash
./crawl.sh --url https://example.com --depth 3 --verbose --tags news,tech
```

## Result Handling

### Result Event

Both agent types produce `result` events that are stored and retrievable:

```json
{
  "event_type": "result",
  "session_id": "ses_abc123",
  "timestamp": "2025-01-10T12:00:00Z",
  "result_type": "procedural",
  "result_text": null,
  "result_data": {
    "status": "success",
    "items_processed": 42
  },
  "exit_code": 0
}
```

**Fields:**
- `result_type`: "autonomous" or "procedural"
- `result_text`: Text output (primarily for autonomous agents)
- `result_data`: Structured JSON output (primarily for procedural agents)
- `exit_code`: Process exit code (procedural only, 0 = success)

### Retrieving Results

```
GET /sessions/{session_id}/result

Response:
{
  "result_type": "procedural",
  "result_text": null,
  "result_data": { ... },
  "exit_code": 0
}
```

### Procedural Output Handling

The procedural executor attempts to parse stdout as JSON:

1. **If valid JSON**: Uses as `result_data`
2. **If not JSON**: Creates structured fallback:
   ```json
   {
     "return_code": 0,
     "stdout": "raw output text",
     "stderr": ""
   }
   ```

## Executor Profiles

Executor profiles define how the Runner processes runs for each agent type.

**Location:** `servers/agent-runner/profiles/`

### Autonomous Profile Example

```json
{
  "type": "autonomous",
  "command": "executors/claude-code/ao-claude-code-exec",
  "config": {
    "max_turns": 50
  }
}
```

### Procedural Profile Example

```json
{
  "type": "procedural",
  "command": "executors/procedural-executor/ao-procedural-exec",
  "agents_dir": "executors/procedural-executor/scripts/echo/agents",
  "config": {}
}
```

**Profile Fields:**
- `type`: "autonomous" or "procedural"
- `command`: Path to executor binary (relative to runner)
- `agents_dir`: Where to find agent definitions (procedural only)
- `config`: Executor-specific configuration

### Running with Profiles

```bash
# Default autonomous profile
./servers/agent-runner/agent-runner

# Specific procedural profile
./servers/agent-runner/agent-runner -x echo

# Test procedural profile
./servers/agent-runner/agent-runner -x test-procedural
```

## Runner-Owned Blueprints

Procedural agents have blueprints that live on the Runner, not the Coordinator.

### Rationale

- Deterministic tasks (scripts, CLI tools) are installed on specific machines
- Blueprint availability is tied to executor availability
- Registration announces blueprints; disconnect removes them
- Clean lifecycle: no stale agent references

### Registration Flow

```
Runner startup
    │
    ├─► Load agents from agents_dir
    │   (Each agent.json becomes a discoverable agent)
    │
    ├─► POST /runner/register
    │   {
    │     "hostname": "...",
    │     "executor_type": "procedural",
    │     "executor_profile": "echo",
    │     "agents": [
    │       { "name": "echo", "type": "procedural", ... }
    │     ]
    │   }
    │
    └─► Coordinator stores agents bound to runner_id
```

### Agent Name Collision

When multiple runners try to register agents with the same name:

- **Policy:** First runner wins (rejection)
- Registration rejected with HTTP 409 Conflict
- Error includes: agent name, existing runner ID

This ensures predictable external API behavior without hidden renaming.

## Lifecycle and Disconnect Handling

### Runner Heartbeat

Runners send heartbeats every 60 seconds. Status progression:

1. **Online**: Heartbeat received within threshold
2. **Stale**: No heartbeat for 120 seconds (configurable)
3. **Removed**: No heartbeat for 600 seconds (configurable)

### Disconnect Cleanup

When a runner is removed:

1. **Blueprint cleanup**: All runner's agents are deleted
2. **Orphaned runs**: Active runs marked as failed with error "Runner disconnected during execution"
3. **Session update**: Session status set to "failed"
4. **Event broadcast**: `RUN_FAILED` event sent via SSE
5. **Callbacks**: Parent orchestrators receive failure callbacks

### No Automatic Retry

The framework does not auto-retry failed runs. Orchestrating agents decide whether to retry with same or different parameters.

## Validation Semantics by Agent Type

| Aspect | Autonomous | Procedural |
|--------|------------|------------|
| Output unpredictability | High (AI-generated) | None (programmed) |
| On validation failure | Retry with feedback | Fail immediately |
| Rationale | AI can learn and correct | Bug in code; retry won't help |

For autonomous agents, validation errors are feedback that enables AI self-correction. For procedural agents, validation errors indicate a bug in the calling code that must be fixed.

## Agent API

### Agent Listing

```
GET /agents

Response:
{
  "agents": [
    {
      "name": "researcher",
      "type": "autonomous",
      "description": "Research assistant"
    },
    {
      "name": "web-crawler",
      "type": "procedural",
      "description": "Crawls web pages",
      "parameters_schema": {
        "type": "object",
        "required": ["url"],
        "properties": {
          "url": { "type": "string", "format": "uri" }
        }
      }
    }
  ]
}
```

Notes:
- Autonomous agents don't expose `parameters_schema` (implicit: `{prompt: string}`)
- Procedural agents include `parameters_schema` for callers to construct valid input

### Run Creation

```
POST /runs
{
  "agent_name": "web-crawler",
  "parameters": {
    "url": "https://example.com",
    "depth": 3
  },
  "mode": "sync"
}
```

Modes:
- `sync`: Wait for completion (streaming response)
- `async_poll`: Return immediately, poll for result
- `async_callback`: Return immediately, callback on completion

## Component Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Agent Coordinator                                │
│                                                                         │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────────┐   │
│  │ Agent Registry  │  │ Parameter        │  │ Result Storage       │   │
│  │ (file + runner) │  │ Validator        │  │ (events table)       │   │
│  └────────┬────────┘  └────────┬─────────┘  └──────────┬───────────┘   │
│           │                    │                       │                │
│           ▼                    ▼                       ▼                │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                        Run Queue                                  │  │
│  │  - Validates parameters against schema                           │  │
│  │  - Routes to appropriate runner                                  │  │
│  │  - Tracks run status                                             │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                    Long-poll       │      Reports status
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                           Agent Runner                                  │
│                                                                         │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────────┐   │
│  │ Profile Loader  │  │ Agent Loader     │  │ Run Supervisor       │   │
│  │ (type, command) │  │ (agents_dir)     │  │ (spawn, monitor)     │   │
│  └────────┬────────┘  └────────┬─────────┘  └──────────┬───────────┘   │
│           │                    │                       │                │
│           ▼                    ▼                       ▼                │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     Executor Spawner                              │  │
│  │  - Builds invocation JSON                                        │  │
│  │  - Spawns executor subprocess                                    │  │
│  │  - Captures exit code                                            │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                     Subprocess     │      stdin: invocation JSON
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                            Executors                                    │
│                                                                         │
│  ┌─────────────────────────────┐  ┌─────────────────────────────────┐  │
│  │    ao-claude-code-exec      │  │     ao-procedural-exec          │  │
│  │                             │  │                                 │  │
│  │  - Claude Agent SDK         │  │  - CLI argument builder         │  │
│  │  - Session resumption       │  │  - Subprocess execution         │  │
│  │  - AI interpretation        │  │  - JSON output parsing          │  │
│  │  - Message events           │  │  - Result event                 │  │
│  └─────────────────────────────┘  └─────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

## Summary

The unified agent type architecture provides:

1. **Consistent Interface**: Both agent types use the same API for invocation and result retrieval
2. **Type Safety**: JSON Schema validation prevents invalid parameters from reaching executors
3. **Flexibility**: Autonomous agents for AI tasks, procedural agents for deterministic operations
4. **Clean Lifecycle**: Runner-owned blueprints are automatically cleaned up on disconnect
5. **Error Handling**: Structured validation errors enable AI self-correction
6. **Extensibility**: New executor types can be added by implementing the invocation protocol
