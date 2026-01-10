# ADR-015: Autonomous Agent Input Schema Handling

**Status:** Proposed
**Date:** 2026-01-10
**Decision Makers:** Architecture Review

## Context

The Agent Orchestrator framework supports two types of agents:

- **Procedural agents**: Execute deterministic scripts with structured parameters defined by `parameters_schema`
- **Autonomous agents**: AI-powered agents that interpret user intent via a `prompt` string

Currently, autonomous agents accept only `{"prompt": "..."}` as input. We want to extend autonomous agents to support **custom input schemas** - structured parameters beyond a simple prompt.

### Use Cases

1. **Structured inputs**: An agent that generates content might need `topic`, `format`, and `max_words` as distinct, validated fields
2. **Self-documenting agents**: Clear parameter requirements visible to orchestrating agents
3. **Input validation**: Validate inputs before starting expensive AI sessions

### Design Question

When an autonomous agent defines a custom `parameters_schema`, how should we handle the relationship between the custom schema and the traditional `prompt` field?

## Decision

**The custom schema is authoritative.** When an autonomous agent defines a `parameters_schema`, that schema alone determines what parameters are required and validated.

### Two Modes of Operation

**Mode A: No `parameters_schema` defined (default)**

- Implicit schema: `{"type": "object", "required": ["prompt"], "properties": {"prompt": {"type": "string", "minLength": 1}}}`
- Input: `{"prompt": "user's request"}`
- Agent receives: the prompt string directly

**Mode B: `parameters_schema` IS defined**

- Validation: Use the schema exactly as specified
- Input: Whatever matches the schema
- Agent receives: All fields formatted as an `<inputs>` XML block
- The `prompt` field is NOT automatically required - it's the agent designer's choice

### Input Formatting

When a custom schema is defined, all parameters are formatted consistently:

```
<inputs>
field1: value1
field2: value2
</inputs>
```

If the designer includes `prompt` in their schema, it appears in the `<inputs>` block like any other field - no special treatment.

### Examples

**Structured-only agent** (agent knows what to do from parameters alone):
```json
{
  "parameters_schema": {
    "type": "object",
    "required": ["repo_url", "branch"],
    "properties": {
      "repo_url": {"type": "string"},
      "branch": {"type": "string"}
    }
  }
}
```

Input: `{"repo_url": "https://github.com/...", "branch": "main"}`

Agent receives:
```
<inputs>
repo_url: https://github.com/...
branch: main
</inputs>
```

**Structured + free-form agent** (designer explicitly includes `prompt`):
```json
{
  "parameters_schema": {
    "type": "object",
    "required": ["topic", "prompt"],
    "properties": {
      "topic": {"type": "string"},
      "format": {"type": "string", "enum": ["summary", "essay"]},
      "prompt": {"type": "string", "description": "Specific instructions"}
    }
  }
}
```

Input: `{"topic": "AI Safety", "format": "summary", "prompt": "Focus on recent developments"}`

Agent receives:
```
<inputs>
topic: AI Safety
format: summary
prompt: Focus on recent developments
</inputs>
```

## Rationale

### Why NOT automatically require `prompt`?

**Option A (rejected): Always merge `prompt` into custom schemas**
- Force all autonomous agents to accept `prompt` even with custom schema
- Pros: Consistent with default behavior
- Cons:
  - Schema returned by API differs from schema used for validation (confusing)
  - Some agents genuinely don't need free-form input
  - Mixed formatting: structured fields in `<inputs>` block, prompt appended separately

**Option B (selected): Custom schema is authoritative**
- Schema defines exactly what's validated - no hidden additions
- Pros:
  - Schema transparency: what you see = what you validate
  - Agent designer autonomy: they choose if `prompt` is needed
  - Consistent formatting: all fields in `<inputs>` block
  - Simple mental model for orchestrating agents
- Cons:
  - Designer must explicitly add `prompt` if they want free-form input

### Why the `<inputs>` XML block format?

- Clear separation between structured inputs and agent's system context
- AI models handle XML-like delimiters reliably
- System prompt can reference `<inputs>` to explain field meanings
- Easy to parse for debugging

## Consequences

### Positive

- **Schema Transparency**: API returns exactly what will be validated
- **Flexibility**: Agent designers choose their input contract
- **Consistent Formatting**: All custom schema fields handled identically
- **Clear Contract**: Orchestrating agents see requirements without hidden surprises

### Negative

- **Designer Responsibility**: Must remember to add `prompt` if free-form input is desired
- **Breaking Change**: Cannot accidentally rely on implicit `prompt` with custom schemas

### Neutral

- **Backward Compatibility**: Agents without `parameters_schema` work identically
- **Documentation**: System prompts should explain how `<inputs>` block works

## References

- [Autonomous Agent Input Schema Implementation](../implementation/autonomous-agent-input-schema.md)
