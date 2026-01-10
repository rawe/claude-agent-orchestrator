# Autonomous Agent Input Schema

**Status:** Implemented
**Version:** 1.0

## Overview

Custom input schemas allow autonomous agents to accept structured parameters beyond the default prompt-only model. Agent designers can define a JSON Schema that specifies required fields, types, and validation rules. This enables self-documenting agents, input validation before expensive AI sessions, and structured inputs for specific use cases.

## Motivation

### The Problem: Prompt-Only Input

Previously, autonomous agents only accepted a single `prompt` parameter:

```json
{"prompt": "Help me write a summary about AI safety"}
```

This created limitations:

| Use Case | Desired Input | Problem |
|----------|--------------|---------|
| Content generation | topic, format, word limit | Can't validate or separate concerns |
| Code review | repo URL, branch, focus areas | No structured input possible |
| Data analysis | dataset, columns, output format | All info crammed into prompt |

### The Solution: Custom Schemas

Custom input schemas solve this by allowing structured parameters:

```json
{
  "topic": "AI Safety",
  "format": "bullet_points",
  "max_words": 200
}
```

The agent receives these as a formatted `<inputs>` block, validated against a JSON Schema before execution.

## Key Concepts

### Two Modes of Operation

| Mode | Schema | Input | Agent Receives |
|------|--------|-------|----------------|
| **Default** | `null` | `{"prompt": "..."}` | Prompt string directly |
| **Custom** | JSON Schema | Fields matching schema | `<inputs>` XML block |

### Schema Transparency

The schema you see is exactly what gets validated. There are no hidden requirements:

- **Default mode**: Requires `{"prompt": string}`
- **Custom mode**: Requires exactly what the schema defines

If you want free-form input with a custom schema, explicitly add `prompt` to your schema.

### Input Formatting

**Default mode** (no schema):
```
Help me debug this code...
```

**Custom mode** (with schema):
```
<inputs>
topic: AI Safety
format: summary
max_words: 200
</inputs>
```

All fields are formatted in the `<inputs>` block. The agent's system prompt should explain how to interpret these fields.

## Defining a Schema

Add `parameters_schema` to your agent's `agent.json`:

### Structured-Only Agent

For agents that don't need free-form input:

```json
{
  "name": "code-reviewer",
  "description": "Reviews code in a repository",
  "type": "autonomous",
  "parameters_schema": {
    "type": "object",
    "required": ["repo_url", "branch"],
    "properties": {
      "repo_url": {
        "type": "string",
        "description": "Repository URL to review"
      },
      "branch": {
        "type": "string",
        "description": "Branch to review"
      },
      "focus_areas": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Areas to focus on (e.g., security, performance)"
      }
    },
    "additionalProperties": false
  }
}
```

### Structured + Free-Form Agent

For agents that need both structured parameters and free-form input:

```json
{
  "name": "content-writer",
  "description": "Generates content with specific parameters",
  "type": "autonomous",
  "parameters_schema": {
    "type": "object",
    "required": ["topic", "format", "prompt"],
    "properties": {
      "topic": {
        "type": "string",
        "description": "The main topic to write about"
      },
      "format": {
        "type": "string",
        "enum": ["summary", "bullet_points", "essay"],
        "description": "Output format"
      },
      "prompt": {
        "type": "string",
        "description": "Specific instructions for this content"
      }
    },
    "additionalProperties": false
  }
}
```

### System Prompt Integration

Your agent's system prompt should explain the input format:

```markdown
# Agent Instructions

You will receive your inputs in an `<inputs>` block containing all parameters.

The inputs contain:
- **topic**: The main subject to write about
- **format**: The output format (summary, bullet_points, or essay)
- **prompt**: Specific instructions for this content

Follow the format specification exactly.
```

## Complex Types

The schema supports arrays, objects, and nested structures. Complex types are JSON-serialized.

### Array of Strings

Schema:
```json
{
  "focus_areas": {
    "type": "array",
    "items": {"type": "string"}
  }
}
```

Input: `{"focus_areas": ["security", "performance", "readability"]}`

Agent receives:
```
<inputs>
focus_areas: ["security", "performance", "readability"]
</inputs>
```

### Nested Object

Schema:
```json
{
  "config": {
    "type": "object",
    "properties": {
      "timeout": {"type": "integer"},
      "options": {
        "type": "object",
        "properties": {
          "verbose": {"type": "boolean"}
        }
      }
    }
  }
}
```

Input: `{"config": {"timeout": 30, "options": {"verbose": true}}}`

Agent receives:
```
<inputs>
config: {"timeout": 30, "options": {"verbose": true}}
</inputs>
```

### Array of Objects

Schema:
```json
{
  "tasks": {
    "type": "array",
    "items": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "steps": {"type": "array", "items": {"type": "string"}}
      }
    }
  }
}
```

Input: `{"tasks": [{"name": "build", "steps": ["compile", "test"]}]}`

Agent receives:
```
<inputs>
tasks: [{"name": "build", "steps": ["compile", "test"]}]
</inputs>
```

**Note:** Complex types are JSON-serialized on a single line. For large nested structures, consider whether the agent's system prompt should explain how to parse these values.

## API Usage

### Starting an Agent

**Structured-only agent:**
```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "agent_name": "code-reviewer",
    "parameters": {
      "repo_url": "https://github.com/example/repo",
      "branch": "main",
      "focus_areas": ["security", "performance"]
    }
  }'
```

**Structured + prompt agent:**
```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "agent_name": "content-writer",
    "parameters": {
      "topic": "Machine Learning",
      "format": "bullet_points",
      "prompt": "Focus on recent breakthroughs"
    }
  }'
```

### Validation Errors

If parameters don't match the schema:

```json
{
  "error": "parameter_validation_failed",
  "message": "Parameters do not match agent's parameters_schema",
  "agent_name": "content-writer",
  "validation_errors": [
    {
      "path": "$.format",
      "message": "'invalid' is not one of ['summary', 'bullet_points', 'essay']",
      "schema_path": "properties.format.enum"
    }
  ],
  "parameters_schema": { ... }
}
```

### Resuming Sessions

Resume always uses `{prompt: "..."}` regardless of the agent's custom schema. The custom schema only applies to `start_session`.

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "resume_session",
    "session_id": "ses_abc123",
    "parameters": {
      "prompt": "Can you expand on the security section?"
    }
  }'
```

See [ADR-015: Resume Behavior](../adr/ADR-015-autonomous-agent-input-schema.md#resume-behavior-prompt-only) for the rationale.

## Dashboard Usage

1. Navigate to **Agents** and select an agent to edit
2. Toggle **Custom Input Schema** to enable
3. Define your JSON Schema in the editor
4. Click **Save**

The dashboard provides:
- JSON Schema editor with syntax highlighting
- Schema validation before saving
- Prettify button for formatting

**Note:** If your agent needs free-form user input, add a `prompt` field to your schema explicitly.

## Backward Compatibility

- Existing agents without `parameters_schema` continue to work unchanged
- They use the implicit schema: `{"prompt": string}`
- No migration required for existing agents

## References

- [ADR-015: Autonomous Agent Input Schema Handling](../adr/ADR-015-autonomous-agent-input-schema.md) - Design rationale and decision record
