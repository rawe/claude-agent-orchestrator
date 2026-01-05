# Design Notes: Structured Output + Deterministic Task Synergy

**Status:** Design Notes (Internal)
**Date:** 2025-01-05
**Related:**
- [Structured Output Schema Enforcement](./structured-output-schema-enforcement.md)
- [Deterministic Task Execution](./deterministic-task-execution.md)

---

## The Asymmetry Problem

The current deterministic task design has an asymmetry:

```
Current State:
┌─────────────────────────────────────────────────────────────────────┐
│  AI Agent:       prompt (unstructured) → result (unstructured)      │
│  Deterministic:  parameters (STRUCTURED) → result (UNSTRUCTURED)    │
└─────────────────────────────────────────────────────────────────────┘
```

Deterministic tasks have **structured input** via `parameters_schema`, but their output is just raw stdout captured as `result_text`. This creates a gap when:

1. An AI orchestrator needs to process deterministic task results
2. Tasks need to be chained in pipelines
3. External systems need predictable data formats

---

## The Unified Type System

With structured output enforcement, we achieve symmetry:

```
With Structured Output:
┌─────────────────────────────────────────────────────────────────────┐
│  AI Agent:       prompt (unstructured) → result (STRUCTURED)        │
│  Deterministic:  parameters (STRUCTURED) → result (STRUCTURED)      │
└─────────────────────────────────────────────────────────────────────┘
```

Both task types now have typed outputs. This creates a **complete type system** for the framework.

---

## Key Insight: Bidirectional Schemas for Deterministic Tasks

Extending the deterministic blueprint with `output_schema`:

```json
{
  "name": "web-crawler",
  "description": "Crawls websites to specified depth",
  "command": "python -m crawler.main",
  "parameters_schema": {
    "type": "object",
    "required": ["url"],
    "properties": {
      "url": { "type": "string", "format": "uri" },
      "depth": { "type": "integer", "default": 2 }
    }
  },
  "output_schema": {
    "type": "object",
    "required": ["pages_crawled", "data"],
    "properties": {
      "pages_crawled": { "type": "integer" },
      "data": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "url": { "type": "string" },
            "title": { "type": "string" },
            "content": { "type": "string" }
          }
        }
      }
    }
  }
}
```

**This gives deterministic tasks a complete contract:**
- `parameters_schema`: What they accept (INPUT)
- `output_schema`: What they produce (OUTPUT)

---

## Different Validation Semantics

Critical distinction between AI and deterministic validation:

| Aspect | AI Agent | Deterministic Task |
|--------|----------|-------------------|
| **Output unpredictability** | High (AI-generated) | None (programmed) |
| **Validation purpose** | Enforcement | Quality assurance |
| **On validation failure** | Retry with feedback | Fail immediately |
| **Retry makes sense?** | Yes (AI can correct) | No (bug in task code) |

**For deterministic tasks, output schema validation catches bugs, not behavioral variance.**

If a deterministic task produces output that doesn't match its `output_schema`, the task implementation has a bug. Retrying won't help - the developer needs to fix the code.

```python
# Validation behavior
if task.type == "ai_agent":
    if not valid:
        if retry_count < max_retries:
            resume_with_feedback()  # AI can learn and correct
        else:
            fail()
elif task.type == "deterministic":
    if not valid:
        fail_immediately()  # Bug in task, retrying is pointless
```

---

## The AI-to-Deterministic Handoff Problem

When an AI orchestrator needs to call a deterministic task:

```
Orchestrator AI Agent
    │
    │ "I need to crawl example.com to depth 3"
    │
    └─► How does the AI produce valid parameters
        for the deterministic task?
```

**Current problem:** The AI might produce invalid parameters (wrong types, missing required fields) which would cause the deterministic task to fail.

**Solution with structured output:**

```
Orchestrator AI Agent
    │
    ├─► 1. Fetch web-crawler's parameters_schema
    │      GET /agents/web-crawler/schema
    │      → { parameters_schema: {...} }
    │
    ├─► 2. Use structured output to produce parameters
    │      Internal prompt: "Generate parameters for web-crawler"
    │      output_schema = web-crawler.parameters_schema
    │
    ├─► 3. Receive VALIDATED parameters
    │      { "url": "https://example.com", "depth": 3 }
    │
    └─► 4. Call deterministic task with guaranteed-valid params
        start_agent_session("web-crawler", parameters={...})
```

**The AI uses structured output enforcement to produce valid input for the deterministic task.**

---

## Pipeline Composability

With bidirectional schemas, the framework can verify pipeline type safety:

```
Task A                              Task B
┌─────────────────────┐            ┌─────────────────────┐
│ parameters_schema:  │            │ parameters_schema:  │
│   { url: string }   │            │   { pages: Page[] } │
│                     │            │                     │
│ output_schema:      │───────────►│ output_schema:      │
│   { pages: Page[] } │  MATCHES   │   { report: {...} } │
└─────────────────────┘            └─────────────────────┘
```

**Type compatibility check:**
```
Task_A.output_schema ⊇ Task_B.parameters_schema
```

If Task A's output satisfies Task B's input requirements, the pipeline is type-safe.

---

## Enhanced Schema Discovery

Current schema endpoint:
```
GET /agents/{name}/schema
→ { parameters_schema: {...} }  // INPUT only
```

Enhanced with output schema:
```
GET /agents/{name}/schema
→ {
    type: "deterministic",
    parameters_schema: {...},   // INPUT contract
    output_schema: {...}        // OUTPUT contract
  }
```

For AI agents:
```
GET /agents/{name}/schema
→ {
    type: "agent",
    default_output_schema: {...}  // Optional blueprint default
  }
```

---

## Enhanced Result Model

Current deterministic result:
```json
{
  "result_text": "...(raw stdout)...",
  "exit_code": 0
}
```

Enhanced with structured output:
```json
{
  "result_text": "...(raw stdout)...",
  "exit_code": 0,
  "result_data": {
    "pages_crawled": 42,
    "data": [
      {"url": "...", "title": "...", "content": "..."},
      ...
    ]
  },
  "output_validation": {
    "valid": true,
    "schema_used": "web-crawler-output",
    "validation_errors": []
  }
}
```

- `result_text`: Raw stdout (preserved for debugging/logging)
- `result_data`: Parsed and validated JSON (for programmatic use)
- `output_validation`: Validation metadata

---

## The Type-Safe Bridge Architecture

Structured output creates a bridge between AI and deterministic worlds:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Type-Safe Orchestration                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────┐                      ┌─────────────────────────┐   │
│  │   AI Agent      │                      │   Deterministic Task    │   │
│  │                 │                      │                         │   │
│  │  prompt → ...   │                      │  params_schema → exec   │   │
│  │                 │                      │                         │   │
│  │  ... → output   │                      │  exec → output_schema   │   │
│  │  (enforced via  │                      │  (validated, no retry)  │   │
│  │   retry loop)   │                      │                         │   │
│  └────────┬────────┘                      └────────────┬────────────┘   │
│           │                                            │                 │
│           │    ┌──────────────────────────────────┐    │                 │
│           │    │   Schema Compatibility Layer     │    │                 │
│           └───►│                                  │◄───┘                 │
│                │  • Validates AI output can feed  │                      │
│                │    deterministic input           │                      │
│                │  • Validates deterministic output│                      │
│                │    matches AI expectations       │                      │
│                │  • Enables pipeline composition  │                      │
│                └──────────────────────────────────┘                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## The "Contract" Concept

With bidirectional schemas, each task has a formal CONTRACT:

```
┌────────────────────────────────────────────────────────────────┐
│  Task Contract: web-crawler                                     │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  INPUT CONTRACT (parameters_schema):                            │
│    REQUIRES:                                                    │
│      - url: string, format=uri                                  │
│    ACCEPTS:                                                     │
│      - depth: integer (default: 2)                              │
│      - patterns: string[] (optional)                            │
│                                                                 │
│  OUTPUT CONTRACT (output_schema):                               │
│    GUARANTEES:                                                  │
│      - pages_crawled: integer                                   │
│      - data: array of Page objects                              │
│    WHERE Page:                                                  │
│      - url: string                                              │
│      - title: string                                            │
│      - content: string                                          │
│                                                                 │
│  INVARIANTS:                                                    │
│    - If input satisfies INPUT CONTRACT                          │
│    - AND exit_code == 0                                         │
│    - THEN output satisfies OUTPUT CONTRACT                      │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

This is essentially **Design by Contract** applied to distributed task execution.

---

## Self-Describing Tasks

With complete schemas, tasks become fully self-describing:

```
┌─────────────────────────────────────────────────────────────────┐
│  Discovery Flow                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Orchestrator: "What tasks are available?"                    │
│     GET /agents                                                  │
│     → [                                                          │
│         {name: "web-crawler", type: "deterministic", ...},       │
│         {name: "ai-analyzer", type: "agent", ...}                │
│       ]                                                          │
│                                                                  │
│  2. Orchestrator: "What does web-crawler accept/produce?"        │
│     GET /agents/web-crawler/schema                               │
│     → {                                                          │
│         parameters_schema: {...},  // What it needs              │
│         output_schema: {...}       // What it gives              │
│       }                                                          │
│                                                                  │
│  3. Orchestrator can now:                                        │
│     - Generate valid parameters using structured output          │
│     - Know exactly what result format to expect                  │
│     - Validate compatibility with downstream tasks               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**AI orchestrators can dynamically discover and correctly invoke any task without hardcoded knowledge.**

---

## Executor Changes for Deterministic Tasks

The deterministic executor gains output validation:

```python
# ao-deterministic-exec (enhanced)

def execute(invocation):
    # 1. Run the command
    result = subprocess.run(
        build_command(invocation.command, invocation.parameters),
        capture_output=True
    )

    # 2. If output_schema defined, validate stdout
    if invocation.output_schema:
        try:
            parsed = json.loads(result.stdout)
            validation = validate_schema(parsed, invocation.output_schema)

            if not validation.valid:
                # Don't retry - this is a bug
                report_failed(
                    session_id=invocation.session_id,
                    error=f"Output schema violation: {validation.errors}",
                    result_text=result.stdout
                )
                return

            report_completed(
                session_id=invocation.session_id,
                result_text=result.stdout,
                result_data=parsed,  # Validated JSON
                exit_code=result.returncode
            )
        except json.JSONDecodeError as e:
            report_failed(
                session_id=invocation.session_id,
                error=f"Output is not valid JSON: {e}",
                result_text=result.stdout
            )
    else:
        # No schema - raw result as before
        report_completed(
            session_id=invocation.session_id,
            result_text=result.stdout,
            exit_code=result.returncode
        )
```

---

## Pipeline Definition Vision (Future)

With complete type information, declarative pipelines become possible:

```yaml
pipeline: security-audit
description: Full security scan with AI-powered analysis

steps:
  - name: scan
    task: code-scanner        # deterministic
    parameters:
      target: $input.repository
      rules: ["owasp-top-10", "cwe-25"]
    output: $scan_results
    # Framework knows: output matches code-scanner.output_schema

  - name: analyze
    task: ai-security-analyst  # AI agent
    prompt: |
      Analyze these scan results and identify critical vulnerabilities.
      Focus on exploitability and business impact.
    input: $scan_results
    output_schema:
      type: object
      required: [critical_findings, risk_score]
      properties:
        critical_findings: { type: array }
        risk_score: { type: number, minimum: 0, maximum: 10 }
    output: $analysis
    # Framework enforces: AI output matches this schema

  - name: report
    task: report-generator    # deterministic
    parameters:
      findings: $analysis.critical_findings
      score: $analysis.risk_score
      raw_scan: $scan_results
    output: $final_report
    # Framework validates: parameters match report-generator.parameters_schema

# Framework can validate at definition time:
# - scan.output_schema compatible with analyze.input expectations
# - analyze.output_schema compatible with report.parameters_schema
```

---

## Implementation Implications

### 1. Blueprint Schema Extension

```python
class DeterministicBlueprint(BaseModel):
    name: str
    description: str
    command: str
    parameters_schema: dict          # INPUT (existing)
    output_schema: Optional[dict]    # OUTPUT (new)
```

### 2. Schema Discovery Endpoint Enhancement

```python
@app.get("/agents/{name}/schema")
async def get_agent_schema(name: str):
    agent = get_agent(name)

    if agent.type == "deterministic":
        return {
            "type": "deterministic",
            "parameters_schema": agent.parameters_schema,
            "output_schema": agent.output_schema  # NEW
        }
    else:
        return {
            "type": "agent",
            "default_output_schema": agent.default_output_schema
        }
```

### 3. Result Storage Enhancement

```sql
-- Enhanced sessions table
ALTER TABLE sessions ADD COLUMN result_data TEXT;      -- Validated JSON
ALTER TABLE sessions ADD COLUMN output_schema TEXT;    -- Schema used
ALTER TABLE sessions ADD COLUMN validation_result TEXT; -- Validation metadata
```

### 4. MCP Server Type Awareness

```python
@tool
def start_agent_session(
    agent_name: str,
    # For AI agents:
    prompt: Optional[str] = None,
    output_schema: Optional[dict] = None,
    # For deterministic tasks:
    parameters: Optional[dict] = None,
) -> dict:
    """
    Unified interface for both AI agents and deterministic tasks.

    The task type determines which parameters are used:
    - AI agent: prompt + optional output_schema
    - Deterministic: parameters (validated against parameters_schema)

    Both can produce structured output via output_schema.
    """
```

---

## Summary: The Synergy

| Aspect | Before | After |
|--------|--------|-------|
| **Deterministic output** | Raw text | Structured, validated |
| **AI→Deterministic handoff** | Error-prone | Type-safe |
| **Task discovery** | Partial (input only) | Complete (input+output) |
| **Pipeline composition** | Manual validation | Framework-verified |
| **Error diagnosis** | "Task failed" | "Schema violation at $.field" |
| **Contract enforcement** | None | Design by Contract |

**The structured output feature transforms deterministic task execution from a "fire and pray" model to a type-safe, contract-driven system.**

---

## The Inversion: Unified Structured Input Model

### The Conceptual Shift

The current mental model treats AI agents and deterministic tasks as fundamentally different:

```
Current Mental Model:
┌────────────────────────────────────────────────────────────────────┐
│  AI Agent:      prompt (special, unstructured)                     │
│  Deterministic: parameters (structured, schema-validated)          │
└────────────────────────────────────────────────────────────────────┘
```

**The inversion**: What if AI agents aren't "unstructured"? What if they're just structured with a trivial schema?

```
Inverted Mental Model:
┌────────────────────────────────────────────────────────────────────┐
│  AI Agent:      parameters { prompt: string }  ← ALSO STRUCTURED   │
│  Deterministic: parameters { url, depth, ... }                     │
└────────────────────────────────────────────────────────────────────┘
```

**Both are structured. AI agents just have a simpler schema.**

### The Unified Signature

Every task - whether AI or deterministic - has the same invocation signature:

```
invoke(task_name, parameters) → result
```

Where:
- `parameters` is validated against `parameters_schema`
- `result` is validated against `output_schema`

The distinction between AI and deterministic becomes an **implementation detail**, not a caller concern.

### AI Agent as Structured Task

An AI agent's implicit `parameters_schema`:

```json
{
  "type": "object",
  "required": ["prompt"],
  "properties": {
    "prompt": {
      "type": "string",
      "description": "Instructions for the AI agent"
    }
  }
}
```

Invocation becomes:

```python
# Instead of:
start_agent_session(agent_name="researcher", prompt="Research quantum computing")

# We have:
start_agent_session(
    agent_name="researcher",
    parameters={"prompt": "Research quantum computing"}
)
```

### Prompt Is Just Another Parameter

The profound shift: **`prompt` is not special**. It's just a string parameter that happens to be interpreted by an AI model.

This opens up powerful possibilities:

#### 1. Rich Input Schemas for AI Agents

AI agents can accept structured context alongside the prompt:

```json
{
  "name": "code-reviewer",
  "type": "agent",
  "parameters_schema": {
    "type": "object",
    "required": ["prompt"],
    "properties": {
      "prompt": {
        "type": "string",
        "description": "Review instructions"
      },
      "files": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Specific files to review"
      },
      "focus_areas": {
        "type": "array",
        "items": {
          "type": "string",
          "enum": ["security", "performance", "maintainability", "testing"]
        }
      },
      "severity_threshold": {
        "type": "string",
        "enum": ["info", "warning", "error"],
        "default": "warning"
      }
    }
  },
  "output_schema": { ... }
}
```

Invocation:

```json
{
  "agent_name": "code-reviewer",
  "parameters": {
    "prompt": "Review authentication changes",
    "files": ["src/auth/*.ts"],
    "focus_areas": ["security"],
    "severity_threshold": "error"
  }
}
```

#### 2. Input Validation for AI Agents

With a proper schema, we can validate AI agent inputs before execution:

```
Bad input:
  { "prompt": "", "severity_threshold": "extreme" }

Validation errors:
  - $.prompt: String must not be empty
  - $.severity_threshold: 'extreme' is not one of ['info', 'warning', 'error']
```

**Catch errors early, before wasting AI tokens!**

#### 3. Schema-Driven Prompt Construction

The framework can transform structured parameters into an enriched prompt:

```python
def build_prompt(parameters: dict, blueprint: AgentBlueprint) -> str:
    """
    Transform structured parameters into AI prompt.
    """
    prompt = parameters["prompt"]

    # Add structured context to prompt
    if "files" in parameters:
        prompt += f"\n\n## Files to Review\n{format_list(parameters['files'])}"

    if "focus_areas" in parameters:
        prompt += f"\n\n## Focus Areas\n{format_list(parameters['focus_areas'])}"

    if "severity_threshold" in parameters:
        prompt += f"\n\nOnly report issues at {parameters['severity_threshold']} level or above."

    return prompt
```

The caller provides structured data; the framework builds the prompt.

### The Spectrum of Structuredness

Instead of a binary distinction, we have a spectrum:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       THE STRUCTUREDNESS SPECTRUM                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Minimal Structure              Moderate                    Full Structure   │
│        │                           │                              │          │
│        ▼                           ▼                              ▼          │
│  ┌───────────┐            ┌─────────────────┐           ┌─────────────────┐ │
│  │ AI Agent  │            │   AI Agent +    │           │  Deterministic  │ │
│  │ (prompt   │            │   Context       │           │  Task           │ │
│  │  only)    │            │                 │           │                 │ │
│  ├───────────┤            ├─────────────────┤           ├─────────────────┤ │
│  │ params:   │            │ params:         │           │ params:         │ │
│  │  prompt   │            │  prompt         │           │  url            │ │
│  │           │            │  context: {...} │           │  depth          │ │
│  │           │            │  constraints    │           │  patterns       │ │
│  └───────────┘            └─────────────────┘           └─────────────────┘ │
│                                                                              │
│  parameters_schema:       parameters_schema:             parameters_schema:  │
│  { prompt: string }       { prompt: string,              { url: uri,        │
│                             context: object,               depth: int,      │
│                             constraints: object }          patterns: array }│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

Tasks can exist anywhere on this spectrum. The framework treats them uniformly.

### Hybrid Tasks: The Natural Middle Ground

This model naturally enables "hybrid" tasks that combine AI with structured data:

```json
{
  "name": "intelligent-crawler",
  "type": "hybrid",
  "parameters_schema": {
    "type": "object",
    "required": ["url", "extraction_goal"],
    "properties": {
      "url": { "type": "string", "format": "uri" },
      "depth": { "type": "integer", "default": 2 },
      "extraction_goal": {
        "type": "string",
        "description": "What to extract (interpreted by AI)"
      }
    }
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "pages_crawled": { "type": "integer" },
      "extracted_data": { "type": "array" }
    }
  }
}
```

Invocation:
```json
{
  "parameters": {
    "url": "https://example.com/products",
    "depth": 3,
    "extraction_goal": "Extract all product names and prices"
  }
}
```

Is this AI or deterministic? **It's both** - and the caller doesn't need to care.

### Caller-Agnostic Orchestration

The orchestrator treats ALL tasks uniformly:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    UNIFIED ORCHESTRATION FLOW                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. DISCOVER                                                                 │
│     GET /agents/{name}/schema                                                │
│     → { parameters_schema, output_schema, type }                             │
│                                                                              │
│  2. PREPARE                                                                  │
│     Generate/validate parameters against parameters_schema                   │
│     (If orchestrator is AI, use structured output to produce valid params)   │
│                                                                              │
│  3. INVOKE                                                                   │
│     start_agent_session(name, parameters)                                    │
│     ← Same signature for ALL task types                                      │
│                                                                              │
│  4. RECEIVE                                                                  │
│     result validated against output_schema                                   │
│     ← Structured, predictable, type-safe                                     │
│                                                                              │
│  The orchestrator DOES NOT CARE if the task is AI, deterministic, or hybrid. │
│  All tasks are just: parameters_schema → output_schema                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The Complete Unified Task Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         UNIFIED TASK MODEL                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Every task (AI, deterministic, or hybrid) has:                              │
│                                                                              │
│    ┌────────────────────┐                     ┌────────────────────┐        │
│    │  parameters_schema │ ──── invoke() ────► │   output_schema    │        │
│    │   (INPUT contract) │                     │  (OUTPUT contract) │        │
│    └────────────────────┘                     └────────────────────┘        │
│                                                                              │
│  Implementation detail (hidden from caller):                                 │
│    - executor_type: "claude-code" | "deterministic" | "hybrid"               │
│    - For AI: framework may transform parameters → enriched prompt            │
│    - For deterministic: framework passes parameters → CLI args               │
│                                                                              │
│  Caller experience:                                                          │
│    result = invoke(task_name, parameters)                                    │
│    # parameters validated against parameters_schema                          │
│    # result validated against output_schema                                  │
│    # executor_type is INVISIBLE to caller                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Backward Compatibility

For AI agents without explicit `parameters_schema`, use the implicit default:

```python
IMPLICIT_AI_AGENT_SCHEMA = {
    "type": "object",
    "required": ["prompt"],
    "properties": {
        "prompt": {"type": "string"}
    }
}

# Old API still works:
start_agent_session(agent_name="researcher", prompt="...")

# Framework internally converts to:
start_agent_session(
    agent_name="researcher",
    parameters={"prompt": "..."}  # Validated against implicit schema
)
```

### Implications

1. **Uniform API**: Single `parameters` field for all task types
2. **Input validation**: All inputs validated, even for AI agents
3. **Richer AI inputs**: AI agents can accept structured context + constraints
4. **Caller simplicity**: Caller doesn't know/care about executor type
5. **Pipeline composability**: All tasks have same signature, easy to chain
6. **Type-safe orchestration**: Orchestrators work with any task uniformly
7. **Future flexibility**: New executor types (hybrid, external AI) fit naturally

### API Impact

Current API:
```python
# Different signatures for different task types
start_agent_session(agent_name, prompt=...)           # AI
start_agent_session(agent_name, parameters=...)       # Deterministic
```

Unified API:
```python
# Single signature for all task types
start_agent_session(agent_name, parameters=...)       # Everything

# With backward compatibility:
start_agent_session(agent_name, prompt="...")         # Sugar for {"prompt": "..."}
```

### The Mental Model Shift

```
OLD: "AI agents take prompts, deterministic tasks take parameters"
     ↓
NEW: "All tasks take parameters. AI agents just have a simple schema
      where prompt is the main (or only) parameter."
```

This seemingly small shift has profound implications for the architecture:
- It unifies the invocation model
- It enables richer AI agent inputs
- It makes the caller experience uniform
- It allows hybrid tasks naturally
- It simplifies orchestration logic

**The prompt is demoted from "special input type" to "just another parameter that happens to be interpreted by an AI."**

---

## Open Questions

1. **Should deterministic tasks define output_schema in blueprint or separate file?**
   - Blueprint: simpler, single source of truth
   - Separate: allows schema reuse, smaller blueprint files

2. **How to handle deterministic tasks that legitimately produce variable output?**
   - Optional output_schema (current approach)
   - Union types in schema
   - Multiple output schemas with discriminator

3. **Should framework support schema evolution/versioning?**
   - Out of scope for initial implementation
   - Could add `schema_version` field later

4. **Pipeline validation at definition time vs execution time?**
   - Definition time: catches errors early, requires static analysis
   - Execution time: simpler, handles dynamic schemas
