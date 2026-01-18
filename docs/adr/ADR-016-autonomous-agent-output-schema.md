# ADR-016: Autonomous Agent Output Schema

**Status:** Accepted
**Date:** 2026-01-18
**Implemented:** 2026-01-18
**Decision Makers:** Architecture Review

## Context

Autonomous agents currently return unstructured text in `result_text`. This creates challenges for:

- **Multi-agent orchestration**: Parent agents must parse free-form text to extract structured data
- **Pipeline integration**: Downstream systems can't rely on predictable output formats
- **Data aggregation**: No validation or contract for output structure

We want to extend autonomous agents to support **custom output schemas** - structured JSON responses validated before completion.

### Related Decision

This complements ADR-015 (Autonomous Agent Input Schema), creating symmetric input/output contracts for autonomous agents.

## Decision

Add `output_schema` field to agent blueprints. Schema is:

- **Defined by agent designer** (not caller) in the blueprint
- **Enforced by executor** on every run (start and resume)
- **Validated with JSON Schema Draft-7**
- **Retried once** on validation failure

### Validation Location

Validation happens in the **executor**, not coordinator. Rationale:

- Executor has live AI session for re-prompting
- No coordinator complexity for retry orchestration
- Caller sees only valid results or failures

### System Prompt Enrichment

When `output_schema` is defined, the executor enriches the system prompt with JSON format instructions:

```markdown
## Required Output Format

You MUST provide structured output as JSON conforming to this schema:
<schema>

Your final response MUST be valid JSON that matches this schema exactly.
```

### Result Fields

Two mutually exclusive result fields:

| Field | Used When | Contains |
|-------|-----------|----------|
| `result_text` | No `output_schema` | AI-generated text |
| `result_data` | With `output_schema` | Validated JSON object |

### Retry Behavior

On validation failure:

1. Extract validation errors
2. Send error prompt: "Your output did not match the required schema. [errors]. Please provide output matching the schema."
3. Receive new response
4. Validate again
5. After 1 retry: fail run with `OutputSchemaValidationError`

### Callback Behavior

When a child with `output_schema` completes, the parent callback receives:

- `result_data` formatted as JSON (if present)
- `result_text` directly (if no `result_data`)

This prioritizes structured output for multi-agent orchestration.

## Rationale

### Why blueprint-defined (not caller-defined)?

- Agent designer knows the output format requirements
- Consistent with `parameters_schema` (input validation)
- Callers rely on the contract, don't define it

### Why executor-level validation?

Alternative: Coordinator validates after run completion

**Rejected because:**
- No ability to retry (session is closed)
- Would require coordinator to maintain AI session state
- Executor already handles the live session

### Why 1 retry?

- Balances cost vs success rate
- Single retry handles most format errors
- More retries unlikely to succeed if first retry fails
- Keeps latency predictable

## Consequences

### Positive

- **Predictable outputs** for multi-agent orchestration
- **Input/output contracts** match (`parameters_schema` + `output_schema`)
- **Consistent** with procedural agents (which already produce `result_data`)
- **Validated** outputs reduce downstream parsing errors

### Negative

- **Agent designer responsibility**: Must craft system prompts that reliably produce JSON
- **Retry overhead**: Failed validation costs one additional AI call
- **Not guaranteed**: 1 retry may not always recover from validation failures

### Neutral

- **Backward compatible**: Agents without `output_schema` work unchanged
- **Same API surface**: Uses existing `result_text`/`result_data` fields

## References

- [ADR-015: Autonomous Agent Input Schema](./ADR-015-autonomous-agent-input-schema.md)
- [Feature: Autonomous Agent Output Schema](../features/autonomous-agent-output-schema.md)
- JSON Schema specification: https://json-schema.org/
