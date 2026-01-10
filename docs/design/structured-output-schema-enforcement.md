# Structured Output with Schema Enforcement

**Status:** Draft
**Date:** 2025-01-05

## Overview

Enable callers to request structured output from agent runs that conforms to a specified JSON Schema. The framework enforces schema compliance **independently of the underlying AI API** - ensuring deterministic, parseable responses regardless of which AI backend is used.

**Key Principle:** Schema enforcement is the **caller's responsibility**, not the agent blueprint's. An orchestrating system should be able to request a specific output format from any agent, regardless of how that agent is configured.

## Motivation

### Problem Statement

When integrating AI agents with deterministic systems (CI/CD pipelines, workflow engines, external APIs), the calling system needs predictable, structured responses:

| Scenario | Current Behavior | Desired Behavior |
|----------|-----------------|------------------|
| Pipeline integration | Agent returns free-form text | Agent returns `{"status": "success", "files_modified": [...]}` |
| Multi-agent orchestration | Parent parses unstructured result | Parent receives typed data structure |
| External API bridge | Manual parsing, error-prone | Guaranteed schema compliance |

### Why Framework-Level Enforcement?

1. **API Independence**: Does not rely on Claude's structured output feature or any specific AI backend
2. **Caller Control**: Schema is specified per-run, not baked into agent blueprints
3. **Guaranteed Compliance**: Programmatic validation + retry ensures output matches schema
4. **Universal Applicability**: Works with any executor (Claude Code, future deterministic executors, etc.)

## Design

### 1. Schema Specification in Run Request

Callers specify the desired output schema when creating a run:

```json
POST /runs
{
  "type": "start_session",
  "agent_name": "code-analyzer",
  "prompt": "Analyze the codebase structure",
  "output_schema": {
    "type": "object",
    "required": ["summary", "files_analyzed", "issues"],
    "properties": {
      "summary": { "type": "string" },
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

### 2. Schema Storage Options

Schemas can come from multiple sources:

| Source | Use Case | Example |
|--------|----------|---------|
| **Inline (per-run)** | Ad-hoc requests, dynamic schemas | `POST /runs { output_schema: {...} }` |
| **Named schema (coordinator)** | Reusable schemas, organization standards | `POST /runs { output_schema_name: "code-analysis-result" }` |
| **Agent blueprint default** | Agent-recommended output format | Blueprint has `default_output_schema` |

**Resolution Priority:**
1. Inline `output_schema` in run request (highest)
2. Named `output_schema_name` reference
3. Agent blueprint's `default_output_schema` (lowest)

### 3. Named Schema Registry

For reusable schemas, the coordinator maintains a schema registry:

```
POST /schemas
{
  "name": "code-analysis-result",
  "description": "Standard format for code analysis output",
  "schema": {
    "type": "object",
    "required": ["summary", "issues"],
    ...
  }
}

GET /schemas
GET /schemas/{name}
DELETE /schemas/{name}
```

**Storage:** Schemas stored in SQLite `output_schemas` table or as files in `.agent-orchestrator/schemas/`.

### 4. Schema Enforcement Approaches

The framework provides multiple enforcement strategies, selectable per-run:

#### Approach A: Prompt Injection + Validation Loop (Recommended)

**How it works:**
1. **Instruction injection**: Append schema requirements to the agent's prompt
2. **Initial execution**: Run agent with modified prompt
3. **Validation**: Parse output and validate against JSON Schema
4. **Retry on failure**: Resume session with validation errors, ask agent to fix
5. **Final result**: Return validated output or fail after max retries

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Schema Enforcement Flow                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. Run Created with output_schema                                       │
│     ↓                                                                    │
│  2. Coordinator enriches prompt:                                         │
│     Original: "Analyze the codebase"                                     │
│     Enriched: "Analyze the codebase                                      │
│                                                                          │
│                ## Output Format (REQUIRED)                               │
│                Your response MUST be valid JSON matching this schema:    │
│                ```json                                                   │
│                {schema}                                                  │
│                ```                                                       │
│                Output ONLY the JSON, no additional text."                │
│     ↓                                                                    │
│  3. Agent executes, produces result                                      │
│     ↓                                                                    │
│  4. Coordinator validates result against schema                          │
│     ↓                                                                    │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ Valid?                                                            │   │
│  │   YES → Store result, mark run completed                          │   │
│  │   NO  → Check retry count                                         │   │
│  │         < max_retries → Resume with validation feedback           │   │
│  │         >= max_retries → Fail run with validation error           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Retry prompt (on validation failure):**

```
Your previous response did not match the required JSON schema.

## Validation Errors:
- $.issues[0].severity: 'critical' is not one of ['low', 'medium', 'high']
- $.summary: Required field missing

## Your Previous Response:
{previous_output}

## Required Schema:
{schema}

Please provide a corrected response that matches the schema exactly.
Output ONLY the valid JSON, no additional text.
```

**Configuration options:**

```json
{
  "output_schema": { ... },
  "output_schema_options": {
    "max_retries": 3,              // Default: 2
    "extract_json": true,          // Try to extract JSON from mixed output
    "strict_json_only": false      // If true, fail if any non-JSON text present
  }
}
```

#### Approach B: Post-Processing Extraction

For agents that may return JSON embedded in text:

```
Agent output: "Here's the analysis:\n```json\n{\"summary\": \"...\"}```\n\nLet me know if you need more details."

Extraction: {"summary": "..."}
```

**Extraction strategies:**
1. Parse entire output as JSON (fastest)
2. Extract first JSON block (```json...``` or {...})
3. Extract last JSON block
4. Use regex patterns for common formats

#### Approach C: Schema-Aware System Prompt

Inject schema requirements into the agent's system prompt (for new sessions):

```python
# In blueprint resolver or executor
if run.output_schema:
    system_prompt = f"""
{original_system_prompt}

IMPORTANT: All your responses must be valid JSON conforming to this schema:
{json.dumps(run.output_schema, indent=2)}

Never include explanatory text outside the JSON structure.
"""
```

**Trade-off:** More persistent but less flexible than prompt injection.

### 5. Implementation Architecture

#### Coordinator Changes

**New fields in Run model:**

```python
class RunCreate(BaseModel):
    # ... existing fields ...
    output_schema: Optional[dict] = None          # Inline JSON Schema
    output_schema_name: Optional[str] = None      # Reference to named schema
    output_schema_options: Optional[OutputSchemaOptions] = None

class OutputSchemaOptions(BaseModel):
    max_retries: int = 2
    extract_json: bool = True
    strict_json_only: bool = False
```

**New service: SchemaEnforcer**

```python
# servers/agent-coordinator/services/schema_enforcer.py

class SchemaEnforcer:
    """Validates and enforces output schema compliance."""

    def enrich_prompt(self, prompt: str, schema: dict) -> str:
        """Add schema instructions to prompt."""

    def validate_output(self, output: str, schema: dict) -> ValidationResult:
        """Validate output against JSON Schema."""

    def extract_json(self, output: str) -> Optional[str]:
        """Try to extract JSON from mixed output."""

    def build_retry_prompt(
        self,
        original_output: str,
        errors: List[str],
        schema: dict
    ) -> str:
        """Build prompt for retry with validation feedback."""
```

**Modified run completion flow:**

```python
# In callback_processor.py or run completion handler

async def on_run_completed(run_id: str):
    run = run_queue.get_run(run_id)

    if run.output_schema:
        result = get_session_result(run.session_id)
        validation = schema_enforcer.validate_output(result, run.output_schema)

        if validation.valid:
            # Store validated result, mark complete
            store_validated_result(run.session_id, validation.parsed_json)
            update_run_status(run_id, COMPLETED)
        else:
            retry_count = get_retry_count(run_id)
            if retry_count < run.output_schema_options.max_retries:
                # Create retry run
                retry_prompt = schema_enforcer.build_retry_prompt(
                    result, validation.errors, run.output_schema
                )
                create_resume_run(
                    session_id=run.session_id,
                    prompt=retry_prompt,
                    output_schema=run.output_schema,
                    retry_count=retry_count + 1
                )
            else:
                # Max retries exceeded
                update_run_status(run_id, FAILED,
                    error=f"Schema validation failed after {retry_count} retries: {validation.errors}")
    else:
        # No schema enforcement, complete as usual
        update_run_status(run_id, COMPLETED)
```

#### Database Changes

**New table for named schemas:**

```sql
CREATE TABLE output_schemas (
    name TEXT PRIMARY KEY,
    description TEXT,
    schema TEXT NOT NULL,  -- JSON Schema as JSON string
    created_at TEXT NOT NULL,
    modified_at TEXT NOT NULL
);
```

**Extended sessions table:**

```sql
ALTER TABLE sessions ADD COLUMN validated_output TEXT;  -- Parsed JSON result
ALTER TABLE sessions ADD COLUMN output_schema TEXT;     -- Schema used (for reference)
```

#### Runner/Executor Changes

**Minimal changes required.** The schema enforcement happens at the coordinator level, after the executor reports completion. The executor continues to:
1. Run the session with the (enriched) prompt
2. Report result via `session_stop` event
3. Coordinator handles validation and retry

**Optional executor awareness:** Executors could receive schema hints for native support:

```python
# In executor invocation payload (Schema 2.1)
{
    "schema_version": "2.1",
    "mode": "start",
    "session_id": "ses_abc123",
    "prompt": "...",  # Already enriched by coordinator
    "output_schema_hint": { ... }  # Optional: executor can use native features
}
```

### 6. API Endpoints

#### Create Run with Schema

```
POST /runs
{
  "type": "start_session",
  "agent_name": "analyzer",
  "prompt": "Analyze security vulnerabilities",
  "output_schema": {
    "type": "object",
    "required": ["vulnerabilities"],
    "properties": {
      "vulnerabilities": {
        "type": "array",
        "items": { "$ref": "#/definitions/vulnerability" }
      }
    },
    "definitions": {
      "vulnerability": {
        "type": "object",
        "required": ["id", "severity", "description"],
        "properties": {
          "id": { "type": "string" },
          "severity": { "type": "string", "enum": ["low", "medium", "high", "critical"] },
          "description": { "type": "string" },
          "affected_files": { "type": "array", "items": { "type": "string" } }
        }
      }
    }
  }
}
```

#### Get Validated Result

```
GET /sessions/{session_id}/result

Response (with schema enforcement):
{
  "result": "...",           // Raw result text
  "validated_output": {      // Parsed, validated JSON (NEW)
    "vulnerabilities": [...]
  },
  "schema_validation": {     // Validation metadata (NEW)
    "valid": true,
    "schema_name": "security-scan-result",
    "retry_count": 1
  }
}
```

#### Schema Registry

```
POST /schemas
{
  "name": "security-scan-result",
  "description": "Output format for security scanning agents",
  "schema": { ... }
}

GET /schemas
[
  {"name": "security-scan-result", "description": "..."},
  {"name": "code-analysis-result", "description": "..."}
]

GET /schemas/{name}
{
  "name": "security-scan-result",
  "description": "...",
  "schema": { ... },
  "created_at": "...",
  "modified_at": "..."
}

DELETE /schemas/{name}
```

### 7. Agent Blueprint Integration

Blueprints can define a default output schema:

```json
{
  "name": "security-scanner",
  "description": "Scans code for security vulnerabilities",
  "system_prompt": "...",
  "default_output_schema": {
    "type": "object",
    "required": ["scan_complete", "vulnerabilities"],
    "properties": {
      "scan_complete": { "type": "boolean" },
      "vulnerabilities": { "type": "array" }
    }
  },
  "default_output_schema_options": {
    "max_retries": 3,
    "extract_json": true
  }
}
```

**Override behavior:** Caller's `output_schema` always takes precedence over blueprint defaults.

### 8. MCP Server Integration

The Agent Orchestrator MCP server exposes schema enforcement:

```python
@tool
def start_agent_session(
    agent_name: str,
    prompt: str,
    output_schema: Optional[dict] = None,
    output_schema_name: Optional[str] = None,
    # ... other params
) -> dict:
    """Start an agent session with optional structured output.

    Args:
        output_schema: JSON Schema the output must conform to
        output_schema_name: Name of a registered schema to use
    """
```

**Use case:** Orchestrating agents can request structured output from child agents:

```python
# Orchestrator agent code
result = await start_agent_session(
    agent_name="code-analyzer",
    prompt="Analyze src/ directory",
    output_schema={
        "type": "object",
        "required": ["files", "loc"],
        "properties": {
            "files": {"type": "integer"},
            "loc": {"type": "integer"}
        }
    }
)
# Result is guaranteed to be {"files": N, "loc": M}
```

## Validation Implementation

### JSON Schema Validation

Use `jsonschema` library for validation:

```python
import jsonschema
from jsonschema import Draft7Validator, ValidationError

class SchemaValidator:
    def validate(self, data: dict, schema: dict) -> ValidationResult:
        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(data))

        if not errors:
            return ValidationResult(valid=True, parsed_json=data)

        error_messages = [
            f"$.{'.'.join(str(p) for p in e.absolute_path)}: {e.message}"
            for e in errors
        ]
        return ValidationResult(valid=False, errors=error_messages)
```

### JSON Extraction Strategies

```python
import json
import re

class JSONExtractor:
    def extract(self, text: str) -> Optional[dict]:
        # Strategy 1: Direct parse
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract from code block
        code_block = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if code_block:
            try:
                return json.loads(code_block.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Strategy 3: Find JSON object/array
        json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        return None
```

## Error Handling

### Validation Failure After Max Retries

```json
{
  "run_id": "run_abc123",
  "status": "failed",
  "error": {
    "type": "schema_validation_failed",
    "message": "Output did not match schema after 3 attempts",
    "validation_errors": [
      "$.severity: 'critical' is not one of ['low', 'medium', 'high']"
    ],
    "last_output": "..."
  }
}
```

### Schema Not Found

```json
{
  "error": "SchemaNotFound",
  "message": "Output schema 'nonexistent-schema' not found",
  "status_code": 404
}
```

### Invalid Schema Definition

```json
{
  "error": "InvalidSchema",
  "message": "output_schema is not a valid JSON Schema",
  "details": "Schema validation error at $.properties: Expected object"
}
```

## Comparison of Enforcement Approaches

| Approach | Reliability | Latency | Complexity | API Independence |
|----------|-------------|---------|------------|------------------|
| **Prompt Injection + Validation Loop** | High | Medium (retries) | Medium | Full |
| **Post-Processing Extraction** | Medium | Low | Low | Full |
| **System Prompt Injection** | Medium | Low | Low | Full |
| **Native AI API (e.g., Claude structured)** | Very High | Low | Low | None |

**Recommendation:** Use **Prompt Injection + Validation Loop** as the primary approach for maximum reliability while maintaining API independence.

## Configuration Summary

### Run-Level Options

```json
{
  "output_schema": { ... },           // Inline schema
  "output_schema_name": "...",        // OR named schema reference
  "output_schema_options": {
    "max_retries": 2,                 // Retry attempts on validation failure
    "extract_json": true,             // Try to extract JSON from text
    "strict_json_only": false,        // Fail if non-JSON text present
    "validation_mode": "strict"       // "strict" | "lenient"
  }
}
```

### Global Defaults (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `SCHEMA_ENFORCEMENT_MAX_RETRIES` | `2` | Default max retry attempts |
| `SCHEMA_ENFORCEMENT_EXTRACT_JSON` | `true` | Default extraction behavior |

## Implementation Plan

### Phase 1: Core Validation Infrastructure

1. Add `output_schema` field to Run model
2. Implement `SchemaEnforcer` service
3. Add validation to run completion handler
4. Extend result API to include validated output

### Phase 2: Retry Mechanism

1. Implement retry counting and tracking
2. Build retry prompt generation
3. Integrate with resume run creation
4. Add retry status to run/session queries

### Phase 3: Schema Registry

1. Create `output_schemas` table
2. Implement CRUD endpoints
3. Add schema resolution (inline → named → blueprint default)

### Phase 4: Integration

1. Update MCP server with schema parameters
2. Update Dashboard run creation UI
3. Add schema management to Dashboard
4. Documentation and examples

## Success Criteria

- [ ] Runs can specify output schema inline or by name
- [ ] Agent output is validated against JSON Schema
- [ ] Failed validation triggers retry with feedback
- [ ] Validated JSON stored separately from raw result
- [ ] Schema registry supports CRUD operations
- [ ] MCP server supports schema parameters
- [ ] Works with any executor (API-independent)

## Out of Scope

- **Schema versioning** - Schemas are immutable; create new schema for changes
- **Schema inheritance** - Use JSON Schema `$ref` for composition
- **Complex transformations** - Framework validates, doesn't transform output
- **Streaming validation** - Validation happens on complete result only

## References

- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture overview
- [agent-callback-architecture.md](../features/agent-callback-architecture.md) - Resume mechanism
- [agent-types.md](../architecture/agent-types.md) - Agent types and parameter validation
- [RUNS_API.md](../components/agent-coordinator/RUNS_API.md) - Run API reference
