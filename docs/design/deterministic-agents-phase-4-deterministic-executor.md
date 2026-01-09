# Phase 4: Deterministic Executor

**Status:** Implementation Ready
**Depends on:** Phase 1, 2, 3 (Unified model foundation)
**Design Reference:** [deterministic-agents-implementation.md](./deterministic-agents-implementation.md) - Sections 1, 9, 10

---

## Objective

Create the deterministic executor (`ao-deterministic-exec`) that executes CLI commands with structured parameters. Implement runner-side blueprint loading and registration with the coordinator.

**End state:** Deterministic agents can be registered, discovered, and executed through the same orchestration infrastructure as AI agents.

---

## Key Components

### 1. Deterministic Executor

**Location:** `servers/agent-runner/executors/deterministic/ao-deterministic-exec`

**Responsibilities:**
- Parse invocation from stdin (same pattern as claude-code executor)
- Build CLI arguments from `parameters`
- Execute subprocess with captured stdout/stderr
- Send `result` event via `session_client.add_event()`
- Exit with subprocess exit code

**Invocation schema:**
```json
{
  "schema_version": "2.2",
  "mode": "start",
  "session_id": "ses_abc123",
  "parameters": {
    "url": "https://example.com",
    "depth": 2
  },
  "command": "python -m crawler.main",
  "project_dir": "/path/to/project",
  "gateway_url": "http://127.0.0.1:8766"
}
```

**Key differences from claude-code:**
- Uses `command` + `parameters` instead of `prompt`
- No `agent_blueprint` with system_prompt/mcp_servers
- No resume support (deterministic agents are stateless)
- Simpler lifecycle: run command, capture output, report result

**Reference:** See [ao-claude-code-exec](../../servers/agent-runner/executors/claude-code/ao-claude-code-exec) for pattern.

### 2. Invocation Schema Extension

**File:** `servers/agent-runner/lib/invocation.py`

Add deterministic-specific fields to `ExecutorInvocation`:
- `command: Optional[str]` - CLI command to execute
- Mode validation: `"resume"` rejected for deterministic

Create separate validation path or discriminated union based on executor type.

### 3. Blueprint Loading

**File:** `servers/agent-runner/` (new module or extend existing)

**Blueprint file location:**
```
~/.agent-runner/blueprints/
├── web-crawler.json
└── db-backup.json
```

**Blueprint format:**
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

**Runner startup:**
1. Read `--blueprints-dir` CLI flag (default: `~/.agent-runner/blueprints`)
2. Load all `*.json` files from directory
3. Include blueprints in registration payload

### 4. Runner Registration

**File:** `servers/agent-runner/agent-runner` (main binary)

Extend registration payload:
```json
{
  "hostname": "crawler-host",
  "executor_type": "deterministic",
  "executor_profile": "deterministic",
  "blueprints": [
    {
      "name": "web-crawler",
      "description": "...",
      "command": "python -m crawler.main",
      "parameters_schema": { ... }
    }
  ]
}
```

**File:** `servers/agent-coordinator/main.py`
- `register_runner()` (lines 904-952): Accept `blueprints` array
- Store blueprints bound to `runner_id`
- Set `type: "procedural"` for these blueprints

### 5. Coordinator Blueprint Storage

**File:** `servers/agent-coordinator/database.py`

Store runner-owned blueprints:
- Link blueprint to `runner_id`
- Include `command` field (for deterministic only)
- On runner disconnect: Delete bound blueprints

**Table structure:**
```
blueprints:
  - name (TEXT, PRIMARY KEY with runner_id)
  - runner_id (TEXT, FOREIGN KEY → runners)
  - type (TEXT: "autonomous" | "procedural")
  - description (TEXT)
  - command (TEXT, nullable - deterministic only)
  - parameters_schema (TEXT, JSON)
```

### 6. Run Dispatch

**File:** `servers/agent-coordinator/services/run_queue.py`

Route deterministic runs to correct runner:
- Lookup blueprint by name
- Get bound `runner_id`
- Add runner constraint to run demands

### 7. Invocation Building

**File:** `servers/agent-runner/` (run handler)

When claiming a deterministic run:
1. Fetch blueprint config (including `command`)
2. Build invocation payload with `command` and `parameters`
3. Spawn `ao-deterministic-exec` with payload on stdin

---

## CLI Argument Building

The executor converts `parameters` to CLI arguments:

```python
def build_cli_args(command: str, parameters: dict) -> list[str]:
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
```

**Example:**
```python
build_cli_args("python -m crawler.main", {"url": "https://x.com", "depth": 2})
# → ["python", "-m", "crawler.main", "--url", "https://x.com", "--depth", "2"]
```

---

## Result Event

The executor sends a `result` event after execution:

```json
{
  "event_type": "result",
  "session_id": "ses_abc123",
  "timestamp": "2026-01-08T12:00:00Z",
  "result_type": "procedural",
  "result_text": "raw stdout output",
  "result_data": { "pages_crawled": 42 },
  "exit_code": 0
}
```

- `result_text`: Always raw stdout
- `result_data`: Parsed JSON if stdout is valid JSON, otherwise null
- `exit_code`: Process exit code (0 = success)

---

## Files to Create

| File | Purpose |
|------|---------|
| `servers/agent-runner/executors/deterministic/ao-deterministic-exec` | Main executor script |
| `servers/agent-runner/profiles/deterministic.json` | Executor profile |

## Files to Modify

| File | Change |
|------|--------|
| `servers/agent-runner/lib/invocation.py` | Add `command` field, deterministic validation |
| `servers/agent-runner/agent-runner` | Blueprint loading, registration payload |
| `servers/agent-coordinator/main.py` | Accept blueprints in registration |
| `servers/agent-coordinator/database.py` | Blueprint storage table |
| `servers/agent-coordinator/services/run_queue.py` | Route to bound runner |

---

## Acceptance Criteria

1. **Blueprint loading:**
   - Runner reads `*.json` from blueprints directory
   - Blueprints included in registration payload

2. **Blueprint registration:**
   - Coordinator stores blueprints bound to runner
   - Agent list includes deterministic agents with schema

3. **Run creation:**
   ```bash
   curl -X POST /runs -d '{
     "agent_name": "web-crawler",
     "parameters": {"url": "https://example.com", "depth": 2}
   }'
   # Returns: 201 Created
   ```

4. **Run dispatch:**
   - Run routed to runner that owns the blueprint
   - Other runners cannot claim the run

5. **Execution:**
   - Executor receives invocation with `command` and `parameters`
   - Subprocess executed with CLI arguments
   - Result event stored with `result_type: "procedural"`

6. **Callback works:**
   - Parent agent receives callback with structured result
   - `result_data` accessible if stdout was JSON

7. **Resume rejected:**
   ```bash
   curl -X POST /runs -d '{"agent_name": "web-crawler", "mode": "resume", ...}'
   # Returns: 400 "Deterministic agents do not support resumption"
   ```

---

## Testing Strategy

1. Unit test blueprint loading from directory

2. Unit test CLI argument building with various parameter types

3. Integration test runner registration with blueprints

4. Integration test run routing to correct runner

5. End-to-end test: Create deterministic run → executor runs → result stored → callback delivered

6. Test with real CLI tool (e.g., simple Python script that echoes JSON)

---

## Example Deterministic Agent

Create a test agent for verification:

**File:** `~/.agent-runner/blueprints/echo-json.json`
```json
{
  "name": "echo-json",
  "description": "Echoes parameters as JSON (for testing)",
  "command": "python -c \"import sys, json; print(json.dumps(json.loads(sys.stdin.read())))\"",
  "parameters_schema": {
    "type": "object",
    "properties": {
      "message": { "type": "string" },
      "count": { "type": "integer" }
    }
  }
}
```

---

## References

- [ao-claude-code-exec](../../servers/agent-runner/executors/claude-code/ao-claude-code-exec) - Pattern reference
- [invocation.py](../../servers/agent-runner/lib/invocation.py) - Invocation schema
- [deterministic-agents-implementation.md](./deterministic-agents-implementation.md) - Sections 1, 9, 10
- [ADR-002](../adr/ADR-002-agent-runner-architecture.md) - Runner architecture
