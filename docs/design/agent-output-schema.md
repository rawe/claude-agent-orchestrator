# Agent Output Schema

**Status:** Draft
**Date:** 2026-01-18

## Overview

This document defines how **autonomous agent** blueprints can specify an **output schema** - a JSON Schema that the agent's output must conform to. This is the output-side counterpart to `parameters_schema` (input schema), creating a complete input/output contract for agents.

**Key Principle:** The output schema is defined by the **agent designer** as part of the blueprint, not by the caller. This establishes a reliable contract: "this agent always outputs data in this format."

**Enforcement:** Output schema is validated on **every run** (start and resume) by the **executor**. This ensures a consistent structured interface for all interactions with the agent.

**Note:** Procedural agents already produce structured output via `result_data`. This feature brings the same capability to autonomous agents.

### Relationship to Existing Design

This feature **supersedes** the caller-driven approach from `structured-output-schema-enforcement.md` for blueprint-defined schemas. When an agent has an `output_schema` in its blueprint:

- The blueprint's schema is **authoritative** - callers cannot override it
- The schema is enforced by the executor on every run
- Invalid results are never sent to the coordinator - only schema-conforming results

The existing caller-driven design remains valid for agents **without** a blueprint-defined output schema.

## Motivation

### Problem Statement

Currently, agents can return arbitrary unstructured output. This creates challenges for:

| Scenario | Problem |
|----------|---------|
| Multi-agent orchestration | Parent agent must parse free-form text from child |
| Pipeline integration | CI/CD systems need predictable, structured responses |
| API bridges | External systems require typed data structures |
| Quality assurance | No way to ensure agent output meets requirements |

### Solution

Define `output_schema` in the agent blueprint, mirroring how `parameters_schema` defines inputs:

```json
{
  "name": "code-analyzer",
  "parameters_schema": {
    "type": "object",
    "required": ["repo_path"],
    "properties": {
      "repo_path": { "type": "string" }
    }
  },
  "output_schema": {
    "type": "object",
    "required": ["files_analyzed", "issues"],
    "properties": {
      "files_analyzed": { "type": "integer" },
      "issues": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["file", "severity", "message"],
          "properties": {
            "file": { "type": "string" },
            "severity": { "type": "string", "enum": ["low", "medium", "high"] },
            "message": { "type": "string" }
          }
        }
      }
    }
  }
}
```

## Design

### 1. Agent Blueprint Schema Changes

Add one new field to the Agent model:

```python
class Agent(BaseModel):
    # ... existing fields ...

    # Input contract (existing)
    parameters_schema: Optional[dict] = None

    # Output contract (NEW)
    output_schema: Optional[dict] = None  # JSON Schema for result validation
```

**Field definition:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `output_schema` | `dict \| null` | `null` | JSON Schema (Draft-7) that the agent's output must conform to |

**Enforcement behavior:**

| Run Type | Output Schema Validation |
|----------|-------------------------|
| `start_session` | **Always enforced** (in executor) |
| `resume_session` | **Always enforced** (in executor) |

The structured output contract applies to **every interaction** with the agent.

### 2. Architecture: Executor-Level Validation

Validation and retry happen entirely within the **executor**, not the coordinator. This keeps the coordinator simple and leverages the executor's direct access to the AI session.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Architecture                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Coordinator                                                                 │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ - Stores output_schema in agent blueprint                              │ │
│  │ - Passes blueprint to runner (unchanged)                               │ │
│  │ - Receives ONLY valid results or failures                              │ │
│  │ - NO validation logic                                                  │ │
│  │ - NO retry orchestration                                               │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                               │                                              │
│                               ▼                                              │
│  Agent Runner                                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ - Fetches blueprint (includes output_schema)                           │ │
│  │ - Resolves placeholders                                                │ │
│  │ - Passes blueprint to executor (unchanged)                             │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                               │                                              │
│                               ▼                                              │
│  Executor                                                                    │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ - Receives blueprint with output_schema                                │ │
│  │ - Enriches system_prompt with output schema instructions               │ │
│  │ - Runs AI session                                                      │ │
│  │ - Validates output against output_schema                               │ │
│  │ - Re-prompts on validation failure (1 retry max)                       │ │
│  │ - Sends only valid results to coordinator                              │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Why executor-level validation?**

| Aspect | Coordinator Validation | Executor Validation |
|--------|----------------------|---------------------|
| **Retry mechanism** | Create new resume run, complex state | Re-prompt in same session (trivial) |
| **Caller visibility** | Must hide internal retries | Transparent - caller just waits |
| **Coordinator complexity** | High - retry orchestration | None - receives clean results |
| **Session management** | Resume creates new run | Same session, no new runs |

### 3. Executor Implementation

The executor is responsible for:
1. **System prompt enrichment** - Append output schema instructions
2. **Validation** - Validate result against schema
3. **Retry** - Re-prompt if validation fails (1 retry max)

#### 3.1 System Prompt Enrichment

The executor appends output schema instructions as the **last section** of the system prompt:

```python
def build_system_prompt_with_output_schema(blueprint: dict) -> str:
    """Build system prompt with output schema appended as last section."""
    system_prompt = blueprint.get("system_prompt", "")
    output_schema = blueprint.get("output_schema")

    if not output_schema:
        return system_prompt

    output_instructions = f"""

## Required Output Format

You MUST provide structured output as JSON conforming to this schema:

```json
{json.dumps(output_schema, indent=2)}
```

Your response MUST be valid JSON that matches this schema exactly. Output ONLY the JSON, no additional text."""

    return system_prompt + output_instructions
```

#### 3.2 Validation and Retry Flow

Validation happens when receiving the result, before sending to coordinator:

```python
# In executor (claude_client.py) - conceptual implementation

async def run_claude_session(
    prompt: str,
    session_id: str,
    output_schema: Optional[dict] = None,
    ...
) -> tuple[str, str]:

    retry_count = 0
    max_retries = 1

    async for message in client.receive_response():
        if isinstance(message, ResultMessage):
            result_text = message.result

            # Extract JSON output from response
            output_json = extract_json_from_response(result_text)

            # Validate if output_schema exists
            if output_schema:
                validation = validate_against_schema(output_json, output_schema)

                if not validation.valid:
                    if retry_count < max_retries:
                        # Re-prompt in same session
                        retry_count += 1
                        retry_prompt = build_validation_error_prompt(
                            validation.errors,
                            output_schema
                        )
                        await client.query(retry_prompt)
                        continue  # Back to message loop
                    else:
                        # Retry exhausted - report failure
                        raise OutputSchemaValidationError(
                            f"Output validation failed after {retry_count} retry",
                            validation.errors
                        )

            # Send result to coordinator (mutually exclusive fields)
            if output_schema:
                # With schema: validated JSON in result_data
                session_client.add_event(session_id, {
                    "event_type": "result",
                    "session_id": session_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "result_text": None,
                    "result_data": output_json,
                })
            else:
                # Without schema: text in result_text (current behavior)
                session_client.add_event(session_id, {
                    "event_type": "result",
                    "session_id": session_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "result_text": result_text,
                    "result_data": None,
                })

            return executor_session_id, result_text
```

#### 3.3 Validation Error Prompt

When validation fails, the executor re-prompts with:

```python
def build_validation_error_prompt(errors: list[dict], schema: dict) -> str:
    """Build prompt for schema validation retry."""
    error_lines = "\n".join(f"- {e['path']}: {e['message']}" for e in errors)

    return f"""<output-validation-error>
Your output did not match the required schema.

## Validation Errors
{error_lines}

## Required Schema
```json
{json.dumps(schema, indent=2)}
```

Please provide output matching the schema exactly.
</output-validation-error>"""
```

#### 3.4 JSON Schema Validation

```python
from jsonschema import Draft7Validator

def validate_against_schema(output: dict | None, schema: dict) -> ValidationResult:
    """Validate agent output against JSON Schema."""
    if output is None:
        return ValidationResult(
            valid=False,
            errors=[{"path": "$", "message": "No JSON output found but output_schema requires structured output"}]
        )

    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(output))

    if not errors:
        return ValidationResult(valid=True)

    return ValidationResult(
        valid=False,
        errors=[
            {
                "path": f"$.{'.'.join(str(p) for p in e.absolute_path)}" if e.absolute_path else "$",
                "message": e.message,
            }
            for e in errors
        ]
    )
```

### 4. Retry Behavior

**Retry limit:** 1 retry per run (2 total attempts: initial + 1 retry)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Executor Validation Flow                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. AI produces response                                                     │
│                     │                                                        │
│                     ▼                                                        │
│  2. Extract JSON output from response                                        │
│                     │                                                        │
│                     ▼                                                        │
│  3. Validate against output_schema                                           │
│                     │                                                        │
│         ┌──────────┴──────────┐                                             │
│         │                     │                                              │
│         ▼                     ▼                                              │
│      Valid              Invalid                                              │
│         │                     │                                              │
│         │         ┌───────────┴───────────┐                                 │
│         │         │                       │                                  │
│         │         ▼                       ▼                                  │
│         │   retry_count < 1         retry_count >= 1                        │
│         │         │                       │                                  │
│         │         ▼                       ▼                                  │
│         │   Re-prompt AI            Report FAILURE                          │
│         │   (same session)          (don't send result)                     │
│         │   retry_count++                                                    │
│         │         │                                                          │
│         │         └──────────▶ Back to step 1                               │
│         │                                                                    │
│         ▼                                                                    │
│  4. Send valid result to coordinator (mutually exclusive fields)             │
│     session_client.add_event({                                              │
│         event_type: "result",                                                │
│         result_text: ...   // AI text (if no output_schema)                 │
│         result_data: ...   // Validated JSON (if output_schema)             │
│     })                                                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5. Result Structure (Backwards Compatible)

This design keeps the existing `result_text` and `result_data` fields. They are **mutually exclusive**: only one is set per result.

#### Result Event Structure

```python
# Result event structure - mutually exclusive fields
{
    "event_type": "result",
    "session_id": "ses_abc123",
    "timestamp": "...",
    "result_text": str | None,  # AI text response (if no output_schema)
    "result_data": dict | None, # Validated JSON (if output_schema)
}
```

#### Result Field by Agent Type and Schema

| Agent Type | Has output_schema | `result_text` | `result_data` |
|------------|-------------------|---------------|---------------|
| **Autonomous** | No | AI's text response | `None` |
| **Autonomous** | Yes | `None` | Validated JSON |
| **Procedural** | (always has schema) | `None` | Structured JSON |

**Examples:**

```json
// Autonomous agent WITHOUT output_schema
{
    "event_type": "result",
    "session_id": "ses_abc123",
    "result_text": "I've analyzed the code and found 3 issues...",
    "result_data": null
}

// Autonomous agent WITH output_schema
{
    "event_type": "result",
    "session_id": "ses_abc123",
    "result_text": null,
    "result_data": {
        "files_analyzed": 42,
        "issues": [
            {"file": "main.py", "severity": "high", "message": "SQL injection"}
        ]
    }
}
```

#### Callback Processor: Returning Results to Parent Agents

The callback processor must return either `result_text` or `result_data` as the child's result, not both:

```python
def format_child_result(result_dict: dict) -> str:
    """Format child result for callback to parent agent.

    Returns result_data (as JSON) if present, otherwise result_text.
    """
    result_data = result_dict.get("result_data")
    if result_data is not None:
        # Structured output - return as formatted JSON
        return json.dumps(result_data, indent=2)
    else:
        # Text output - return directly
        return result_dict.get("result_text") or "(No result available)"
```

This ensures parent agents receive a single coherent result regardless of whether the child used structured output.

### 6. API Changes

#### Agent Model Updates

```python
class AgentCreate(BaseModel):
    # ... existing fields ...
    output_schema: Optional[dict] = None

class AgentUpdate(BaseModel):
    # ... existing fields ...
    output_schema: Optional[dict] = None

class Agent(BaseModel):
    # ... existing fields ...
    output_schema: Optional[dict] = None
```

#### Event and SessionResult Models (No Changes)

The existing `result_text` and `result_data` fields are preserved:

```python
class Event(BaseModel):
    event_type: str
    session_id: str
    timestamp: str
    # ... other fields ...
    result_text: Optional[str] = None   # Unchanged
    result_data: Optional[dict] = None  # Unchanged

class SessionResult(BaseModel):
    result_text: Optional[str] = None   # Unchanged
    result_data: Optional[dict] = None  # Unchanged
```

**Guarantee:** If the agent has `output_schema` and the run completed successfully, `result_data` is guaranteed to conform to the schema. If no `output_schema`, `result_text` contains the AI's response.

#### Failure Response

When validation fails after retry, the run fails:

```json
{
  "run_id": "run_abc123",
  "status": "failed",
  "error": {
    "type": "output_schema_validation_failed",
    "message": "Output did not match schema after 1 retry",
    "validation_errors": [
      "$.severity: 'critical' is not one of ['low', 'medium', 'high']",
      "$.count: -5 is less than minimum 0"
    ]
  }
}
```

### 6. Dashboard Changes

#### Agent Editor

Add output schema configuration alongside input schema:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Agent: code-analyzer                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  [General] [Input Schema] [Output Schema] [MCP Servers] [...]               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Output Schema (JSON Schema)                                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ {                                                                      │  │
│  │   "type": "object",                                                    │  │
│  │   "required": ["status", "data"],                                      │  │
│  │   ...                                                                  │  │
│  │ }                                                                      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  Info: Output schema is enforced on every run (start and resume).           │
│        Validation happens in the executor with 1 retry on failure.          │
│                                                                              │
│  [Validate Schema]                                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Session View

Show validation status:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Session: ses_abc123                                                         │
│  Agent: code-analyzer                                                        │
│  Status: completed                                                           │
│                                                                              │
│  Output Schema: Valid                                                        │
│                                                                              │
│  Result:                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ {"files_analyzed": 42, "issues": [...]}                                │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

For failed validation:

```
│  Status: failed                                                              │
│                                                                              │
│  Output Schema: Validation Failed                                            │
│  Errors:                                                                     │
│    - $.severity: 'critical' not in ['low', 'medium', 'high']                │
│                                                                              │
│  Retry attempts: 1/1 exhausted                                               │
```

### 7. Component Responsibilities Summary

| Component | Responsibility |
|-----------|----------------|
| **Agent Model** (`models.py`) | Add `output_schema` field |
| **Agent Storage** (`agent_storage.py`) | Load `output_schema` from JSON |
| **Coordinator** | Store blueprint, receive clean results (no validation) |
| **Callback Processor** | Return `result_data` if present, otherwise `result_text` |
| **Agent Runner** | Pass blueprint to executor (no changes) |
| **Executor** (`claude_client.py`) | Enrich system_prompt + validate + retry; use `result_data` when output_schema present |
| **Dashboard** | Output schema editor tab |

### 8. Database Changes

**None required.** All validation state is managed within the executor during execution.

## Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Agent with Output Schema - Full Flow                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. User creates run                                                         │
│     POST /runs { agent_name: "pr-reviewer", parameters: {pr_url: "..."} }   │
│                                                                              │
│  2. Coordinator validates input parameters (existing)                        │
│     Parameters match parameters_schema                                       │
│                                                                              │
│  3. Runner claims run, fetches blueprint (includes output_schema)            │
│                                                                              │
│  4. Executor receives blueprint, builds system prompt:                       │
│     ┌────────────────────────────────────────────────────────────────────┐  │
│     │ {original system_prompt}                                            │  │
│     │                                                                     │  │
│     │ ## Required Output Format                                           │  │
│     │                                                                     │  │
│     │ You MUST provide structured output as JSON conforming to schema:    │  │
│     │ ```json                                                             │  │
│     │ {"type": "object", "required": ["summary", "approval"], ...}        │  │
│     │ ```                                                                 │  │
│     └────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  5. Executor runs AI session with enriched system prompt                     │
│                                                                              │
│  6. AI produces JSON response, executor extracts and parses it               │
│                                                                              │
│  7. Executor validates JSON against output_schema                            │
│     ┌────────────────────────────────────────────────────────────────────┐  │
│     │ Valid?                                                              │  │
│     │   YES → Continue to step 8                                          │  │
│     │   NO  → retry_count < 1? Re-prompt AI, go to step 6                │  │
│     │         retry exhausted? Report failure                             │  │
│     └────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  8. Executor sends valid result to coordinator                               │
│     session_client.add_event({                                              │
│         event_type: "result",                                                │
│         result_text: null,                                                   │
│         result_data: {"summary": "...", "approval": "approve", ...}         │
│     })                                                                       │
│                                                                              │
│  9. Coordinator receives clean, validated result                             │
│     Stores result, marks run completed                                       │
│                                                                              │
│ 10. Result available via GET /sessions/{id}/result                           │
│     result_data guaranteed to match output_schema                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Example Agent Blueprint

```json
{
  "name": "pr-reviewer",
  "description": "Reviews pull requests and provides structured feedback",
  "type": "autonomous",
  "parameters_schema": {
    "type": "object",
    "required": ["pr_url"],
    "properties": {
      "pr_url": {
        "type": "string",
        "description": "GitHub PR URL to review"
      },
      "focus_areas": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Specific areas to focus on"
      }
    }
  },
  "output_schema": {
    "type": "object",
    "required": ["summary", "approval", "comments"],
    "properties": {
      "summary": {
        "type": "string",
        "description": "Brief summary of the PR"
      },
      "approval": {
        "type": "string",
        "enum": ["approve", "request_changes", "comment"],
        "description": "Review decision"
      },
      "comments": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["file", "line", "severity", "message"],
          "properties": {
            "file": { "type": "string" },
            "line": { "type": "integer" },
            "severity": { "type": "string", "enum": ["nitpick", "suggestion", "concern", "blocker"] },
            "message": { "type": "string" }
          }
        }
      },
      "metrics": {
        "type": "object",
        "properties": {
          "files_reviewed": { "type": "integer" },
          "lines_changed": { "type": "integer" },
          "complexity_score": { "type": "number", "minimum": 0, "maximum": 10 }
        }
      }
    }
  },
  "system_prompt": "You are a thorough code reviewer..."
}
```

## Success Criteria

- [ ] Agent blueprints can define `output_schema` (JSON Schema)
- [ ] Executor enriches system_prompt with output schema instructions (last section)
- [ ] Executor validates output against schema on **every run**
- [ ] Executor re-prompts on validation failure (1 retry max, same session)
- [ ] Executor uses `result_data` (not `result_text`) when output_schema is present
- [ ] Invalid results are never sent to coordinator
- [ ] Failed validation after retry marks run as `failed` with errors
- [ ] Coordinator receives only valid results or failures (no validation logic)
- [ ] Callback processor returns `result_data` if present, otherwise `result_text`
- [ ] Dashboard supports output schema editing
- [ ] Dashboard shows validation status on sessions

## Relevant Files for Implementation

### Documentation Files

| File | Purpose |
|------|---------|
| `docs/adr/ADR-015-autonomous-agent-input-schema.md` | Input schema handling - **reference for consistency** (how parameters_schema works) |
| `docs/adr/ADR-014-callback-message-format.md` | Callback message format - **how results are returned to parent agents** |
| `docs/design/structured-output-schema-enforcement.md` | Caller-driven output schemas - **alternative approach, may need reconciliation** |
| `docs/architecture/agent-types.md` | Agent type definitions |
| `docs/components/agent-coordinator/RUNS_API.md` | Run API reference |

### Code Files - Coordinator

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `servers/agent-coordinator/models.py` | Agent, Event, SessionResult models | Add `output_schema` to Agent (Event/SessionResult unchanged) |
| `servers/agent-coordinator/agent_storage.py` | Loads agent blueprints from JSON | Load `output_schema` field |
| `servers/agent-coordinator/database.py` | Stores events | No changes needed |
| `servers/agent-coordinator/services/callback_processor.py` | Returns results to parent agents | Return `result_data` (as JSON) if present, otherwise `result_text` |
| `servers/agent-coordinator/services/run_queue.py` | Parameter validation | Reference for validation pattern (input schema validation logic) |

### Code Files - Agent Runner / Executor

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `servers/agent-runner/executors/claude-code/ao-claude-code-exec` | Claude Code executor entry point | Pass output_schema to claude_client |
| `servers/agent-runner/executors/claude-code/lib/claude_client.py` | Runs Claude sessions, sends result events | **Main implementation**: system prompt enrichment, validation, retry; use `result_data` when output_schema present |
| `servers/agent-runner/lib/blueprint_resolver.py` | Fetches and resolves blueprints | No changes (passes blueprint unchanged) |
| `servers/agent-runner/lib/utils.py` | Shared utilities (input formatting) | Reference for `format_autonomous_inputs()` pattern |

### Code Files - Dashboard

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `dashboard/src/types/agent.ts` | Agent TypeScript types | Add `output_schema` field |
| `dashboard/src/components/features/agents/AgentEditor.tsx` | Agent creation/editing UI | Add Output Schema tab |
| `dashboard/src/components/features/agents/InputSchemaEditor.tsx` | Input schema editor component | Reference for building OutputSchemaEditor (similar pattern) |

## Out of Scope

- **Caller-specified output schemas** - See `structured-output-schema-enforcement.md` for that feature
- **Schema versioning** - Schemas are part of blueprint; version the blueprint
- **Output transformation** - Framework validates, doesn't transform
- **Streaming validation** - Validation on complete result only
- **Configurable retry count** - Fixed at 1 retry (may add later if needed)
- **Coordinator validation** - All validation in executor for simplicity

## References

- [ADR-015: Autonomous Agent Input Schema](../adr/ADR-015-autonomous-agent-input-schema.md) - Input schema handling (consistency reference)
- [structured-output-schema-enforcement.md](./structured-output-schema-enforcement.md) - Caller-driven output schemas (alternative approach)
- [agent-types.md](../architecture/agent-types.md) - Agent type definitions
- [RUNS_API.md](../components/agent-coordinator/RUNS_API.md) - Run API reference
