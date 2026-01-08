# Deterministic Agents Implementation Guide

**Status:** Implementation Reference
**Date:** 2026-01-08
**References:**
- [deterministic-task-execution.md](./deterministic-task-execution.md) - Original design concepts
- [unified-task-model-overview.md](./unified-task-model-overview.md) - Unified invocation model
- [structured-output-schema-enforcement.md](./structured-output-schema-enforcement.md) - Output schema enforcement
- [notes-structured-output-deterministic-synergy.md](./notes-structured-output-deterministic-synergy.md) - AI↔Deterministic type-safe handoff
- [ADR-003](../adr/ADR-003-callback-based-async.md) - Callback-based async
- [ADR-011](../adr/ADR-011-runner-capabilities-and-run-demands.md) - Runner capabilities
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture overview

**Implementation Phases:**
- [Phase 1: Unified Input](./deterministic-agents-phase-1-unified-input.md) - Migrate to `parameters: dict`
- [Phase 2: Structured Output](./deterministic-agents-phase-2-structured-output.md) - Introduce `result` events
- [Phase 3: Schema Validation](./deterministic-agents-phase-3-schema-validation.md) - Discovery and validation
- [Phase 4: Deterministic Executor](./deterministic-agents-phase-4-deterministic-executor.md) - New executor and blueprints
- [Phase 5: Production Hardening](./deterministic-agents-phase-5-production-hardening.md) - Disconnect handling, collisions

---

## Summary

This document defines **how to implement deterministic agents** in the Agent Orchestrator framework. Deterministic agents are non-AI tasks (scripts, CLI tools, data pipelines) that execute with structured parameters and produce structured output.

**Core principle:** Deterministic agents use the same orchestration infrastructure as AI agents - same session model, same callback system, same runner dispatch.

---

## Architectural Decisions

### 1. Blueprints Are Runner-Owned

Deterministic blueprints live on the runner host, not in the coordinator.

**Rationale:** Deterministic apps (Python scripts, CLI tools) are installed on specific machines. The blueprint must be co-located with the executable.

```
Runner Host:
~/.agent-runner/
└── blueprints/
    ├── web-crawler.json
    └── db-backup.json
```

Blueprint format:
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
      "depth": { "type": "integer", "default": 2 }
    }
  }
}
```

**Runner registration announces blueprints:**
```
POST /runner/register
{
  "hostname": "crawler-host",
  "executor_type": "deterministic",
  "blueprints": [
    { "name": "web-crawler", ... }
  ]
}
```

Coordinator stores blueprints bound to that runner. When runner disconnects, its blueprints are removed.

---

### 2. Unified Invocation Model

**Core insight:** "Prompt is just a parameter." Both AI agents and deterministic agents use the same invocation signature with a unified `parameters` field.

#### The Unified `parameters` Field

All agents - AI and deterministic - are invoked with `parameters`:

```python
# MCP Tool signature
start_agent_session(
    agent_name: str,
    parameters: dict,      # Required - schema depends on agent type
    mode: str = "sync"     # sync | async_poll | async_callback
)
```

**For AI agents** (implicit schema `{prompt: string}`):
```python
start_agent_session(
    agent_name="researcher",
    parameters={"prompt": "Research quantum computing trends"},
    mode="async_callback"
)
```

**For deterministic agents** (custom schema):
```python
start_agent_session(
    agent_name="web-crawler",
    parameters={"url": "https://example.com", "depth": 3},
    mode="async_callback"
)
```

**Backward compatibility sugar:** For convenience, `prompt` is accepted as shorthand:
```python
# This sugar:
start_agent_session(agent_name="researcher", prompt="Research X")

# Is equivalent to:
start_agent_session(agent_name="researcher", parameters={"prompt": "Research X"})
```

#### Why Unified Parameters?

| Aspect | Separate `prompt`/`parameters` | Unified `parameters` |
|--------|-------------------------------|----------------------|
| AI decision cost | Must choose which field | Always use `parameters` |
| Ambiguity | What if both provided? | None |
| Rich AI inputs | Awkward mixing | Natural extension |
| Mental model | "AI agents are special" | "All tasks are uniform" |
| Future-proof | Limited | AI agents can have rich schemas |

**The ~2 token overhead (`{"prompt": "..."}` vs `"..."`) is negligible compared to the architectural clarity.**

#### Implicit Schema for AI Agents

AI agents without explicit `parameters_schema` use an implicit default:

```json
{
  "type": "object",
  "required": ["prompt"],
  "properties": {
    "prompt": { "type": "string", "minLength": 1 }
  }
}
```

This means **every agent has a `parameters_schema`** - the only difference is complexity.

#### Future: Rich AI Agent Inputs

The unified model naturally enables rich inputs for AI agents:

```json
{
  "name": "code-reviewer",
  "type": "agent",
  "parameters_schema": {
    "type": "object",
    "required": ["prompt"],
    "properties": {
      "prompt": { "type": "string" },
      "files": { "type": "array", "items": { "type": "string" } },
      "focus_areas": { "type": "array", "items": { "type": "string" } },
      "severity_threshold": { "type": "string", "enum": ["info", "warning", "error"] }
    }
  }
}
```

Invocation:
```python
start_agent_session("code-reviewer", parameters={
    "prompt": "Review security implications",
    "files": ["src/auth/**/*.ts"],
    "focus_areas": ["injection", "authentication"],
    "severity_threshold": "error"
})
```

---

### 3. Handling AI Agent Results from Deterministic Agents

When a deterministic agent needs to call an AI agent and process its result:

**Option A: Synchronous call (blocking)**
```python
# Deterministic script calls AI agent synchronously
result = call_ai_agent(
    agent_name="summarizer",
    prompt="Summarize this content...",
    mode="sync"
)
# result contains AI output, script continues
```

**Option B: Callback-based (non-blocking)**

Deterministic agents **should not use callbacks** to receive AI results. Callbacks resume sessions, but deterministic tasks are stateless - there's no session to resume.

**The simple solution:** Deterministic agents that need AI results use **sync mode**. The script blocks until the AI completes.

```python
# ao-deterministic-exec implementation
def execute_with_ai_call(invocation):
    # 1. Run deterministic logic
    data = crawl_website(invocation.parameters)

    # 2. Call AI agent synchronously (via coordinator API)
    summary = coordinator_client.start_agent_session(
        agent_name="summarizer",
        prompt=f"Summarize: {data}",
        mode="sync"  # Block until AI completes
    )

    # 3. Continue with AI result
    return format_report(data, summary)
```

**Why no callback for deterministic agents:**
- Callbacks are designed for session resumption
- Deterministic tasks have no session state to resume
- Sync calls are simpler and sufficient for this use case

---

### 4. Resumption of Deterministic Agents

**Deterministic agents do not support resumption.**

**Rationale:**
- Resumption restores conversation state (message history)
- Deterministic tasks have no conversation - they're stateless function calls
- If a deterministic task fails, you restart it from scratch

**What about long-running tasks?**

For long-running deterministic tasks that fail mid-execution:
1. The task writes checkpoints to disk (application responsibility)
2. On restart, the task reads checkpoints and continues
3. This is application-level checkpointing, not framework resumption

**Example: Crawler with checkpointing**
```python
# Application handles its own state
def crawl():
    checkpoint = load_checkpoint_if_exists()
    visited = checkpoint.visited if checkpoint else set()

    for url in urls:
        if url in visited:
            continue
        crawl_page(url)
        visited.add(url)
        save_checkpoint(visited)  # Application responsibility
```

**Framework behavior:**
- `mode: "resume"` is rejected for deterministic agents
- Error: "Deterministic agents do not support resumption"

---

### 5. Schema Discovery

The agent listing endpoint returns `parameters_schema` inline for deterministic agents. This enables AI orchestrators to discover schemas without additional API calls.

#### List Agents Response

```json
GET /agents

{
  "agents": [
    {
      "name": "researcher",
      "type": "agent",
      "description": "Research assistant for technical topics"
    },
    {
      "name": "web-crawler",
      "type": "deterministic",
      "description": "Crawls websites to specified depth",
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
  ]
}
```

**Key design decisions:**
- AI agents return `type: "agent"` with no `parameters_schema` (implicit schema applies)
- Deterministic agents return `type: "deterministic"` with full `parameters_schema` inline
- Schema is included in listing to minimize round-trips (AI sees schema immediately)

#### MCP Tool: `list_agent_blueprints`

The MCP server exposes this via `list_agent_blueprints`:

```python
@mcp.tool(description="""
List available agent blueprints.

Returns agent metadata including type and parameters_schema.
For deterministic agents, use parameters_schema to construct valid parameters.
For AI agents, use parameters={"prompt": "your instructions"}.
""")
async def list_agent_blueprints() -> list[dict]:
    # Returns agents with type and parameters_schema inline
```

---

### 6. Parameter Validation

The coordinator validates `parameters` against `parameters_schema` **before creating a run**. This catches invalid parameters early, before wasting runner resources.

#### Validation Flow

```
POST /runs
  │
  ├─► Fetch agent blueprint
  │
  ├─► Get parameters_schema (explicit or implicit)
  │
  ├─► Validate parameters against schema (JSON Schema Draft 7)
  │
  ├─► If valid: Create run
  │
  └─► If invalid: Return 400 with validation errors
```

#### Validation Error Response

When parameters don't match the schema, the coordinator returns a structured error:

```json
HTTP 400 Bad Request

{
  "error": "parameter_validation_failed",
  "message": "Parameters do not match agent's parameters_schema",
  "agent_name": "web-crawler",
  "validation_errors": [
    {
      "path": "$.url",
      "message": "'not-a-url' is not a valid URI",
      "schema_path": "properties.url.format"
    },
    {
      "path": "$.depth",
      "message": "'deep' is not of type 'integer'",
      "schema_path": "properties.depth.type"
    }
  ],
  "parameters_schema": {
    "type": "object",
    "required": ["url"],
    "properties": {
      "url": { "type": "string", "format": "uri" },
      "depth": { "type": "integer", "default": 2 }
    }
  }
}
```

**Error response includes:**
- `validation_errors`: Array of specific validation failures with JSON path
- `parameters_schema`: The full schema for reference (enables AI self-correction)

#### AI Self-Correction

When an AI orchestrator receives a validation error, it can self-correct:

1. AI constructs parameters (possibly incorrectly)
2. Coordinator returns 400 with validation errors and schema
3. AI reads errors and schema, constructs corrected parameters
4. AI retries with valid parameters

This loop happens at the API level, not inside the framework.

---

### 7. AI Orchestrator Parameter Construction

**AI orchestrators construct parameters using their native JSON generation capability after discovering the schema.**

This is a critical design principle: the framework does **not** transform prompts into structured parameters. Instead:

1. AI orchestrator lists agents → receives `parameters_schema` inline
2. AI reads the schema and understands the required structure
3. AI constructs a valid `parameters` object matching the schema
4. AI calls `start_agent_session` with those parameters

#### Why No Framework Transformation?

| Approach | Pros | Cons |
|----------|------|------|
| **Framework transforms prompt→parameters** | Simpler caller experience | Hidden AI cost/latency, magic behavior, not KISS |
| **AI constructs parameters natively** | Transparent, no hidden costs, KISS | AI must understand schemas |

Modern LLMs (like Claude) are excellent at reading JSON schemas and producing matching JSON. This is a **native capability**, not something requiring framework support.

#### Example Flow

```
AI Orchestrator receives task: "Crawl example.com and extract product data"
    │
    ├─► 1. list_agent_blueprints()
    │      Returns: [{name: "web-crawler", type: "deterministic",
    │                 parameters_schema: {url: string, depth: int, ...}}]
    │
    ├─► 2. AI reasons: "I need to call web-crawler with url and depth"
    │      AI constructs: {"url": "https://example.com", "depth": 3}
    │
    └─► 3. start_agent_session("web-crawler",
    │          parameters={"url": "https://example.com", "depth": 3})
    │
    └─► 4. Coordinator validates parameters ✓, creates run
```

**The "transformation" from natural language to structured parameters happens inside the AI's reasoning, not in framework code.**

#### MCP Tool Description

The MCP tool description guides AI orchestrators:

```python
@mcp.tool(description="""
Start an agent session.

Args:
    agent_name: Name of the agent to invoke
    parameters: Input parameters matching the agent's parameters_schema.
                - For AI agents: {"prompt": "your instructions"}
                - For deterministic agents: see agent's parameters_schema
    mode: Execution mode (sync, async_poll, async_callback)

Discover agent schemas via list_agent_blueprints() before calling.
Parameters are validated against the schema - invalid parameters return an error
with details that can be used to self-correct.
""")
async def start_agent_session(
    agent_name: str,
    parameters: dict,
    mode: str = "sync"
) -> dict:
```

---

### 8. Structured Result Events

**Core insight:** Just as input is unified via `parameters`, output should be unified via structured **result events**.

#### Current AI Agent Result Pattern

AI agents currently store results as assistant message events:

```json
{
  "event_type": "message",
  "session_id": "ses_abc123",
  "timestamp": "2026-01-08T12:00:00Z",
  "role": "assistant",
  "content": [{"type": "text", "text": "Here is the research summary..."}]
}
```

The coordinator extracts result text from the last assistant message for callbacks.

#### Structured Result Event for Deterministic Agents

Deterministic agents send a dedicated `result` event:

```json
{
  "event_type": "result",
  "session_id": "ses_abc123",
  "timestamp": "2026-01-08T12:00:00Z",
  "result_type": "deterministic",
  "result_text": "raw stdout output",
  "result_data": {
    "pages_crawled": 42,
    "data": [
      {"url": "https://example.com/page1", "title": "Page 1"},
      {"url": "https://example.com/page2", "title": "Page 2"}
    ]
  },
  "exit_code": 0
}
```

**Fields:**
- `event_type`: Always `"result"` for result events
- `result_type`: `"deterministic"` or `"agent"` (for future AI agent migration)
- `result_text`: Raw text output (stdout for deterministic, last message for AI)
- `result_data`: Structured JSON output (optional, parsed from stdout if valid JSON)
- `exit_code`: Process exit code (deterministic only)
- `error`: Error message if failed (optional)

#### Unified Result Model

This creates symmetry with the unified parameters model:

| Aspect | AI Agent | Deterministic Agent |
|--------|----------|---------------------|
| **Input schema** | Implicit `{prompt: string}` | Custom `parameters_schema` |
| **Output schema** | `{result_text: string}` | `{result_text, result_data, exit_code}` |
| **Result event** | `event_type: "result"` | `event_type: "result"` |

#### Callback Result Format

When a callback is triggered, the coordinator extracts the result from the `result` event:

```json
{
  "callback_type": "child_completed",
  "child_session_id": "ses_abc123",
  "result": {
    "result_type": "deterministic",
    "result_text": "...",
    "result_data": {...},
    "exit_code": 0
  }
}
```

This allows parent orchestrators to access structured data directly without parsing text.

#### Migration Path for AI Agents

For consistency, AI agents could migrate to the unified `result` event format:

```json
{
  "event_type": "result",
  "session_id": "ses_abc123",
  "result_type": "agent",
  "result_text": "Here is the research summary..."
}
```

This is optional and can be deferred - the coordinator can support both patterns during transition.

---

### 9. Creating the Deterministic Executor

Create a new executor following the existing pattern:

```
servers/agent-runner/executors/
├── claude-code/                    # AI agent executor (existing)
│   └── ao-claude-code-exec
└── deterministic/                  # Deterministic executor (new)
    └── ao-deterministic-exec
```

**Implementation: `ao-deterministic-exec`**

**Important:** Like the claude-code executor, the deterministic executor communicates with the coordinator via the **Runner Gateway** (proxy). The executor:
1. Sends **result events** to coordinator via `session_client.add_event()` during/after execution
2. Exits with appropriate code (0 = success, non-zero = failure)
3. The **RunSupervisor** monitors the exit code and signals completion to coordinator

This follows the same pattern as AI agents, where results are stored as events.

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add runner lib
runner_lib = Path(__file__).parent.parent.parent / "lib"
sys.path.insert(0, str(runner_lib))

from invocation import ExecutorInvocation
from session_client import SessionClient


def main():
    inv = ExecutorInvocation.from_stdin()

    # Reject resume mode
    if inv.mode == "resume":
        print("Error: Deterministic agents do not support resumption", file=sys.stderr)
        sys.exit(1)

    # Initialize session client for communicating with coordinator via gateway
    session_client = SessionClient(inv.gateway_url)

    # Build CLI arguments from parameters
    args = build_cli_args(inv.command, inv.parameters)

    # Execute command
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        cwd=inv.project_dir
    )

    # Send result event to coordinator (via gateway)
    # This stores the structured result for callbacks and queries
    result_event = {
        "event_type": "result",
        "session_id": inv.session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result_type": "deterministic",
        "result_text": result.stdout,
        "exit_code": result.returncode,
    }

    # Include structured data if stdout is valid JSON
    try:
        result_event["result_data"] = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        pass  # Not JSON, result_text only

    if result.returncode != 0:
        result_event["error"] = result.stderr or f"Exit code: {result.returncode}"

    session_client.add_event(inv.session_id, result_event)

    # Print result to stdout (for logging/debugging)
    print(result.stdout)

    # Exit with subprocess code - RunSupervisor uses this to signal completion
    sys.exit(result.returncode)


def build_cli_args(command: str, parameters: dict) -> list[str]:
    """Convert parameters to CLI arguments."""
    args = command.split()

    for key, value in parameters.items():
        if isinstance(value, bool):
            if value:
                args.append(f"--{key}")
        elif isinstance(value, list):
            args.extend([f"--{key}", ",".join(str(v) for v in value)])
        else:
            args.extend([f"--{key}", str(value)])

    return args


if __name__ == "__main__":
    main()
```

**Executor Communication Pattern:**
```
ao-deterministic-exec
    │
    │ 1. Runs subprocess, captures output
    │
    │ 2. Sends result event via session_client.add_event()
    │    POST /events → Runner Gateway → Coordinator
    │
    │ 3. Exits with subprocess exit code
    ▼
Runner (RunSupervisor)
    │
    │ Monitors executor process
    │ On exit: POST /runner/runs/{id}/completed or /failed
    ▼
Coordinator
    │
    │ Updates session status
    │ Triggers callback (if async_callback mode)
    │ Callback includes result from stored event
```

**Invocation schema for deterministic executor:**

```json
{
  "schema_version": "2.1",
  "mode": "start",
  "session_id": "ses_abc123",
  "command": "python -m crawler.main",
  "parameters": {
    "url": "https://example.com",
    "depth": 2
  },
  "project_dir": "/path/to/project"
}
```

**Key differences from claude-code executor:**
- Uses `command` + `parameters` instead of `prompt`
- No `agent_blueprint` with system_prompt/mcp_servers
- No resume support
- Simpler lifecycle: run command, capture output, report result

---

### 10. Runner Configuration for Deterministic Agents

**Executor profile for deterministic runner:**

```json
// profiles/deterministic.json
{
  "type": "deterministic",
  "command": "executors/deterministic/ao-deterministic-exec",
  "blueprints_dir": "~/.agent-runner/blueprints"
}
```

**Running a deterministic runner:**

```bash
./agent-runner \
  --profile deterministic \
  --blueprints-dir ~/.agent-runner/blueprints
```

**Runner behavior:**
1. Load blueprints from `blueprints_dir` at startup
2. Register with coordinator, including blueprint list
3. Poll for runs matching its blueprints
4. Spawn `ao-deterministic-exec` for each run

---

### 11. Runner Disconnect and Session Orphan Handling

**What happens when a runner disconnects while executing a deterministic task?**

#### Runner Disconnect Detection

The coordinator detects runner disconnect via heartbeat timeout (existing mechanism per ADR-006):

```
Runner sends heartbeat every 30s
    │
    └─► Coordinator marks runner "stale" after 90s no heartbeat
        │
        └─► Coordinator marks runner "offline" after 180s
            │
            └─► Runner's blueprints are removed
            └─► Running sessions on that runner are marked "failed"
```

#### Session Orphan Handling

When a runner goes offline with running sessions:

1. **Coordinator marks sessions as failed** with error: "Runner disconnected during execution"
2. **Callbacks are triggered** (if `async_callback` mode) with failure status
3. **Parent orchestrator can retry** by creating a new run

```json
{
  "session_id": "ses_abc123",
  "status": "failed",
  "error": "Runner disconnected during execution",
  "result_text": null
}
```

#### No Automatic Retry

The framework does **not** automatically retry failed deterministic tasks because:
- The task may have had side effects before failure
- Idempotency is application-specific
- The orchestrator should decide whether to retry

**Orchestrator pattern for retry:**
```python
# Parent AI agent receives failure callback
if result.status == "failed" and "Runner disconnected" in result.error:
    # Decide whether to retry based on task semantics
    if task_is_idempotent:
        start_agent_session(agent_name, parameters, mode="async_callback")
```

---

## Implementation Tasks

### Phase 1: Executor and Runner

1. **Create `ao-deterministic-exec`**
   - Parse invocation from stdin
   - Build CLI args from parameters
   - Execute subprocess
   - Send structured `result` event via `session_client.add_event()`
   - Exit with subprocess exit code
   - Location: `servers/agent-runner/executors/deterministic/`

2. **Add blueprint loading to runner**
   - Read `*.json` from blueprints directory
   - Include in registration payload
   - Add `--blueprints-dir` CLI flag

3. **Create deterministic profile**
   - Location: `servers/agent-runner/profiles/deterministic.json`
   - Set executor command and blueprints_dir

### Phase 2: Coordinator

**Prerequisite:** Add `jsonschema` dependency to coordinator for parameter validation:
```bash
cd servers/agent-coordinator && uv add jsonschema
```

4. **Store runner-bound blueprints**
   - Add `blueprints` table: `name, runner_id, config_json`
   - Insert on registration, delete on runner disconnect
   - Handle name collisions with `name@runner_id` suffix

5. **Add `type` and `parameters_schema` to agents list**
   - Return `type: "agent"` or `type: "deterministic"`
   - Return `parameters_schema` inline for deterministic agents
   - AI agents return no schema (implicit `{prompt: string}` applies)

6. **Add parameter validation**
   - Validate `parameters` against `parameters_schema` on run creation
   - Use `jsonschema.Draft7Validator` for JSON Schema Draft 7 compliance
   - Return structured 400 error with `validation_errors` array
   - Include `parameters_schema` in error response for AI self-correction

7. **Support structured result events**
   - Add `RESULT` to `SessionEventType` enum
   - Extend events table with `result_type` (discriminator: `"agent"` | `"deterministic"`) and `result_data` (JSON) columns
   - Update `get_session_result()` to prioritize `result` events, falling back to legacy `message` extraction for backward compatibility
   - Include structured result in callback payload

### Phase 3: Run Dispatch

8. **Route runs to correct runner**
   - Deterministic runs only go to runner that owns the blueprint
   - Use `runner_id` from blueprint binding

9. **Accept unified `parameters` in run creation**
   - `POST /runs` accepts `parameters` field (required)
   - Accept `prompt` as sugar → converts to `{"prompt": "..."}`
   - Validate against agent's `parameters_schema`

### Phase 4: MCP Integration

10. **Update `start_agent_session` MCP tool**
    - Use unified `parameters: dict` field (required)
    - Accept `prompt` as backward-compat sugar
    - Update tool description to explain unified model

11. **Update `list_agent_blueprints` MCP tool**
    - Return `type` and `parameters_schema` inline
    - Enable AI orchestrators to discover schemas without extra calls

---

## Result Model

Deterministic agents send a structured `result` event to the coordinator:

```json
{
  "event_type": "result",
  "session_id": "ses_abc123",
  "timestamp": "2026-01-08T12:00:00Z",
  "result_type": "deterministic",
  "result_text": "...raw stdout...",
  "result_data": {
    "pages_crawled": 42,
    "data": [...]
  },
  "exit_code": 0
}
```

**Fields:**
- `result_text`: Raw stdout from subprocess (always present)
- `result_data`: Structured JSON if stdout is valid JSON (optional)
- `exit_code`: Process exit code (0 = success)
- `error`: Error message if failed (optional)

**During execution:** stderr lines can be streamed as progress events to coordinator.

**On completion:** Executor sends `result` event, then exits. RunSupervisor signals completion.

**Callback payload:** Includes the full result object for structured access by parent orchestrator.

---

## Flow Diagram

```
AI Agent (orchestrator)
    │
    │ 1. list_agent_blueprints()
    │    → Receives type + parameters_schema inline
    │
    │ 2. AI constructs parameters matching schema
    │    (native JSON generation capability)
    │
    │ 3. start_agent_session("web-crawler", parameters={...})
    ▼
MCP Server
    │
    │ POST /runs { agent_name, parameters, mode }
    ▼
Coordinator
    │
    │ 1. Fetch agent blueprint
    │ 2. Validate parameters against parameters_schema
    │    → If invalid: return 400 with validation_errors
    │ 3. Create run (pending)
    │ 4. Lookup runner bound to blueprint
    ▼
Runner (deterministic)
    │
    │ Claims run
    │ Starts Runner Gateway (proxy)
    │ Builds invocation payload with gateway_url
    │ Spawns: ao-deterministic-exec < payload
    ▼
ao-deterministic-exec
    │
    │ 1. Build CLI args from parameters
    │ 2. Execute: python -m crawler.main --url ... --depth ...
    │ 3. Capture stdout/stderr
    │ 4. Send result event via session_client.add_event()
    │    POST /events → Runner Gateway → Coordinator
    │ 5. Exit with subprocess exit code
    ▼
Runner (RunSupervisor)
    │
    │ Detects executor exit
    │ POST /runner/runs/{id}/completed (or /failed)
    ▼
Coordinator
    │
    │ Session status = completed
    │ Extracts result from result event
    │ Triggers callback (if async_callback mode)
    │ Callback includes structured result
    ▼
AI Agent (resumes with structured result)
```

---

## FAQ

**Q: Can a deterministic agent call another deterministic agent?**
A: Yes. Same mechanism - use `start_agent_session` with `mode="sync"`.

**Q: What if the deterministic script needs environment variables?**
A: Pass via `metadata` in blueprint or run request. Executor sets them before subprocess.

**Q: How do I test a deterministic agent locally?**
A: Run the command directly with CLI args. The executor is just a thin wrapper.

**Q: Can I mix AI and deterministic in the same runner?**
A: No. Each runner runs one executor type. Run separate runners for different executor types.
