# Autonomous Agent Input Schema

## Overview

This document describes the implementation of optional custom input schemas for autonomous agents. Previously, autonomous agents only accepted `{"prompt": "..."}` as input. With this feature, autonomous agents can now define additional structured parameters that are validated and formatted into the prompt.

## Implementation Summary

### 1. Coordinator - Parameter Validation (`servers/agent-coordinator/services/run_queue.py`)
- Added `_merge_autonomous_schema_with_prompt()` function that merges custom schemas with the prompt requirement
- Updated `validate_parameters()` to handle three cases:
  - Autonomous agents without schema: Use implicit `{"prompt": string}` schema
  - Autonomous agents with schema: Merge custom schema with prompt requirement
  - Procedural agents: Use schema directly (no prompt required)

### 2. Runner - Input Formatting (`servers/agent-runner/lib/utils.py`)
- Added `format_autonomous_inputs()` function that:
  - Extracts the prompt from parameters
  - Formats additional parameters as an `<inputs>` block
  - Prepends the formatted inputs to the user's prompt

### 3. Executor - Prompt Processing (`servers/agent-runner/executors/claude-code/ao-claude-code-exec`)
- Updated `run_start()` and `run_resume()` to use `format_autonomous_inputs()`
- Logs whether additional inputs were included

### 4. MCP Tool Descriptions (`servers/agent-runner/lib/agent_orchestrator_mcp/tools.py`)
- Updated `list_agent_blueprints()`, `start_agent_session()`, and `resume_agent_session()` with clear documentation about schema handling by agent type

### 5. Dashboard - Input Schema Editor
- Created `InputSchemaEditor.tsx` component with:
  - JSON editor for defining custom schemas
  - Validation for JSON Schema format
  - Prettify button
- Updated `AgentEditor.tsx` with:
  - Enable/disable toggle for custom input schema
  - Conditional display of the schema editor
  - Clear indication that prompt is always required

### 6. Example Agent (`config/agents/parametric-agent/`)
- Created a complete example showing:
  - Custom `parameters_schema` with multiple fields (topic, format, max_words, audience)
  - System prompt explaining how to use the structured inputs

---

## Detailed Implementation

### Design Rationale

#### Why Optional Input Schemas?

The agent orchestration framework supports two types of agents:
- **Procedural agents**: Execute deterministic scripts with structured parameters
- **Autonomous agents**: AI-powered agents that interpret user intent

Previously, procedural agents could define a `parameters_schema` in their `agent.json`, but autonomous agents were limited to a single `prompt` parameter. This created a gap when users wanted:
1. Structured inputs for autonomous agents (e.g., topic, format, constraints)
2. Validation of inputs before starting expensive AI sessions
3. Self-documenting agents with clear parameter requirements

#### Key Design Decisions

##### 1. Schema is `null` vs Non-null (Explicit Activation)

**Decision**: Use `null` as the indicator for "default behavior" rather than a boolean flag.

**Rationale**:
- Simpler storage: One field serves both purposes (enabled state + schema value)
- Clearer semantics: `null` = not configured, non-null = explicitly configured
- Backward compatible: Existing agents without schema continue to work
- Consistent with how procedural agents already work

##### 2. Prompt is Always Required for Autonomous Agents

**Decision**: Always merge `prompt` into the validated schema, even if the agent's custom schema doesn't define it.

**Rationale**:
- Autonomous agents fundamentally need a prompt to know what to do
- Prevents agents from accidentally omitting the prompt requirement
- Consistent user experience: all autonomous agents accept `prompt`
- The merge happens at validation time, not storage time, so the stored schema remains clean

##### 3. Input Formatting with `<inputs>` Block

**Decision**: Format additional parameters as an XML-like `<inputs>` block prepended to the prompt.

```
<inputs>
topic: AI Safety
format: summary
max_words: 200
</inputs>

Create content about this topic.
```

**Rationale**:
- Clear separation between structured inputs and free-form prompt
- AI models understand XML-like delimiters well
- Easy to parse if needed for debugging
- Consistent with how Claude handles other structured content
- The system prompt can reference `<inputs>` to explain their meaning

##### 4. Dashboard Toggle vs Direct Schema Editing

**Decision**: Provide an explicit enable/disable toggle alongside the schema editor.

**Rationale**:
- Clear user intent: toggling off explicitly disables the feature
- Prevents accidental schema activation from empty editor state
- Allows saving "draft" schemas that aren't active yet
- Visual clarity: users see at a glance if custom schema is active

---

## Code Walkthrough

### Validation Logic (`run_queue.py`)

```python
def _merge_autonomous_schema_with_prompt(custom_schema: dict) -> dict:
    """
    Merge custom parameters_schema with prompt requirement for autonomous agents.
    """
    merged = copy.deepcopy(custom_schema)

    # Ensure type is object
    if merged.get("type") != "object":
        merged["type"] = "object"

    # Add prompt property if not present
    if "properties" not in merged:
        merged["properties"] = {}
    if "prompt" not in merged["properties"]:
        merged["properties"]["prompt"] = {"type": "string", "minLength": 1}

    # Ensure prompt is in required list
    required = merged.get("required", [])
    if "prompt" not in required:
        merged["required"] = list(required) + ["prompt"]

    return merged
```

The merge function ensures:
1. Schema type is always "object"
2. `prompt` property exists with string type and minLength validation
3. `prompt` is in the required list

This is done at validation time, not storage time, so the agent's stored schema remains exactly as configured.

### Input Formatting (`utils.py`)

```python
def format_autonomous_inputs(parameters: dict) -> str:
    """
    Format parameters for autonomous agents into a prompt string.
    """
    prompt = parameters["prompt"]
    additional_params = {k: v for k, v in parameters.items() if k != "prompt"}

    # If no additional params, return prompt as-is
    if not additional_params:
        return prompt

    # Format as <inputs> block
    lines = ["<inputs>"]
    for key, value in additional_params.items():
        if isinstance(value, str):
            if "\n" in value:
                lines.append(f"{key}:")
                for line in value.split("\n"):
                    lines.append(f"  {line}")
            else:
                lines.append(f"{key}: {value}")
        elif isinstance(value, (list, dict)):
            lines.append(f"{key}: {json.dumps(value)}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("</inputs>")
    lines.append("")

    return "\n".join(lines) + "\n" + prompt
```

Key behaviors:
- Returns prompt unchanged if no additional parameters
- Handles multi-line strings with indentation
- JSON-serializes complex types (lists, dicts)
- Adds empty line between inputs block and prompt for readability

### Executor Integration (`ao-claude-code-exec`)

```python
def run_start(inv: ExecutorInvocation):
    # ... setup code ...

    # Format prompt with additional inputs
    formatted_prompt = format_autonomous_inputs(inv.parameters)

    # Run Claude session with formatted prompt
    executor_session_id, result = run_session_sync(
        prompt=formatted_prompt,
        # ... other params ...
    )
```

The executor simply calls `format_autonomous_inputs()` before passing the prompt to the Claude SDK. This keeps the formatting logic centralized in `utils.py`.

---

## Agent Blueprint Configuration

### Schema Definition

Define `parameters_schema` in `agent.json`:

```json
{
  "name": "parametric-agent",
  "description": "Agent with custom input parameters",
  "type": "autonomous",
  "tags": ["internal"],
  "parameters_schema": {
    "type": "object",
    "required": ["topic", "format"],
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
      "max_words": {
        "type": "integer",
        "minimum": 50,
        "maximum": 2000,
        "description": "Maximum word count"
      }
    },
    "additionalProperties": false
  }
}
```

### System Prompt Integration

The system prompt should explain how to use the inputs:

```markdown
# Agent Instructions

You will receive structured inputs in an `<inputs>` block followed by a prompt.

The inputs contain:
- **topic**: The main subject to write about
- **format**: The output format (summary, bullet_points, or essay)
- **max_words**: Optional maximum word count

Follow the format specification exactly and respect any word limits.
```

---

## API Usage

### Starting an Agent with Custom Parameters

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "agent_name": "parametric-agent",
    "parameters": {
      "prompt": "Create content about this topic.",
      "topic": "Machine Learning in Healthcare",
      "format": "bullet_points",
      "max_words": 300
    }
  }'
```

### Validation Errors

If parameters don't match the schema, the API returns detailed validation errors:

```json
{
  "error": "parameter_validation_failed",
  "message": "Parameters do not match agent's parameters_schema",
  "agent_name": "parametric-agent",
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

---

## Testing

### Unit Tests for Validation

```python
# Test merge function
custom_schema = {
    'type': 'object',
    'properties': {'topic': {'type': 'string'}},
    'required': ['topic']
}
merged = _merge_autonomous_schema_with_prompt(custom_schema)
assert 'prompt' in merged['properties']
assert 'prompt' in merged['required']

# Test validation with custom schema
agent = Agent(name='test', type='autonomous', parameters_schema=custom_schema, ...)
validate_parameters({'prompt': 'hello', 'topic': 'AI'}, agent)  # Should pass
validate_parameters({'topic': 'AI'}, agent)  # Should fail - missing prompt
```

### Unit Tests for Input Formatting

```python
# Test prompt only
result = format_autonomous_inputs({'prompt': 'Hello'})
assert result == 'Hello'

# Test with additional parameters
result = format_autonomous_inputs({
    'prompt': 'Create content.',
    'topic': 'AI',
    'format': 'summary'
})
assert '<inputs>' in result
assert 'topic: AI' in result
assert 'Create content.' in result
```

---

## Migration Notes

### Existing Agents

Existing autonomous agents without `parameters_schema` continue to work unchanged. They use the implicit schema requiring only `{"prompt": "..."}`.

### Adding Schema to Existing Agents

To add a custom schema to an existing agent:

1. **Via Dashboard**: Edit the agent, enable "Custom Input Schema", define the schema, save
2. **Via File**: Add `parameters_schema` to the agent's `agent.json` file

No migration of existing data is required.

---

## Future Considerations

1. **Schema Inheritance**: Allow agents to extend a base schema
2. **Dynamic Schema**: Schema that changes based on context or capabilities
3. **Output Schema**: Validate agent outputs against a schema
4. **Schema Versioning**: Track schema changes over time
