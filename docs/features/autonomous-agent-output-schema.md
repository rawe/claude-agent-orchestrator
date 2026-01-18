# Autonomous Agent Output Schema

**Status:** Implemented
**Version:** 1.0

## Overview

Custom output schemas allow autonomous agents to produce structured JSON responses that are validated before completion. Agent designers define a JSON Schema that specifies the required output format. This enables predictable outputs for multi-agent orchestration, structured data pipelines, and consistent result formats.

## Motivation

### The Problem: Unstructured Output

Autonomous agents typically return free-form text in `result_text`:

```json
{
  "result_text": "I analyzed the repository and found 3 security issues...",
  "result_data": null
}
```

This creates challenges:

| Use Case | Desired Output | Problem |
|----------|---------------|---------|
| Multi-agent pipeline | Structured JSON for downstream processing | Parent agents must parse free-form text |
| API integration | Predictable response format | Consumers can't rely on output structure |
| Data aggregation | Consistent field names and types | No validation or contract |

### The Solution: Output Schemas

Custom output schemas solve this by defining a contract for agent output:

```json
{
  "result_text": null,
  "result_data": {
    "issues": [
      {"severity": "high", "description": "SQL injection vulnerability"},
      {"severity": "medium", "description": "Missing rate limiting"}
    ],
    "summary": "Found 2 security issues requiring attention"
  }
}
```

The agent is instructed to produce JSON matching the schema, the output is validated, and valid results are stored in `result_data` instead of `result_text`.

## Key Concepts

### Blueprint-Defined Schema

The output schema is defined by the **agent designer** in the agent blueprint, not by callers:

```json
{
  "name": "security-scanner",
  "description": "Scans code for security issues",
  "type": "autonomous",
  "output_schema": {
    "type": "object",
    "required": ["issues", "summary"],
    "properties": {
      "issues": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["severity", "description"],
          "properties": {
            "severity": {"type": "string", "enum": ["high", "medium", "low"]},
            "description": {"type": "string"}
          }
        }
      },
      "summary": {"type": "string"}
    }
  }
}
```

### Executor-Level Validation

Validation happens in the **executor**, not the coordinator:

- Executor has live AI session for re-prompting on validation failure
- No coordinator complexity for retry orchestration
- Caller sees only valid results or failures

### Retry Mechanism

When output validation fails, the executor:

1. Sends a validation error prompt to the agent
2. Receives a new response
3. Validates again
4. After 1 retry, fails the run if still invalid

This gives the agent one chance to correct its output format.

### Result Fields

Output schema affects which result field is populated:

| Agent Config | Output Location | Contains |
|-------------|-----------------|----------|
| No `output_schema` | `result_text` | Free-form text |
| With `output_schema` | `result_data` | Validated JSON |

Fields are **mutually exclusive**: when `output_schema` is defined, valid output goes to `result_data` and `result_text` is `null`.

## Defining an Output Schema

Add `output_schema` to your agent's `agent.json`:

### Basic Example

```json
{
  "name": "summarizer",
  "description": "Summarizes text documents",
  "type": "autonomous",
  "output_schema": {
    "type": "object",
    "required": ["summary"],
    "properties": {
      "summary": {
        "type": "string",
        "description": "The main summary"
      },
      "key_points": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Key points from the document"
      }
    }
  }
}
```

### Complex Example (PR Reviewer)

```json
{
  "name": "pr-reviewer",
  "description": "Reviews pull requests and provides structured feedback",
  "type": "autonomous",
  "output_schema": {
    "type": "object",
    "required": ["verdict", "comments"],
    "properties": {
      "verdict": {
        "type": "string",
        "enum": ["approve", "request_changes", "comment"],
        "description": "Overall review verdict"
      },
      "comments": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["file", "line", "message"],
          "properties": {
            "file": {"type": "string"},
            "line": {"type": "integer"},
            "message": {"type": "string"},
            "severity": {"type": "string", "enum": ["error", "warning", "suggestion"]}
          }
        }
      },
      "summary": {
        "type": "string",
        "description": "Brief summary of the review"
      }
    }
  }
}
```

## Validation Flow

### System Prompt Enrichment

When `output_schema` is defined, the executor automatically enriches the system prompt:

```markdown
## Required Output Format

You MUST provide structured output as JSON conforming to this schema:

```json
{
  "type": "object",
  "required": ["summary"],
  "properties": {
    "summary": {"type": "string"}
  }
}
```

Your final response MUST be valid JSON that matches this schema exactly. Output ONLY the JSON, no additional text.
```

### Output Extraction

The executor extracts JSON from the agent's response:

1. First tries JSON code blocks (```json ... ```)
2. Then tries raw JSON objects ({ ... })
3. Returns `null` if no valid JSON found

### Validation and Retry

```
Agent Response → Extract JSON → Validate Schema
                                    ↓
                              Valid? ─── Yes ──→ Store in result_data ─→ Complete
                                │
                                No
                                │
                                ↓
                         Retry count < 1?
                                │
                        Yes ────┴──── No
                         │            │
                         ↓            ↓
                  Send retry      Fail run
                    prompt        with error
                         │
                         ↓
                  New response
                  (loop back)
```

## API Usage

### Creating an Agent with Output Schema

```bash
curl -X POST http://localhost:8765/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "data-extractor",
    "description": "Extracts structured data from text",
    "type": "autonomous",
    "output_schema": {
      "type": "object",
      "required": ["entities"],
      "properties": {
        "entities": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "name": {"type": "string"},
              "type": {"type": "string"}
            }
          }
        }
      }
    }
  }'
```

### Result Structure

When the session completes, the result event contains:

```json
{
  "event_type": "result",
  "session_id": "ses_abc123",
  "timestamp": "2026-01-18T10:30:00Z",
  "result_text": null,
  "result_data": {
    "entities": [
      {"name": "John Smith", "type": "person"},
      {"name": "Acme Corp", "type": "organization"}
    ]
  }
}
```

## Dashboard Usage

1. Navigate to **Agents** and select an agent to edit
2. Toggle **Custom Output Schema** to enable
3. Define your JSON Schema in the editor
4. Click **Save**

The dashboard provides:
- JSON Schema editor with syntax highlighting
- Schema validation before saving
- Prettify button for formatting

## Callback Behavior

When a child agent with `output_schema` completes and calls back to a parent:

- The callback contains the structured JSON from `result_data`
- Parent receives formatted JSON instead of free-form text
- This enables reliable parsing in multi-agent orchestration

Example callback content:
```
<agent-callback session="ses_child123" status="completed">
## Child Result

{
  "verdict": "approve",
  "comments": [],
  "summary": "LGTM, no issues found"
}
</agent-callback>
```

## Error Handling

### Validation Failure

If output validation fails after retry, the run fails with an `OutputSchemaValidationError`:

```json
{
  "error": "OutputSchemaValidationError",
  "message": "Output validation failed after 1 retry",
  "errors": [
    {"path": "$.summary", "message": "'summary' is a required property"},
    {"path": "$.issues[0].severity", "message": "'critical' is not one of ['high', 'medium', 'low']"}
  ]
}
```

### No JSON Found

If the agent's response contains no extractable JSON:

```json
{
  "error": "OutputSchemaValidationError",
  "message": "Output validation failed after 1 retry",
  "errors": [
    {"path": "$", "message": "No JSON output found but output_schema requires structured output"}
  ]
}
```

## References

- [ADR-016: Autonomous Agent Output Schema](../adr/ADR-016-autonomous-agent-output-schema.md) - Design rationale and decision record
- [ADR-015: Autonomous Agent Input Schema](../adr/ADR-015-autonomous-agent-input-schema.md) - Related input schema feature
