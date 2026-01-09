# Phase 4: Procedural Executor Implementation Plan

## Overview

Implement the procedural executor (`ao-procedural-exec`) that executes CLI commands with structured parameters, along with runner-side agent loading and coordinator registration.

**Design Reference:** `docs/design/deterministic-agents-phase-4-deterministic-executor.md`

---

## Prerequisites - Required Reading

Before implementing, read these files to understand the patterns:

**Executor pattern (Block 1):**
- `servers/agent-runner/executors/test-executor/ao-test-exec` - Simple executor reference (follow this pattern)
- `servers/agent-runner/lib/invocation.py` - ExecutorInvocation schema (stdin parsing)
- `servers/agent-runner/lib/session_client.py` - bind() and add_event() API

**Profile and agent loading (Block 2):**
- `servers/agent-runner/lib/executor.py` - ExecutorProfile dataclass, load_profile()
- `servers/agent-runner/agent-runner` - Runner registration flow (search for `register`)

**Coordinator storage and API (Blocks 3-5):**
- `servers/agent-coordinator/database.py` - Table creation pattern, existing methods
- `servers/agent-coordinator/main.py` - Registration endpoint (~line 908), agent endpoints (~line 677)
- `servers/agent-coordinator/models.py` - Pydantic model patterns

**Integration tests (Block 9):**
- `tests/integration/11-result-event-emission.md` - Test case format example
- `tests/README.md` - Test framework overview

---

## Implementation Blocks

### Block 1: Agent Runner - Procedural Executor

**Files to create:**
- `servers/agent-runner/executors/procedural/ao-procedural-exec` - Main executor script
- `servers/agent-runner/profiles/procedural.json` - Executor profile

**Implementation:**

1. **Create profile** (`profiles/procedural.json`):
   ```json
   {
     "type": "procedural",
     "command": "executors/procedural/ao-procedural-exec",
     "config": {},
     "agents_dir": "./agents/procedural"
   }
   ```

   **Profile schema extension:**
   - `agents_dir` (optional): Path to directory containing agent definition JSON files
   - If set, runner loads agents from this directory and registers them with coordinator
   - If not set, no runner-owned agents are loaded
   - Path is relative to the `agent-runner` directory (or absolute)
   - This property is executor-type agnostic (works for procedural, future autonomous, etc.)

   ---

   **Minimal Example: Echo Profile**

   This example demonstrates the full coupling between profile, agent, and script.
   All three are created by the same person and bundled together.

   **Files to create:**
   - `servers/agent-runner/profiles/echo.json` - Echo profile
   - `servers/agent-runner/agents/echo/echo.json` - Echo agent definition
   - `servers/agent-runner/scripts/echo/echo` - Echo script

   **a) Profile** (`profiles/echo.json`):
   ```json
   {
     "type": "procedural",
     "command": "executors/procedural/ao-procedural-exec",
     "config": {},
     "agents_dir": "./agents/echo"
   }
   ```

   **b) Agent definition** (`agents/echo/echo.json`):
   ```json
   {
     "name": "echo",
     "description": "Simple echo agent that returns the input message as JSON",
     "command": "scripts/echo/echo",
     "parameters_schema": {
       "type": "object",
       "required": ["message"],
       "properties": {
         "message": {
           "type": "string",
           "description": "The message to echo back"
         }
       },
       "additionalProperties": false
     }
   }
   ```

   **c) Script** (`scripts/echo/echo`):
   ```bash
   #!/bin/bash
   # Echo script - accepts --message parameter and echoes it back as JSON
   # Only accepts --message to demonstrate strict parameter matching.
   #
   # Usage: ./echo --message "hello world"
   # Output: {"message": "hello world"}

   message=""

   while [[ $# -gt 0 ]]; do
     case $1 in
       --message)
         message="$2"
         shift 2
         ;;
       *)
         echo "Error: Unknown parameter: $1" >&2
         exit 1
         ;;
     esac
   done

   if [[ -z "$message" ]]; then
     echo "Error: --message parameter is required" >&2
     exit 1
   fi

   # Output as JSON
   echo "{\"message\": \"$message\"}"
   ```

   **Why strict parameter matching?**
   - Demonstrates the coupling between schema and script
   - Provides test case for invalid parameters (script rejects unknown args)
   - Shows that `additionalProperties: false` in schema + script validation = robust contract

   **Coupling demonstrated:**
   ```
   Profile (echo.json)
      │
      ├─→ agents_dir: "./agents/echo"
      │       │
      │       └─→ Agent (echo.json)
      │               │
      │               ├─→ command: "scripts/echo/echo"
      │               │       │
      │               │       └─→ Script (echo) - accepts ONLY --message
      │               │
      │               └─→ parameters_schema - defines message (required)
      │                       │
      │                       └─→ MUST match what script accepts!
      │
      └─→ command: "executors/procedural/ao-procedural-exec"
              │
              └─→ Procedural executor - builds CLI args from parameters
   ```

   ---

2. **Create executor** (`executors/procedural/ao-procedural-exec`):
   - Use `uv run --script` shebang pattern (from claude-code reference)
   - Parse `ExecutorInvocation.from_stdin()` for JSON payload
   - Call `session_client.bind()` to register with coordinator:
     - `executor_session_id` is **required** by the gateway (returns 400 if missing)
     - For autonomous agents: this is the framework's session ID (used for resume affinity)
     - For procedural agents: no resume, so generate a UUID or use `session_id` as the value
     - This also records `hostname` and `executor_profile` on the session for observability
   - Extract `command` field from `agent` (new field for procedural agents)
   - **Resolve command path** relative to runner directory (where agent-runner is started)
   - Build CLI arguments from `parameters` dict
   - Execute subprocess:
     - **Working directory**: `project_dir` from invocation
     - Capture stdout/stderr
   - Send `result` event via `session_client.add_event()`:
     - `result_text`: raw stdout
     - `result_data`: parsed JSON if stdout is valid JSON, else null
   - Exit with subprocess exit code

3. **CLI argument building:**

   Parameters are passed to the subprocess as command-line arguments:
   - Each parameter property name becomes `--{property_name}`
   - Each property value becomes the argument value
   - Since subprocess.Popen uses a list of arguments (not shell string), no bash escaping is needed - Python handles argument passing correctly

   ```python
   import shlex

   def build_cli_args(command: str, parameters: dict) -> list[str]:
       # Use shlex.split to properly handle quoted strings in command
       args = shlex.split(command)

       for key, value in parameters.items():
           if isinstance(value, bool):
               # Boolean true → --flag (flag present)
               # Boolean false → flag absent (skip)
               if value:
                   args.append(f"--{key}")
           elif isinstance(value, list):
               # List → --key item1,item2,item3
               args.extend([f"--{key}", ",".join(str(v) for v in value)])
           else:
               # String/number → --key value
               args.extend([f"--{key}", str(value)])

       return args
   ```

   **Example:**
   ```python
   # Command: "python -m crawler.main"
   # Parameters: {"url": "https://example.com", "depth": 2, "verbose": true}
   # Result: ["python", "-m", "crawler.main", "--url", "https://example.com", "--depth", "2", "--verbose"]
   ```

   **Subprocess execution (no shell):**
   ```python
   # Resolve command path relative to runner directory
   runner_dir = Path(__file__).parent.parent.parent  # executors/procedural/ -> agent-runner/
   command_path = runner_dir / args[0]
   args[0] = str(command_path)

   process = subprocess.Popen(
       args,  # List of arguments - no shell escaping needed
       cwd=invocation.project_dir,  # Working directory from invocation
       stdin=subprocess.PIPE,
       stdout=subprocess.PIPE,
       stderr=subprocess.PIPE,
       text=True,
   )
   stdout, stderr = process.communicate()
   ```

---

### Block 2: Agent Runner - Agent Loading & Registration

**Files to modify:**
- `servers/agent-runner/agent-runner` - Main runner script
- `servers/agent-runner/lib/executor.py` - Add agent loading, extend ExecutorProfile

**Implementation:**

1. **Extend `ExecutorProfile`** in `executor.py`:
   ```python
   @dataclass
   class ExecutorProfile:
       name: str
       type: str
       command: str
       config: dict[str, Any]
       agents_dir: Optional[str] = None  # NEW - path to agents directory (runner-local, NOT sent to coordinator)

       def to_dict(self) -> dict[str, Any]:
           """Convert to dictionary for registration payload.

           Note: agents_dir is intentionally excluded - it's runner-local.
           Loaded agents are sent separately in registration.
           """
           return {
               "type": self.type,
               "command": self.command,
               "config": self.config,
               # agents_dir NOT included - runner-local property
           }
   ```

2. **Update `load_profile()`** to read `agents_dir`:
   ```python
   return ExecutorProfile(
       name=name,
       type=profile["type"],
       command=profile["command"],
       config=profile.get("config", {}),
       agents_dir=profile.get("agents_dir"),  # NEW
   )
   ```

3. **Create agent loader** in `executor.py`:
   ```python
   def load_agents_from_profile(profile: ExecutorProfile) -> list[dict]:
       """Load agents from profile's agents_dir if specified."""
       if not profile.agents_dir:
           return []

       # Resolve path relative to agent-runner directory
       agents_dir = Path(profile.agents_dir)
       if not agents_dir.is_absolute():
           agents_dir = get_runner_dir() / agents_dir

       agents = []
       if agents_dir.exists():
           for path in agents_dir.glob("*.json"):
               with open(path) as f:
                   agent = json.load(f)
                   agents.append(agent)
       return agents
   ```

4. **Extend registration** in `Runner.register()`:

   First, update `api_client.register()` signature to accept agents:
   ```python
   def register(
       self,
       hostname: str,
       project_dir: str,
       executor_profile: str,
       executor: dict,
       tags: Optional[list[str]] = None,
       require_matching_tags: bool = False,
       agents: Optional[list[dict]] = None,  # NEW - loaded agents (not the path!)
   ) -> RegistrationResponse:
   ```

   Then update `Runner.register()` to pass loaded agents:
   ```python
   def register(self) -> None:
       # ... existing code ...

       # Load agents from profile (agents_dir is runner-local)
       agents = []
       if self.config.profile:
           agents = load_agents_from_profile(self.config.profile)

       response = self.api_client.register(
           hostname=self._hostname,
           project_dir=self.config.project_dir,
           executor_profile=self._executor_profile,
           executor=executor,  # from profile.to_dict() - does NOT include agents_dir
           tags=self.config.tags,
           require_matching_tags=self.config.require_matching_tags,
           agents=agents if agents else None,  # NEW - loaded agents sent here
       )
   ```

   **Registration payload** sent to coordinator:
   ```python
   {
       "hostname": "my-host",
       "project_dir": "/path/to/project",
       "executor_profile": "procedural",
       "executor": {"type": "procedural", "command": "...", "config": {}},
       "tags": [...],
       "require_matching_tags": false,
       "agents": [  # NEW - actual agent data, NOT the agents_dir path
           {
               "name": "web-crawler",
               "description": "...",
               "command": "python -m crawler.main",
               "parameters_schema": {...}
           }
       ]
   }
   ```

---

### Block 3: Agent Coordinator - Runner Agent Storage

**Files to modify:**
- `servers/agent-coordinator/database.py` - Add runner_agents table
- `servers/agent-coordinator/models.py` - Add RunnerAgent model

**Implementation:**

1. **Add table** in `database.py`:
   ```sql
   CREATE TABLE IF NOT EXISTS runner_agents (
       name TEXT NOT NULL,
       runner_id TEXT NOT NULL REFERENCES runners(runner_id),
       description TEXT,
       command TEXT NOT NULL,
       parameters_schema TEXT,
       created_at TEXT NOT NULL,
       PRIMARY KEY (name, runner_id)
   )
   ```

2. **Add model** in `models.py`:
   ```python
   class RunnerAgent(BaseModel):
       name: str
       description: Optional[str] = None
       command: str
       parameters_schema: Optional[dict] = None
   ```

3. **Add database methods:**
   - `store_runner_agents(runner_id, agents: list[RunnerAgent])`
   - `get_runner_agents(runner_id) -> list[RunnerAgent]`
   - `delete_runner_agents(runner_id)` - Called on runner deregistration
   - `get_runner_agent_by_name(name) -> Optional[tuple[RunnerAgent, runner_id]]`

---

### Block 4: Agent Coordinator - Registration & Agent Discovery

**Files to modify:**
- `servers/agent-coordinator/main.py` - Registration endpoint, agent listing

**Implementation:**

1. **Update `RunnerRegisterRequest`** (lines ~859-874):
   ```python
   class RunnerRegisterRequest(BaseModel):
       hostname: str
       project_dir: str
       executor_profile: str
       executor: Optional[dict] = None
       tags: Optional[list[str]] = None
       require_matching_tags: bool = False
       agents: Optional[list[RunnerAgent]] = None  # NEW
   ```

2. **Update `register_runner()` endpoint** (lines ~908-961):
   - After runner registration, call `store_runner_agents(runner_id, request.agents)`
   - On re-registration (stale runner), replace agents

3. **Update agent listing** to include runner-owned agents:
   - `GET /agents` should query both file-based and runner-owned agents
   - Runner-owned agents have `type: "procedural"` and include `command` field
   - Add `runner_id` field to response for runner-owned agents

4. **Update `get_agent()` endpoint**:
   - Check file-based agents first
   - Fall back to runner_agents table
   - Return 404 if not found in either

5. **On runner deregistration/disconnect:**
   - Call `delete_runner_agents(runner_id)`
   - Clean up associated agents

---

### Block 5: Agent Coordinator - Run Dispatch

**Files to modify:**
- `servers/agent-coordinator/services/run_queue.py`
- `servers/agent-coordinator/main.py` - Run creation

**Implementation:**

1. **Update run creation** (`POST /runs`):
   - If `agent_name` refers to a runner-owned agent:
     - Fetch agent to get bound `runner_id`
     - Add `runner_id` as mandatory demand (affinity)
     - Include `command` in run data

2. **Update run model** if needed:
   - Ensure `command` can be stored/retrieved for procedural runs

3. **Update invocation building** in runner:
   - When claiming a procedural run, include `command` in invocation payload
   - Executor receives `command` via `agent.command`

---

### Block 6: Invocation Schema Extension

**Files to modify:**
- `servers/agent-runner/lib/invocation.py`

**Implementation:**

1. **Add validation** for procedural mode:
   - Reject `mode: "resume"` for procedural agents (stateless)
   - Error: "Procedural agents do not support resumption"

2. **Document** that `agent.command` is required for procedural executors

---

### Block 7: Dashboard Frontend

**Files to modify:**
- `dashboard/src/components/features/agents/AgentEditor.tsx`
- `dashboard/src/components/features/runs/RunDetailPanel.tsx`
- `dashboard/src/types/agent.ts`

**Implementation:**

1. **AgentEditor.tsx** - Add `command` field:
   - Show `command` input when `type === "procedural"`
   - Label: "Command" with helper text "CLI command to execute (e.g., python -m crawler.main)"
   - Only visible for procedural agents

2. **RunDetailPanel.tsx** - Display structured results:
   - Add section for `result_data` display (formatted JSON)
   - Show `exit_code` for procedural runs
   - Differentiate between `result_text` and `result_data`

3. **Update types** if needed:
   - Ensure `Agent` type includes `command: string | null`

---

### Block 8: Chat-UI Frontend

**Files to modify:**
- `interfaces/chat-ui/src/types/index.ts`
- `interfaces/chat-ui/src/contexts/ChatContext.tsx`
- `interfaces/chat-ui/src/components/ChatMessage.tsx`

**Implementation:**

1. **Update types** (`types/index.ts`):
   - Add `command` field to Agent interface
   - Ensure result event handling includes `result_data`

2. **ChatContext.tsx** - Handle result events:
   - Extract `result_data` from result events
   - Store structured data for display

3. **ChatMessage.tsx** - Display structured results:
   - For procedural agents, show `result_data` as formatted JSON
   - Show `exit_code` status

---

### Block 9: Integration Tests

**Files to create:**
- `tests/integration/17-procedural-run-basic.md`
- `tests/integration/18-procedural-run-dispatch.md`
- `tests/integration/19-procedural-resume-rejected.md`

**Test cases:**

1. **17-procedural-run-basic.md** - Basic procedural execution:
   - Start runner with procedural profile (profile has `agents_dir` pointing to test agents)
   - Verify runner registration includes agents
   - Create run for procedural agent
   - Verify result event with `result_data`

2. **18-procedural-run-dispatch.md** - Run routing:
   - Start two runners: one with procedural profile (has agents), one with claude-code profile (no agents)
   - Create run for procedural agent
   - Verify run claimed by correct runner (the one with the agent)

3. **19-procedural-resume-rejected.md** - Resume rejection:
   - Create run for procedural agent
   - Attempt resume
   - Verify 400 error: "Procedural agents do not support resumption"

---

## Implementation Order

1. **Block 3** - Database schema (foundation)
2. **Block 4** - Coordinator registration (enable agent storage)
3. **Block 2** - Runner agent loading & registration
4. **Block 6** - Invocation schema validation
5. **Block 5** - Run dispatch routing
6. **Block 1** - Procedural executor
7. **Block 7** - Dashboard UI
8. **Block 8** - Chat-UI
9. **Block 9** - Integration tests

---

## Key Files Summary

| Component | File | Change |
|-----------|------|--------|
| Runner | `servers/agent-runner/executors/procedural/ao-procedural-exec` | CREATE |
| Runner | `servers/agent-runner/profiles/procedural.json` | CREATE (with `agents_dir` property) |
| Runner | `servers/agent-runner/agents/procedural/` | CREATE - Directory for procedural agent definitions |
| Runner | `servers/agent-runner/profiles/echo.json` | CREATE - Minimal example profile |
| Runner | `servers/agent-runner/agents/echo/echo.json` | CREATE - Echo agent definition |
| Runner | `servers/agent-runner/scripts/echo/echo` | CREATE - Echo script (bash) |
| Runner | `servers/agent-runner/agent-runner` | MODIFY - Agent loading from profile |
| Runner | `servers/agent-runner/lib/executor.py` | MODIFY - Add `agents_dir` to ExecutorProfile, add `load_agents_from_profile()` |
| Runner | `servers/agent-runner/lib/invocation.py` | MODIFY - Validation |
| Coordinator | `servers/agent-coordinator/database.py` | MODIFY - runner_agents table |
| Coordinator | `servers/agent-coordinator/models.py` | MODIFY - RunnerAgent model |
| Coordinator | `servers/agent-coordinator/main.py` | MODIFY - Registration, agent listing |
| Coordinator | `servers/agent-coordinator/services/run_queue.py` | MODIFY - Dispatch routing |
| Dashboard | `dashboard/src/components/features/agents/AgentEditor.tsx` | MODIFY - Command field |
| Dashboard | `dashboard/src/components/features/runs/RunDetailPanel.tsx` | MODIFY - Result display |
| Chat-UI | `interfaces/chat-ui/src/contexts/ChatContext.tsx` | MODIFY - Result handling |
| Chat-UI | `interfaces/chat-ui/src/components/ChatMessage.tsx` | MODIFY - Result display |
| Tests | `tests/integration/17-procedural-run-basic.md` | CREATE |
| Tests | `tests/integration/18-procedural-run-dispatch.md` | CREATE |
| Tests | `tests/integration/19-procedural-resume-rejected.md` | CREATE |

---

## Verification

1. **Unit tests:**
   - Agent loading from profile's `agents_dir`
   - Profile loading with and without `agents_dir`
   - CLI argument building with various parameter types
   - Resume rejection for procedural agents

2. **Integration tests:**
   - `/tests:setup` with procedural profile
   - `/tests:case 17-procedural-run-basic`
   - `/tests:case 18-procedural-run-dispatch`
   - `/tests:case 19-procedural-resume-rejected`

3. **Manual verification using echo example:**
   ```bash
   # Start coordinator
   cd servers/agent-coordinator && AUTH_ENABLED=false uv run python -m main

   # The echo example files should already exist (created as part of implementation):
   # - profiles/echo.json (profile with agents_dir: "./agents/echo")
   # - agents/echo/echo.json (agent definition)
   # - scripts/echo/echo (bash script)

   # Make echo script executable
   chmod +x servers/agent-runner/scripts/echo/echo

   # Start runner with echo profile (agents loaded from profile's agents_dir)
   ./servers/agent-runner/agent-runner -x echo

   # Verify registration
   curl http://localhost:8765/runners | jq

   # Verify agent listing (should include "echo" agent)
   curl http://localhost:8765/agents | jq

   # Create and execute run
   curl -X POST http://localhost:8765/runs \
     -H "Content-Type: application/json" \
     -d '{"agent_name":"echo","parameters":{"message":"Hello World"}}'

   # Expected result_data: {"message": "Hello World"}

   # Test invalid parameter (should fail at script level)
   curl -X POST http://localhost:8765/runs \
     -H "Content-Type: application/json" \
     -d '{"agent_name":"echo","parameters":{"message":"Hello","unknown":"param"}}'

   # Expected: exit code 1, stderr: "Error: Unknown parameter: --unknown"
   ```

---

## Notes

- **No backwards compatibility needed** - Database will be dropped, all clients in monorepo
- **Agent ownership** - Runner-owned agents are deleted when runner deregisters
- **Profile-based agent loading** - Agents are loaded from the profile's `agents_dir` property, not from a CLI flag. This couples agents to the profile, ensuring the person who configures the executor also controls which agents are available.
- **`agents_dir` is executor-type agnostic** - While initially used for procedural agents, the `agents_dir` profile property will support future executor types (e.g., autonomous agents)
- **Command field** - Only present for procedural agents (specifies CLI command to execute)
