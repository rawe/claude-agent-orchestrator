# Unified Task Model: Architectural Overview

**Status:** Partially Implemented
**Date:** 2025-01-05
**Updated:** 2025-01-10

---

## Implementation Status

| Component | Status | Reference |
|-----------|--------|-----------|
| Agent Types (autonomous/procedural) | **Implemented** | [architecture/agent-types.md](../architecture/agent-types.md) |
| Unified Parameters Model | **Implemented** | [architecture/agent-types.md](../architecture/agent-types.md) |
| Input Schema Validation | **Implemented** | [architecture/agent-types.md](../architecture/agent-types.md) |
| Output Schema Enforcement | Design | [structured-output-schema-enforcement.md](./structured-output-schema-enforcement.md) |

---

## Problem Statement

The Agent Orchestrator framework needs to support **deterministic task execution** alongside AI agents, with **predictable, structured outputs** for integration with external systems.

Three core challenges:

| Challenge | Description | Status |
|-----------|-------------|--------|
| **Task Type Asymmetry** | AI agents and deterministic tasks have different invocation models | **Solved** |
| **Structured Output** | Callers need guaranteed JSON Schema-compliant responses from agents | Design |
| **Type-Safe Orchestration** | Orchestrating agents need predictable interfaces to chain tasks | Partial |

---

## Solution: The Unified Task Model

### Core Principle

**All tasks are functions with typed inputs and outputs.**

```
Every task:  parameters_schema → invoke() → output_schema
             ─────────────────────────────   ─────────────
                    IMPLEMENTED                 DESIGN
```

Whether AI, deterministic, or hybrid - the caller sees the same interface.

### Key Insight: Prompt Is Just a Parameter

**Status: Implemented** - See [agent-types.md](../architecture/agent-types.md)

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
│    IMPLEMENTED     │                     │      DESIGN        │
└────────────────────┘                     └────────────────────┘
```

### 2. Schema Enforcement

| Task Type | Input Validation | Output Validation | On Failure |
|-----------|-----------------|-------------------|------------|
| AI Agent | **Implemented** | Design | **Retry with feedback** |
| Procedural | **Implemented** | Design | **Fail immediately** |

AI agents get a retry loop; deterministic tasks fail fast (bugs don't fix themselves).

### 3. The Structuredness Spectrum

```
Minimal                          Moderate                         Full
   │                                │                               │
   ▼                                ▼                               ▼
┌──────────┐                 ┌─────────────┐                ┌─────────────┐
│ AI Agent │                 │  AI Agent + │                │ Procedural  │
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

### For AI Agents: Validation Loop (Design)

```
1. Inject schema requirements into prompt
2. Execute agent
3. Validate output against schema
4. If invalid AND retries remain → Resume with feedback
5. If invalid AND no retries → Fail
6. If valid → Return structured result
```

### For Procedural Tasks: Validate-or-Fail

```
1. Validate parameters against parameters_schema  ← IMPLEMENTED
2. Execute task                                    ← IMPLEMENTED
3. Parse stdout as JSON                            ← IMPLEMENTED
4. Validate against output_schema                  ← DESIGN
5. If invalid → Fail (it's a bug)
6. If valid → Return structured result
```

---

## API Design

### Unified Invocation (Implemented)

```python
# Single signature for ALL task types
result = start_agent_session(
    agent_name="any-task",
    parameters={...}  # Validated against parameters_schema
)
# result validated against output_schema  ← DESIGN
```

### Schema Discovery (Design)

```
GET /agents/{name}/schema
→ {
    parameters_schema: {...},  # What it accepts
    output_schema: {...}       # What it produces
  }
```

### Caller-Provided Output Schema (Design)

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
| **Invocation** | Different APIs for AI vs deterministic | Unified `parameters` interface (**Implemented**) |
| **AI inputs** | Just a prompt string | Structured with optional context (**Implemented**) |
| **Outputs** | Unstructured text | Schema-validated JSON (Design) |
| **Orchestration** | Parse and hope | Type-safe chaining (Partial) |
| **Pipeline composition** | Manual validation | Framework-verified compatibility (Design) |

---

## Implementation Phases

1. ~~**Unified Parameters Model** - Migrate AI agents to `parameters` with implicit schema~~ **Done**
2. ~~**Input Schema Validation** - Validate parameters at run creation~~ **Done**
3. **Structured Output Enforcement** - Add `output_schema` to runs, validation loop for AI
4. **Rich AI Inputs** - Enable `parameters_schema` for AI agents beyond just prompt

---

## Detailed References

| Topic | Document |
|-------|----------|
| Agent types architecture | [../architecture/agent-types.md](../architecture/agent-types.md) |
| Structured output enforcement mechanism | [structured-output-schema-enforcement.md](./structured-output-schema-enforcement.md) |

---

## Key Takeaways

1. **Everything is structured** - AI agents just have simpler schemas
2. **Input schemas are enforced** - Parameter validation at run creation (**Implemented**)
3. **Output schemas are planned** - Retry loop for AI, fail-fast for procedural (Design)
4. **Caller controls output schema** - Not baked into blueprints (Design)
5. **Executor type is hidden** - Callers don't care if task is AI or procedural (**Implemented**)
