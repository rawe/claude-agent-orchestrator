# ADR-014: Deterministic Task Execution

**Status:** Proposed
**Date:** 2025-12-31
**Decision Makers:** Architecture Review

## Context

### Current State

The Agent Runner currently only supports AI agent execution:
- Receives a **prompt** (free-form text)
- Executes an **AI agent** (Claude Code) that interprets the prompt
- Agent behavior is **non-deterministic** (AI makes decisions)

### The Need for Deterministic Tasks

Many orchestration scenarios require executing deterministic programs alongside AI agents:

| Task Type | Example | Behavior |
|-----------|---------|----------|
| **AI Agent** | "Research the Python async ecosystem" | Non-deterministic, exploratory |
| **Deterministic** | "Crawl https://example.com with depth=2" | Deterministic, parameter-driven |

**Real-world examples of deterministic tasks:**
- Web crawling with specific parameters (URL, depth, patterns)
- Database operations (backup, migration, queries)
- File processing pipelines (conversion, compression, aggregation)
- API integrations (fetch data, sync records)
- Test execution (run specific test suites)
- Build/deployment automation
- Data extraction and transformation

### The Integration Challenge

When an orchestrating agent wants to invoke a deterministic task:

```
Current AI Agent Invocation:
┌────────────────────────────────────────────────────────────────┐
│  start_agent_session(                                          │
│      agent_name="web-researcher",                              │
│      prompt="Research Python async frameworks"                 │
│  )                                                             │
└────────────────────────────────────────────────────────────────┘
         ↓
    AI agent receives prompt, interprets it, decides what to do

Desired Deterministic Invocation:
┌────────────────────────────────────────────────────────────────┐
│  start_agent_session(                                          │
│      agent_name="web-crawler",                                 │
│      parameters={                                              │
│          "url": "https://docs.python.org",                     │
│          "depth": 2,                                           │
│          "patterns": ["*.html", "*.md"]                        │
│      }                                                         │
│  )                                                             │
└────────────────────────────────────────────────────────────────┘
         ↓
    Deterministic program receives parameters, executes exactly
```

### Key Requirements

1. **Same Lifecycle**: Deterministic tasks must follow the same run lifecycle (pending → claimed → started → completed/failed)
2. **Same Callback System**: Must support async callbacks for orchestration (ADR-003)
3. **Same Demands/Tags**: Must route via runner demands matching (ADR-011)
4. **Same Monitoring**: Status, events, results accessible the same way
5. **Unified Interface**: Orchestrators use the same MCP tools (`start_agent_session`)
6. **Clear Parameters**: Structured parameters instead of free-form prompt

## Decision

### 1. Introduce Blueprint Types

Extend agent blueprints to support a `type` field:

```python
# Blueprint types
BlueprintType = Literal["agent", "deterministic"]

class AgentBlueprint(BaseModel):
    name: str
    description: str
    type: BlueprintType = "agent"  # Default: AI agent
    tags: list[str] = []
    demands: Optional[RunnerDemands] = None

    # For type="agent"
    system_prompt: Optional[str] = None
    mcp_servers: Optional[dict] = None

    # For type="deterministic"
    command: Optional[str] = None           # Command/script to execute
    parameters_schema: Optional[dict] = None # JSON Schema for parameters
    timeout_seconds: Optional[int] = None    # Execution timeout
```

### 2. Deterministic Blueprint Structure

```
config/agents/web-crawler/
├── agent.json              # Metadata with type="deterministic"
├── agent.parameters.json   # JSON Schema for parameters
└── agent.command.sh        # The script/command to execute (or reference)
```

**agent.json (deterministic):**
```json
{
    "name": "web-crawler",
    "description": "Crawls a website to specified depth, extracting links and content",
    "type": "deterministic",
    "tags": ["internal", "web", "crawler"],
    "demands": {
        "tags": ["python", "playwright"]
    },
    "command": "python -m crawler.main",
    "timeout_seconds": 3600
}
```

**agent.parameters.json (JSON Schema):**
```json
{
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["url"],
    "properties": {
        "url": {
            "type": "string",
            "format": "uri",
            "description": "Starting URL to crawl"
        },
        "depth": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "default": 2,
            "description": "Maximum crawl depth"
        },
        "patterns": {
            "type": "array",
            "items": {"type": "string"},
            "default": ["*"],
            "description": "URL patterns to include"
        },
        "output_dir": {
            "type": "string",
            "description": "Output directory for crawled content"
        }
    }
}
```

### 3. Extend Invocation Schema

Update the executor invocation schema (currently 2.0) to support deterministic tasks:

```python
# Schema version 2.1 - Adds deterministic task support
SCHEMA_VERSION = "2.1"

INVOCATION_SCHEMA = {
    # ... existing fields ...
    "properties": {
        "schema_version": {"const": "2.1"},
        "mode": {"enum": ["start", "resume", "execute"]},  # Add "execute" mode

        # Existing fields for agent mode
        "prompt": {"type": "string"},
        "agent_blueprint": {"type": "object"},

        # New fields for deterministic mode
        "task_blueprint": {
            "type": "object",
            "description": "Resolved deterministic task blueprint",
            "properties": {
                "name": {"type": "string"},
                "type": {"const": "deterministic"},
                "command": {"type": "string"},
                "parameters_schema": {"type": "object"},
                "timeout_seconds": {"type": "integer"}
            }
        },
        "parameters": {
            "type": "object",
            "description": "Validated parameters for deterministic execution"
        }
    }
}
```

### 4. New Executor Type: Deterministic Executor

Create a new executor alongside `claude-code`:

```
servers/agent-runner/executors/
├── claude-code/
│   └── ao-claude-code-exec     # AI agent executor
└── deterministic/
    └── ao-deterministic-exec   # Deterministic task executor
```

**ao-deterministic-exec responsibilities:**
1. Parse invocation payload from stdin
2. Validate parameters against schema
3. Execute the command with parameters
4. Capture stdout/stderr
5. Report events to coordinator
6. Report completion/failure status
7. Return structured result

### 5. Parameter Passing Strategies

The deterministic executor supports multiple parameter passing strategies:

```python
class ParameterPassingStrategy(Enum):
    STDIN_JSON = "stdin_json"      # Write parameters as JSON to stdin
    ARGS = "args"                  # Pass as CLI arguments
    ENV = "env"                    # Set as environment variables
    FILE = "file"                  # Write to temp file, pass path
```

**Blueprint specifies strategy:**
```json
{
    "name": "web-crawler",
    "type": "deterministic",
    "command": "python -m crawler.main",
    "parameter_strategy": "stdin_json"
}
```

**Executor implementation:**
```python
def execute_deterministic(invocation: ExecutorInvocation) -> int:
    blueprint = invocation.task_blueprint
    params = invocation.parameters

    if blueprint.parameter_strategy == "stdin_json":
        # Write params as JSON to stdin
        proc = subprocess.Popen(
            blueprint.command.split(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        proc.stdin.write(json.dumps(params).encode())
        proc.stdin.close()

    elif blueprint.parameter_strategy == "args":
        # Convert params to CLI args
        args = []
        for key, value in params.items():
            if isinstance(value, bool) and value:
                args.append(f"--{key}")
            elif isinstance(value, list):
                for item in value:
                    args.extend([f"--{key}", str(item)])
            else:
                args.extend([f"--{key}", str(value)])

        proc = subprocess.Popen(
            blueprint.command.split() + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    # ... handle output, timeout, completion
```

### 6. Unified MCP Tool Interface

The existing `start_agent_session` tool is extended to handle both types:

```python
# MCP Tool: start_agent_session (extended)

def start_agent_session(
    agent_name: str,
    prompt: Optional[str] = None,       # For agent type
    parameters: Optional[dict] = None,  # For deterministic type
    execution_mode: str = "sync",
    additional_demands: Optional[dict] = None
) -> dict:
    """
    Start a new agent or deterministic task session.

    For AI agents (type="agent"):
        - Provide `prompt` with the task description
        - Agent receives system prompt + user prompt

    For deterministic tasks (type="deterministic"):
        - Provide `parameters` matching the task's schema
        - Parameters are validated against the blueprint's JSON Schema

    Args:
        agent_name: Name of the agent/task blueprint
        prompt: (agent type) Task description for AI agent
        parameters: (deterministic type) Structured parameters
        execution_mode: "sync", "async_poll", or "async_callback"
        additional_demands: Extra runner requirements (additive)

    Returns:
        {session_id, run_id, ...}
    """
```

**Orchestrator usage examples:**

```python
# Starting an AI agent
result = start_agent_session(
    agent_name="web-researcher",
    prompt="Research Python async frameworks and compare them",
    execution_mode="async_callback"
)

# Starting a deterministic task
result = start_agent_session(
    agent_name="web-crawler",
    parameters={
        "url": "https://docs.python.org",
        "depth": 2,
        "patterns": ["*.html"]
    },
    execution_mode="async_callback"
)
```

### 7. Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. RUN CREATION (Coordinator)                                               │
│                                                                             │
│  POST /runs {                                                               │
│      agent_name: "web-crawler",                                             │
│      parameters: { url: "...", depth: 2 }                                   │
│  }                                                                          │
│      ↓                                                                      │
│  Coordinator:                                                               │
│    1. Loads blueprint → type="deterministic"                                │
│    2. Validates parameters against parameters_schema                        │
│    3. Generates session_id                                                  │
│    4. Creates run with demands (requires: deterministic executor)           │
│    5. Returns { run_id, session_id }                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. RUNNER CLAIMS (Agent Runner)                                             │
│                                                                             │
│  Runner (executor_type="deterministic") polls for runs                      │
│      ↓                                                                      │
│  Demands match: executor_type="deterministic", tags=["python","playwright"] │
│      ↓                                                                      │
│  Runner claims run, receives:                                               │
│    - session_id, parameters, task_blueprint                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. EXECUTOR SPAWNED (ao-deterministic-exec)                                 │
│                                                                             │
│  {                                                                          │
│      "schema_version": "2.1",                                               │
│      "mode": "execute",                                                     │
│      "session_id": "ses_abc123",                                            │
│      "parameters": { "url": "...", "depth": 2 },                            │
│      "project_dir": "/path/to/project",                                     │
│      "task_blueprint": {                                                    │
│          "name": "web-crawler",                                             │
│          "type": "deterministic",                                           │
│          "command": "python -m crawler.main",                               │
│          "parameters_schema": {...},                                        │
│          "timeout_seconds": 3600                                            │
│      }                                                                      │
│  }                                                                          │
│      ↓                                                                      │
│  Executor:                                                                  │
│    1. Validates parameters (again, defense in depth)                        │
│    2. Spawns command with parameters                                        │
│    3. Streams events to coordinator                                         │
│    4. Captures result/error                                                 │
│    5. Reports completion                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. CALLBACKS (if async_callback mode)                                       │
│                                                                             │
│  Same as AI agents per ADR-003:                                             │
│    - Child session completes                                                │
│    - Coordinator queues notification for parent                             │
│    - Parent agent resumes with child's result                               │
│                                                                             │
│  Result format:                                                             │
│  {                                                                          │
│      "status": "completed",                                                 │
│      "output": {...},           # Structured output from deterministic task │
│      "stdout": "...",           # Captured stdout                           │
│      "stderr": "...",           # Captured stderr                           │
│      "exit_code": 0,                                                        │
│      "duration_seconds": 45.2                                               │
│  }                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8. Runner Configuration for Deterministic Tasks

Runners can be configured to handle deterministic tasks:

```bash
# Agent Runner for AI agents (default)
./agent-runner \
    --executor-path executors/claude-code/ao-claude-code-exec \
    --tags "python,docker"

# Agent Runner for deterministic tasks
./agent-runner \
    --executor-path executors/deterministic/ao-deterministic-exec \
    --tags "python,playwright,crawler"
```

The `executor_type` is derived from the executor path:
- `executors/claude-code/ao-claude-code-exec` → executor_type="claude-code"
- `executors/deterministic/ao-deterministic-exec` → executor_type="deterministic"

### 9. Blueprint Resolution Logic

Update the coordinator's blueprint resolution:

```python
def resolve_blueprint(agent_name: str) -> Blueprint:
    """
    Load and resolve a blueprint, determining if it's an agent or deterministic task.
    """
    agent_dir = Path(AGENTS_DIR) / agent_name

    # Load metadata
    with open(agent_dir / "agent.json") as f:
        metadata = json.load(f)

    blueprint_type = metadata.get("type", "agent")

    if blueprint_type == "agent":
        # Load system prompt
        system_prompt = (agent_dir / "agent.system-prompt.md").read_text()
        # Load MCP config if exists
        mcp_config = load_mcp_config(agent_dir)

        return AgentBlueprint(
            type="agent",
            name=metadata["name"],
            system_prompt=system_prompt,
            mcp_servers=mcp_config,
            **metadata
        )

    elif blueprint_type == "deterministic":
        # Load parameters schema
        params_schema = None
        schema_file = agent_dir / "agent.parameters.json"
        if schema_file.exists():
            with open(schema_file) as f:
                params_schema = json.load(f)

        return DeterministicBlueprint(
            type="deterministic",
            name=metadata["name"],
            command=metadata["command"],
            parameters_schema=params_schema,
            timeout_seconds=metadata.get("timeout_seconds"),
            **metadata
        )
```

### 10. Validation and Error Handling

```python
def validate_run_request(request: CreateRunRequest, blueprint: Blueprint):
    """
    Validate run request against blueprint type.
    """
    if blueprint.type == "agent":
        if not request.prompt:
            raise ValidationError("Agent blueprints require 'prompt' field")
        if request.parameters:
            raise ValidationError("Agent blueprints don't accept 'parameters', use 'prompt'")

    elif blueprint.type == "deterministic":
        if not request.parameters:
            raise ValidationError("Deterministic blueprints require 'parameters' field")
        if request.prompt:
            # Allow prompt as fallback for basic tasks?
            # Or strict: raise ValidationError("Deterministic blueprints don't accept 'prompt'")
            pass

        # Validate parameters against schema
        if blueprint.parameters_schema:
            try:
                jsonschema.validate(request.parameters, blueprint.parameters_schema)
            except jsonschema.ValidationError as e:
                raise ValidationError(f"Parameter validation failed: {e.message}")
```

## Data Models

### Updated Blueprint Models

```python
from pydantic import BaseModel
from typing import Literal, Optional, Any

class BaseBlueprint(BaseModel):
    name: str
    description: str
    type: Literal["agent", "deterministic"]
    tags: list[str] = []
    demands: Optional[RunnerDemands] = None

class AgentBlueprint(BaseBlueprint):
    type: Literal["agent"] = "agent"
    system_prompt: str
    mcp_servers: Optional[dict[str, Any]] = None

class DeterministicBlueprint(BaseBlueprint):
    type: Literal["deterministic"] = "deterministic"
    command: str
    parameters_schema: Optional[dict[str, Any]] = None
    parameter_strategy: Literal["stdin_json", "args", "env", "file"] = "stdin_json"
    timeout_seconds: Optional[int] = None
    working_dir: Optional[str] = None  # Override project_dir for execution

Blueprint = AgentBlueprint | DeterministicBlueprint
```

### Updated Run Model

```python
class Run(BaseModel):
    run_id: str
    session_id: str
    type: Literal["start_session", "resume_session", "execute_task"]
    status: RunStatus

    # For agent runs
    prompt: Optional[str] = None
    agent_name: Optional[str] = None

    # For deterministic runs
    parameters: Optional[dict[str, Any]] = None
    task_name: Optional[str] = None

    # Common
    project_dir: Optional[str] = None
    demands: Optional[RunnerDemands] = None
    created_at: datetime
    timeout_at: Optional[datetime] = None
```

## Rationale

### Why Not Just "Prompt Engineering"?

One could argue: "Just pass parameters as a prompt and let the AI parse them."

| Approach | Pros | Cons |
|----------|------|------|
| Prompt Engineering | No changes needed | AI overhead, non-deterministic, token cost, latency |
| Native Parameters | Precise, fast, deterministic | Requires schema definition |

For truly deterministic tasks, the overhead of AI interpretation is wasteful and introduces unnecessary variability.

### Why Same Lifecycle as Agents?

Keeping the same lifecycle enables:
- **Unified orchestration**: One set of tools works for both types
- **Consistent monitoring**: Same status API, same events
- **Callback compatibility**: Deterministic children can trigger parent callbacks
- **Familiar patterns**: No new concepts for orchestrator developers

### Why JSON Schema for Parameters?

- **Standard format**: Well-known, tooling exists
- **Validation**: Automatic parameter validation
- **Documentation**: Schema serves as API documentation
- **IDE support**: Editors can provide autocomplete based on schema

### Alternatives Considered

#### A: Separate API for Deterministic Tasks

```
POST /tasks  # Separate from /runs
```

**Rejected because:**
- Creates API fragmentation
- Orchestrators need two different APIs
- Callbacks would need separate handling

#### B: Encode Parameters in Prompt

```
start_agent_session(
    agent_name="web-crawler",
    prompt='{"url": "...", "depth": 2}'  # JSON in prompt
)
```

**Rejected because:**
- Loses type safety
- No validation at coordinator level
- Awkward for orchestrators

#### C: Make All Executors Support Both Modes

Have claude-code executor also handle deterministic tasks.

**Rejected because:**
- Violates single responsibility
- Makes executor code complex
- Different resource requirements

## Consequences

### Positive

- **Unified orchestration**: Same tools work for agents and tasks
- **Callback support**: Deterministic tasks participate in async callbacks
- **Type safety**: Structured parameters with validation
- **Performance**: No AI overhead for deterministic operations
- **Predictability**: Exact same behavior every run
- **Extensibility**: New deterministic tasks are just blueprints

### Negative

- **Schema maintenance**: Need to define/update parameter schemas
- **New executor**: Must implement and maintain deterministic executor
- **Runner configuration**: Need dedicated runners for deterministic tasks
- **Blueprint complexity**: Two types with different required fields

### Neutral

- Existing agent blueprints unchanged (backward compatible)
- MCP tools extended, not replaced
- Coordinator gains parameter validation responsibility

## Implementation Plan

### Phase 1: Core Infrastructure
1. Extend blueprint models with `type` field
2. Add `parameters` field to run creation API
3. Implement parameter validation (JSON Schema)
4. Update blueprint resolution logic

### Phase 2: Deterministic Executor
1. Create `executors/deterministic/` structure
2. Implement `ao-deterministic-exec` executor
3. Support stdin_json parameter strategy
4. Add event reporting and result capture

### Phase 3: Integration
1. Extend `start_agent_session` MCP tool
2. Update coordinator run queue logic
3. Test callback flow with deterministic children
4. Add runner demands for executor_type matching

### Phase 4: Documentation and Examples
1. Create example deterministic blueprints
2. Document parameter schema format
3. Add integration tests
4. Update API documentation

## Example Blueprints

### Web Crawler

```
config/agents/web-crawler/
├── agent.json
└── agent.parameters.json
```

**agent.json:**
```json
{
    "name": "web-crawler",
    "description": "Crawls websites to specified depth",
    "type": "deterministic",
    "tags": ["internal", "web", "crawler"],
    "demands": {
        "tags": ["python", "playwright"]
    },
    "command": "uv run --script scripts/crawler.py",
    "parameter_strategy": "stdin_json",
    "timeout_seconds": 3600
}
```

### Database Backup

```json
{
    "name": "db-backup",
    "description": "Creates database backup",
    "type": "deterministic",
    "tags": ["internal", "database", "backup"],
    "demands": {
        "hostname": "db-server",
        "tags": ["postgres"]
    },
    "command": "pg_dump",
    "parameter_strategy": "args",
    "timeout_seconds": 7200
}
```

### Test Suite Runner

```json
{
    "name": "test-runner",
    "description": "Runs test suite and reports results",
    "type": "deterministic",
    "tags": ["internal", "testing"],
    "demands": {
        "executor_type": "deterministic"
    },
    "command": "uv run pytest",
    "parameter_strategy": "args",
    "timeout_seconds": 1800
}
```

## References

- [ADR-002](./ADR-002-agent-runner-architecture.md) - Agent Runner Architecture
- [ADR-003](./ADR-003-callback-based-async.md) - Callback-Based Async
- [ADR-010](./ADR-010-session-identity-and-executor-abstraction.md) - Session Identity and Executor Abstraction
- [ADR-011](./ADR-011-runner-capabilities-and-run-demands.md) - Runner Capabilities and Run Demands
- [invocation.py](../../servers/agent-runner/lib/invocation.py) - Current invocation schema
- [executor.py](../../servers/agent-runner/lib/executor.py) - Current executor implementation
