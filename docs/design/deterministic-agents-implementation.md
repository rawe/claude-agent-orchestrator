# Deterministic Agents Implementation Guide

**Status:** Implementation Reference
**Date:** 2026-01-08
**References:**
- [deterministic-task-execution.md](./deterministic-task-execution.md) - Original design concepts
- [unified-task-model-overview.md](./unified-task-model-overview.md) - Unified invocation model
- [ADR-003](../adr/ADR-003-callback-based-async.md) - Callback-based async
- [ADR-011](../adr/ADR-011-runner-capabilities-and-run-demands.md) - Runner capabilities

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

### 2. Calling Deterministic Agents from AI Agents

AI agents call deterministic agents using the **same MCP tool** (`start_agent_session`), but with `parameters` instead of `prompt`:

```python
# AI agent calls deterministic agent
start_agent_session(
    agent_name="web-crawler",
    parameters={"url": "https://example.com", "depth": 3},
    mode="async_callback"  # Callback when done
)
```

**The AI agent doesn't know or care that it's calling a deterministic task.** The MCP server routes based on agent type.

**Schema discovery for AI orchestrators:**
```python
# AI fetches schema before calling
schema = get_agent_schema("web-crawler")
# Returns: { parameters_schema: {...}, type: "deterministic" }

# AI uses this to construct valid parameters
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

### 5. Creating the Deterministic Executor

Create a new executor following the existing pattern:

```
servers/agent-runner/executors/
├── claude-code/                    # AI agent executor (existing)
│   └── ao-claude-code-exec
└── deterministic/                  # Deterministic executor (new)
    └── ao-deterministic-exec
```

**Implementation: `ao-deterministic-exec`**

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///

import json
import subprocess
import sys
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

    # Build CLI arguments from parameters
    args = build_cli_args(inv.command, inv.parameters)

    # Execute command
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        cwd=inv.project_dir
    )

    # Report result to coordinator
    client = SessionClient(inv.api_url)

    if result.returncode == 0:
        client.complete_session(
            session_id=inv.session_id,
            result_text=result.stdout,
            exit_code=0
        )
    else:
        client.fail_session(
            session_id=inv.session_id,
            error=result.stderr or f"Exit code: {result.returncode}",
            result_text=result.stdout
        )

    # Print result to stdout (for runner)
    print(result.stdout)


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

### 6. Runner Configuration for Deterministic Agents

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

## Implementation Tasks

### Phase 1: Executor and Runner

1. **Create `ao-deterministic-exec`**
   - Parse invocation from stdin
   - Build CLI args from parameters
   - Execute subprocess
   - Report result to coordinator
   - Location: `servers/agent-runner/executors/deterministic/`

2. **Add blueprint loading to runner**
   - Read `*.json` from blueprints directory
   - Include in registration payload
   - Add `--blueprints-dir` CLI flag

3. **Create deterministic profile**
   - Location: `servers/agent-runner/profiles/deterministic.json`
   - Set executor command and blueprints_dir

### Phase 2: Coordinator

4. **Store runner-bound blueprints**
   - Add `blueprints` table: `name, runner_id, config_json`
   - Insert on registration, delete on runner disconnect
   - Handle name collisions with `name@runner_id` suffix

5. **Add `type` field to agents list**
   - Return `type: "agent"` or `type: "deterministic"`
   - Return `has_schema: true` for deterministic agents

6. **Add schema endpoint**
   - `GET /agents/{name}/schema`
   - Returns `parameters_schema` for deterministic agents

### Phase 3: Run Dispatch

7. **Route runs to correct runner**
   - Deterministic runs only go to runner that owns the blueprint
   - Use `runner_id` from blueprint binding

8. **Validate parameters on run creation**
   - Fetch `parameters_schema` from blueprint
   - Validate `parameters` against schema
   - Return 400 if invalid

### Phase 4: MCP Integration

9. **Update `start_agent_session` MCP tool**
   - Accept `parameters` as alternative to `prompt`
   - Detect agent type from coordinator
   - Route to appropriate endpoint

---

## Result Model

Deterministic agents produce:

```json
{
  "result_text": "...raw stdout...",
  "exit_code": 0
}
```

**During execution:** stderr lines streamed as events to coordinator (real-time progress).

**On completion:** stdout captured as `result_text`.

**For structured output (future):** Parse stdout as JSON, validate against `output_schema`.

---

## Flow Diagram

```
AI Agent (orchestrator)
    │
    │ start_agent_session("web-crawler", parameters={...})
    ▼
MCP Server
    │
    │ Detects: agent type = deterministic
    │ POST /runs { agent_name, parameters, mode }
    ▼
Coordinator
    │
    │ 1. Validate parameters against schema
    │ 2. Create run (pending)
    │ 3. Lookup runner bound to blueprint
    ▼
Runner (deterministic)
    │
    │ Claims run
    │ Builds invocation payload
    │ Spawns: ao-deterministic-exec < payload
    ▼
ao-deterministic-exec
    │
    │ 1. Build CLI args from parameters
    │ 2. Execute: python -m crawler.main --url ... --depth ...
    │ 3. Capture stdout/stderr
    │ 4. Report completion to coordinator
    ▼
Coordinator
    │
    │ Session status = completed
    │ Triggers callback (if async_callback mode)
    ▼
AI Agent (resumes with result)
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
