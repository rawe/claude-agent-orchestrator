# Parameters Schema Reference

A reference guide for defining `parameters_schema` in agent blueprints.

## Overview

The `parameters_schema` field in agent blueprints defines what inputs an agent accepts. It uses **JSON Schema (Draft 7)** for validation.

**Where it's used:**
- **Autonomous agents**: Optional custom parameters beyond `prompt` (defined in `config/agents/<name>/agent.json`)
- **Procedural agents**: Required input definition (defined in runner-owned `agent.json`)

**When validation runs:** The Coordinator validates all parameters against the schema before creating a run. Invalid parameters result in a 400 error with detailed validation messages.

---

## Basic Structure

Every `parameters_schema` must be an object type:

```json
{
  "parameters_schema": {
    "type": "object",
    "required": ["field1", "field2"],
    "properties": {
      "field1": { "type": "string" },
      "field2": { "type": "integer" }
    },
    "additionalProperties": false
  }
}
```

**Root-level fields:**
| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | Must be `"object"` |
| `properties` | Yes | Defines each parameter |
| `required` | No | Array of required parameter names |
| `additionalProperties` | No | Set to `false` to reject unknown fields |

---

## Property Types

### String

```json
{
  "name": {
    "type": "string",
    "description": "User's full name"
  }
}
```

**Constraints:**
| Constraint | Example | Description |
|------------|---------|-------------|
| `minLength` | `"minLength": 1` | Minimum character count |
| `maxLength` | `"maxLength": 100` | Maximum character count |
| `pattern` | `"pattern": "^[a-z]+$"` | Regex pattern (ECMA 262) |
| `enum` | `"enum": ["a", "b", "c"]` | Allowed values only |
| `format` | `"format": "email"` | Semantic format hint |

**Common formats:** `email`, `uri`, `date`, `date-time`, `uuid`, `hostname`, `ipv4`, `ipv6`

```json
{
  "email": {
    "type": "string",
    "format": "email"
  },
  "status": {
    "type": "string",
    "enum": ["pending", "active", "completed"]
  },
  "slug": {
    "type": "string",
    "pattern": "^[a-z0-9-]+$",
    "minLength": 3,
    "maxLength": 50
  }
}
```

### Integer

Whole numbers only.

```json
{
  "count": {
    "type": "integer",
    "description": "Number of items"
  }
}
```

**Constraints:**
| Constraint | Example | Description |
|------------|---------|-------------|
| `minimum` | `"minimum": 0` | Minimum value (inclusive) |
| `maximum` | `"maximum": 100` | Maximum value (inclusive) |
| `exclusiveMinimum` | `"exclusiveMinimum": 0` | Minimum value (exclusive) |
| `exclusiveMaximum` | `"exclusiveMaximum": 100` | Maximum value (exclusive) |
| `multipleOf` | `"multipleOf": 5` | Must be divisible by |

```json
{
  "max_words": {
    "type": "integer",
    "minimum": 50,
    "maximum": 2000,
    "description": "Maximum word count"
  },
  "quantity": {
    "type": "integer",
    "minimum": 1,
    "multipleOf": 1
  }
}
```

### Number

Decimal numbers (includes integers).

```json
{
  "temperature": {
    "type": "number",
    "minimum": 0,
    "maximum": 1,
    "description": "Sampling temperature"
  }
}
```

Same constraints as `integer`.

### Boolean

```json
{
  "verbose": {
    "type": "boolean",
    "description": "Enable verbose output"
  }
}
```

### Null

Rarely used alone, typically combined with other types.

```json
{
  "optional_field": {
    "type": ["string", "null"],
    "description": "Can be string or null"
  }
}
```

---

## Required vs Optional

**Required:** Listed in the `required` array - must be provided.

**Optional:** In `properties` but not in `required` - can be omitted.

```json
{
  "type": "object",
  "required": ["topic", "format"],
  "properties": {
    "topic": { "type": "string" },
    "format": { "type": "string" },
    "max_words": { "type": "integer" }
  }
}
```

In this example:
- `topic` and `format` are **required**
- `max_words` is **optional**

**Note for autonomous agents:** The `prompt` field is always required and automatically added by the Coordinator during validation, even if your schema doesn't define it.

---

## Default Values

Use `default` to specify a fallback when a field is omitted:

```json
{
  "depth": {
    "type": "integer",
    "default": 2,
    "minimum": 1,
    "maximum": 10
  }
}
```

**Important:** JSON Schema defaults are for documentation. The validator does not inject defaults - your executor must handle missing optional fields.

---

## Complex Types

### Arrays (Lists)

```json
{
  "tags": {
    "type": "array",
    "items": { "type": "string" },
    "description": "List of tags"
  }
}
```

**Constraints:**
| Constraint | Example | Description |
|------------|---------|-------------|
| `minItems` | `"minItems": 1` | Minimum array length |
| `maxItems` | `"maxItems": 10` | Maximum array length |
| `uniqueItems` | `"uniqueItems": true` | No duplicates allowed |
| `items` | `{"type": "string"}` | Schema for each item |

```json
{
  "urls": {
    "type": "array",
    "items": {
      "type": "string",
      "format": "uri"
    },
    "minItems": 1,
    "maxItems": 50,
    "uniqueItems": true
  }
}
```

**Array of objects:**

```json
{
  "users": {
    "type": "array",
    "items": {
      "type": "object",
      "required": ["name"],
      "properties": {
        "name": { "type": "string" },
        "email": { "type": "string", "format": "email" }
      }
    }
  }
}
```

### Objects (Dictionaries)

Nested objects use the same structure:

```json
{
  "config": {
    "type": "object",
    "required": ["timeout"],
    "properties": {
      "timeout": { "type": "integer", "minimum": 1 },
      "retries": { "type": "integer", "default": 3 }
    }
  }
}
```

**Dynamic keys (dictionary/map):**

Use `additionalProperties` to allow arbitrary keys:

```json
{
  "metadata": {
    "type": "object",
    "additionalProperties": { "type": "string" }
  }
}
```

This accepts: `{"metadata": {"key1": "value1", "key2": "value2"}}`

**Mixed fixed and dynamic keys:**

```json
{
  "headers": {
    "type": "object",
    "properties": {
      "Content-Type": { "type": "string" }
    },
    "additionalProperties": { "type": "string" }
  }
}
```

---

## Advanced Features

### Multiple Types

Allow a field to accept multiple types:

```json
{
  "value": {
    "type": ["string", "integer"]
  }
}
```

### Conditional Fields (oneOf, anyOf)

**oneOf** - exactly one schema must match:

```json
{
  "output": {
    "oneOf": [
      { "type": "string" },
      {
        "type": "object",
        "required": ["format"],
        "properties": {
          "format": { "type": "string" },
          "path": { "type": "string" }
        }
      }
    ]
  }
}
```

**anyOf** - at least one schema must match:

```json
{
  "id": {
    "anyOf": [
      { "type": "string", "format": "uuid" },
      { "type": "integer", "minimum": 1 }
    ]
  }
}
```

### Description

Always add descriptions for documentation:

```json
{
  "topic": {
    "type": "string",
    "description": "The main subject to write about"
  }
}
```

Descriptions appear in:
- API responses (`GET /agents`)
- Dashboard UI
- Validation error messages

---

## Complete Examples

### Autonomous Agent with Custom Parameters

```json
{
  "name": "content-writer",
  "type": "autonomous",
  "description": "Writes content based on structured inputs",
  "parameters_schema": {
    "type": "object",
    "required": ["topic", "format"],
    "properties": {
      "topic": {
        "type": "string",
        "minLength": 1,
        "description": "The main topic to write about"
      },
      "format": {
        "type": "string",
        "enum": ["summary", "bullet_points", "essay", "outline"],
        "description": "Output format"
      },
      "max_words": {
        "type": "integer",
        "minimum": 50,
        "maximum": 2000,
        "description": "Maximum word count (optional)"
      },
      "audience": {
        "type": "string",
        "description": "Target audience (optional)"
      }
    },
    "additionalProperties": false
  }
}
```

**Valid input:**
```json
{
  "prompt": "Write about this topic in detail.",
  "topic": "Machine Learning",
  "format": "bullet_points",
  "max_words": 300
}
```

### Procedural Agent with Complex Parameters

```json
{
  "name": "data-processor",
  "description": "Processes data with configurable options",
  "command": "./process.sh",
  "parameters_schema": {
    "type": "object",
    "required": ["input_file", "operations"],
    "properties": {
      "input_file": {
        "type": "string",
        "description": "Path to input file"
      },
      "operations": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["type"],
          "properties": {
            "type": {
              "type": "string",
              "enum": ["filter", "transform", "aggregate"]
            },
            "config": {
              "type": "object",
              "additionalProperties": true
            }
          }
        },
        "minItems": 1
      },
      "output_format": {
        "type": "string",
        "enum": ["json", "csv", "xml"],
        "default": "json"
      }
    },
    "additionalProperties": false
  }
}
```

---

## Validation Error Response

When validation fails, the API returns:

```json
{
  "error": "parameter_validation_failed",
  "message": "Parameters do not match agent's parameters_schema",
  "agent_name": "content-writer",
  "validation_errors": [
    {
      "path": "$.format",
      "message": "'invalid' is not one of ['summary', 'bullet_points', 'essay', 'outline']",
      "schema_path": "properties.format.enum"
    }
  ],
  "parameters_schema": { ... }
}
```

---

## Implementation Verification

This section helps verify the documentation matches the implementation.

### Library and Specification

- **Library:** `jsonschema` (Python)
- **Validator:** `Draft7Validator`
- **Specification:** JSON Schema Draft 7

### Key Source Files

| File | Purpose |
|------|---------|
| `servers/agent-coordinator/services/run_queue.py` | Parameter validation (`validate_parameters`, `Draft7Validator`) |
| `servers/agent-coordinator/agent_storage.py` | Schema storage/retrieval |
| `servers/agent-coordinator/main.py` | API endpoint calling validation |
| `servers/agent-coordinator/models.py` | `Agent.parameters_schema` field definition |

### Verification Checklist

To verify this documentation:

1. **Check the validator class:**
   ```python
   # In run_queue.py
   from jsonschema import Draft7Validator
   validator = Draft7Validator(schema)
   ```

2. **Check autonomous agent schema merging:**
   ```python
   # In run_queue.py
   def _merge_autonomous_schema_with_prompt(custom_schema: dict) -> dict:
   ```

3. **Check validation entry point:**
   ```python
   # In run_queue.py
   def validate_parameters(parameters: dict, agent: Agent) -> None:
   ```

4. **Supported Draft 7 features:** All standard Draft 7 keywords are supported. See [JSON Schema Draft 7 Specification](https://json-schema.org/specification-links.html#draft-7) for the complete list.

---

## Further Reading

- [JSON Schema Official Documentation](https://json-schema.org/understanding-json-schema/)
- [JSON Schema Draft 7 Specification](https://json-schema.org/draft-07/json-schema-release-notes.html)
- [Python jsonschema Library](https://python-jsonschema.readthedocs.io/)
- [Agent Types Architecture](../architecture/agent-types.md) - How schemas work with different agent types
- [Autonomous Agent Input Schema Implementation](../implementation/autonomous-agent-input-schema.md) - Implementation details
