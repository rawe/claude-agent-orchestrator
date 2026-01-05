# Unified Task Model: Architectural Overview

**Status:** Design Proposal
**Date:** 2025-01-05

---

## Problem Statement

The Agent Orchestrator framework needs to support **deterministic task execution** alongside AI agents, with **predictable, structured outputs** for integration with external systems.

Three core challenges:

| Challenge | Description |
|-----------|-------------|
| **Structured Output** | Callers need guaranteed JSON Schema-compliant responses from agents |
| **Task Type Asymmetry** | AI agents and deterministic tasks have different invocation models |
| **Type-Safe Orchestration** | Orchestrating agents need predictable interfaces to chain tasks |

---

## Solution: The Unified Task Model

### Core Principle

**All tasks are functions with typed inputs and outputs.**

```
Every task:  parameters_schema → invoke() → output_schema
```

Whether AI, deterministic, or hybrid - the caller sees the same interface.

### Key Insight: Prompt Is Just a Parameter

AI agents aren't "unstructured" - they're structured with a simple schema:

```json
{
  "parameters_schema": {
    "type": "object",
    "required": ["prompt"],
    "properties": {
      "prompt": { "type": "string" }
    }
  }
}
```

This unifies the invocation model:

```python
# Same signature for ALL task types
invoke(task_name, parameters) → result
```

---

## Architecture Summary

### 1. Bidirectional Schemas

Every task defines both input and output contracts:

```
┌────────────────────┐                     ┌────────────────────┐
│  parameters_schema │ ──── invoke() ────► │   output_schema    │
│   (INPUT contract) │                     │  (OUTPUT contract) │
└────────────────────┘                     └────────────────────┘
```

### 2. Schema Enforcement

| Task Type | Input Validation | Output Validation | On Failure |
|-----------|-----------------|-------------------|------------|
| AI Agent | Validate parameters | Validate result | **Retry with feedback** |
| Deterministic | Validate parameters | Validate result | **Fail immediately** |

AI agents get a retry loop; deterministic tasks fail fast (bugs don't fix themselves).

### 3. The Structuredness Spectrum

```
Minimal                          Moderate                         Full
   │                                │                               │
   ▼                                ▼                               ▼
┌──────────┐                 ┌─────────────┐                ┌─────────────┐
│ AI Agent │                 │  AI Agent + │                │Deterministic│
│ (prompt) │                 │   Context   │                │    Task     │
└──────────┘                 └─────────────┘                └─────────────┘
params:                      params:                         params:
  { prompt }                   { prompt,                       { url,
                                 context,                        depth,
                                 constraints }                   patterns }
```

Tasks exist anywhere on this spectrum. The framework treats them uniformly.

---

## Enforcement Mechanism

### For AI Agents: Validation Loop

```
1. Inject schema requirements into prompt
2. Execute agent
3. Validate output against schema
4. If invalid AND retries remain → Resume with feedback
5. If invalid AND no retries → Fail
6. If valid → Return structured result
```

### For Deterministic Tasks: Validate-or-Fail

```
1. Validate parameters against parameters_schema
2. Execute task
3. Parse stdout as JSON
4. Validate against output_schema
5. If invalid → Fail (it's a bug)
6. If valid → Return structured result
```

---

## API Design

### Unified Invocation

```python
# Single signature for all task types
result = start_agent_session(
    agent_name="any-task",
    parameters={...}  # Validated against parameters_schema
)
# result validated against output_schema
```

### Schema Discovery

```
GET /agents/{name}/schema
→ {
    parameters_schema: {...},  # What it accepts
    output_schema: {...}       # What it produces
  }
```

### Caller-Provided Output Schema

```python
# Override or specify output schema per-run
result = start_agent_session(
    agent_name="analyzer",
    parameters={"prompt": "Analyze code"},
    output_schema={...}  # Caller's requirement
)
```

---

## Benefits

| Aspect | Before | After |
|--------|--------|-------|
| **Invocation** | Different APIs for AI vs deterministic | Unified `parameters` interface |
| **AI inputs** | Just a prompt string | Structured with optional context |
| **Outputs** | Unstructured text | Schema-validated JSON |
| **Orchestration** | Parse and hope | Type-safe chaining |
| **Pipeline composition** | Manual validation | Framework-verified compatibility |

---

## Implementation Phases

1. **Structured Output Enforcement** - Add `output_schema` to runs, validation loop for AI
2. **Deterministic Output Schemas** - Extend deterministic blueprints with `output_schema`
3. **Unified Parameters Model** - Migrate AI agents to `parameters` with implicit schema
4. **Rich AI Inputs** - Enable `parameters_schema` for AI agents beyond just prompt

---

## Detailed References

| Topic | Document |
|-------|----------|
| Structured output enforcement mechanism | [structured-output-schema-enforcement.md](./structured-output-schema-enforcement.md) |
| Deterministic task execution design | [deterministic-task-execution.md](./deterministic-task-execution.md) |
| Synergy analysis and unified model details | [notes-structured-output-deterministic-synergy.md](./notes-structured-output-deterministic-synergy.md) |

---

## Key Takeaways

1. **Everything is structured** - AI agents just have simpler schemas
2. **Schemas are bidirectional** - Both input AND output are typed
3. **Enforcement differs by task type** - AI retries, deterministic fails fast
4. **Caller controls output schema** - Not baked into blueprints
5. **Executor type is hidden** - Callers don't care if task is AI or deterministic
