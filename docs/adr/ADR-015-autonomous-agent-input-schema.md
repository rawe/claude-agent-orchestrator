# ADR-015: Autonomous Agent Input Schema Handling

**Status:** Accepted
**Date:** 2026-01-10
**Implemented:** 2026-01-10
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

### Resume Behavior: Prompt-Only

**Custom schemas apply only to `start_session`. Resume sessions always accept prompt-only input.**

| Run Type | Agent Has Custom Schema | Validation Schema |
|----------|------------------------|-------------------|
| `start_session` | No | `{prompt: string}` (implicit) |
| `start_session` | Yes | Full custom schema |
| `resume_session` | No | `{prompt: string}` (implicit) |
| `resume_session` | Yes | `{prompt: string}` (implicit) |

**Rationale: Configure vs. Converse**

Starting and resuming serve fundamentally different purposes:

- **Start** = Configure agent context and constraints
  - Like hiring a specialist with a brief: "Write about AI ethics, bullet points, max 100 words"
  - The custom schema defines this initial configuration

- **Resume** = Continue conversation within established context
  - Like talking to that specialist afterward: "Can you expand on the privacy point?"
  - Free-form prompts are natural here; reconfiguring would be confusing

**Why this makes sense:**

1. **Initial parameters establish context**: The custom schema (`topic`, `format`, `max_words`) sets up the agent's working constraints at session start

2. **Resume is conversational**: Follow-up interactions are naturally free-form - users ask clarifying questions, request changes, or continue the dialogue

3. **Avoid reconfiguration confusion**: If resume required the original schema, you'd essentially be restarting the agent with new parameters. The previous output would be awkward to reconcile.

4. **Client simplicity**: All clients (dashboard, MCP, run client) send `{prompt: "..."}` on resume. This matches user expectations for chat-like interactions.

**Example Flow:**

```
# Start: Structured configuration
POST /runs
{
  "type": "start_session",
  "agent_name": "content-writer",
  "parameters": {"topic": "AI Safety", "format": "essay", "max_words": 500}
}
→ Validated against custom schema ✓
→ Agent receives: <inputs>topic: AI Safety...</inputs>

# Resume: Conversational follow-up
POST /runs
{
  "type": "resume_session",
  "session_id": "ses_abc123",
  "parameters": {"prompt": "Now focus more on the regulatory aspects"}
}
→ Validated against implicit schema {prompt: string} ✓
→ Agent receives: "Now focus more on the regulatory aspects"
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
- **Natural Resume UX**: Resume is always conversational (prompt-only), matching user expectations

### Negative

- **Designer Responsibility**: Must remember to add `prompt` if free-form input is desired
- **Breaking Change**: Cannot accidentally rely on implicit `prompt` with custom schemas

### Neutral

- **Backward Compatibility**: Agents without `parameters_schema` work identically
- **Documentation**: System prompts should explain how `<inputs>` block works
- **Resume Simplicity**: Custom schema is only for initial configuration, not follow-ups

## References

- JSON Schema specification: https://json-schema.org/
