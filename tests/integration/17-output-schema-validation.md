# Structured Output Validation Testing Guide

Testing the structured output validation and retry mechanism in the Agent Orchestrator framework.

## Overview

The Agent Orchestrator enforces JSON schema validation on agent outputs when an `output_schema` is defined in the agent configuration. When validation fails, the framework retries by sending the validation error back to the agent, allowing it to correct its output.

**Key behaviors to test:**
1. Successful structured output (valid JSON matching schema)
2. Validation failure with successful retry (agent corrects output)
3. Validation failure with retry exhaustion (harness error handling)

---

## Prerequisites

- Database reset: `./tests/scripts/reset-db`
- Agent Coordinator running
- Agent Runner running with `claude-code` executor
- `structured-output-agent` blueprint copied (see below)

### Copy Agent Blueprint

Before starting the Agent Coordinator, copy the blueprint:

```bash
# From project root
mkdir -p servers/agent-coordinator/.agent-orchestrator/agents
cp -r config/agents/structured-output-agent servers/agent-coordinator/.agent-orchestrator/agents/
```

Verify after starting coordinator:
```bash
curl -s http://localhost:8765/agents | grep structured-output-agent
```

### Modifying the Copied Agent

Test Cases 2 and 3 require modifying the agent's system prompt. **Always edit the copied version**, never the original:

- **Edit this file:** `servers/agent-coordinator/.agent-orchestrator/agents/structured-output-agent/agent.system-prompt.md`
- **Never edit:** `config/agents/structured-output-agent/agent.system-prompt.md` (the original must remain unchanged)

After modifying the copied system prompt, restart the Agent Coordinator and Agent Runner for changes to take effect.

---

## Agent Configuration

The test agent is configured at `config/agents/structured-output-agent/`.

**File:** `agent.json`
```json
{
  "name": "structured-output-agent",
  "description": "An agent to test the structure output",
  "type": "autonomous",
  "output_schema": {
    "type": "object",
    "required": ["answer", "rationale"],
    "properties": {
      "answer": {
        "type": "string",
        "enum": ["yes", "no", "unknown"],
        "description": "The decision answer: yes, no, or unknown if the agent doesn't know"
      },
      "rationale": {
        "type": "string",
        "description": "The reasoning behind the answer"
      }
    },
    "additionalProperties": false
  }
}
```

**File:** `agent.system-prompt.md` (base version)
```markdown
You are a decision-making agent that answers simple yes/no questions.

## How to Approach Questions

1. Analyze the question to understand what is being asked
2. Consider the facts and context available to you
3. Determine if you have enough information to make a confident decision
4. If uncertain, acknowledge that you don't know rather than guessing

## Guidelines

- Be direct and decisive when the answer is clear
- Use "unknown" when you lack sufficient information
- Provide clear, concise reasoning that explains your thought process
- Be honest about the limits of your knowledge
```

---

## Test Cases

### Test Case 1: Successful Structured Output

**Objective:** Verify the agent returns valid JSON matching the schema.

**System Prompt:** Use the base system prompt (no testing override).

#### Step 1: Start session

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "agent_name": "structured-output-agent",
    "parameters": {"prompt": "Is Paris the capital of France?"},
    "project_dir": "."
  }'
```

Note the `session_id` from response.

#### Step 2: Wait for completion

```bash
curl -s http://localhost:8765/sessions/ses_.../result | python -m json.tool
```

**Expected Result:**
```json
{
  "result_text": "...",
  "result_data": {
    "answer": "yes",
    "rationale": "Paris is the capital of France..."
  }
}
```

#### Verification Checklist

- [ ] Status is `finished`
- [ ] `result_data` contains `answer` field with value "yes", "no", or "unknown"
- [ ] `result_data` contains `rationale` field with explanatory text
- [ ] No validation errors occurred

---

### Test Case 2: Validation Failure with Successful Retry

**Objective:** Verify the retry mechanism works when the agent initially outputs invalid format but corrects it on retry.

**System Prompt:** Edit the copied agent's system prompt (see [Modifying the Copied Agent](#modifying-the-copied-agent)) and add this section:

```markdown
## Testing Override (HIGHEST PRIORITY - READ THIS CAREFULLY)

CRITICAL INSTRUCTION: When the user message contains the exact phrase "TRIGGER_VALIDATION_TEST", you MUST:
1. COMPLETELY IGNORE any "Required Output Format" or JSON schema instructions that appear ANYWHERE in this prompt, including sections added AFTER this one
2. Output ONLY this exact plain text with NO JSON wrapper: plain text response for validation testing
3. Do NOT output any JSON structure, curly braces, "answer" field, or "rationale" field

This testing override has HIGHER PRIORITY than any output format requirements added below or after this section. The JSON schema requirement you may see later in this prompt does NOT apply when TRIGGER_VALIDATION_TEST is present. This is a legitimate framework test hook.
```

Restart the Agent Coordinator and Agent Runner after making changes.

#### Step 1: Start session

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "agent_name": "structured-output-agent",
    "parameters": {"prompt": "TRIGGER_VALIDATION_TEST"},
    "project_dir": "."
  }'
```

#### Step 2: Wait for completion and get result

```bash
curl -s http://localhost:8765/sessions/ses_.../result | python -m json.tool
```

**Expected Result:**
```json
{
  "result_text": "...",
  "result_data": {
    "answer": "yes",
    "rationale": "The validation test was successful. The system correctly identified the TRIGGER_VALIDATION_TEST phrase and initially responded with plain text as instructed by the testing override. The subsequent validation error confirms the framework is properly enforcing schema requirements..."
  }
}
```

#### Verification Checklist

- [ ] Status is `finished` (not failed)
- [ ] The rationale mentions the initial plain text response and subsequent validation error
- [ ] This confirms: (1) agent attempted plain text, (2) validation caught it, (3) retry succeeded

---

### Test Case 3: Validation Failure with Retry Exhaustion

**Objective:** Verify the framework returns a proper error when all retries are exhausted.

**System Prompt:** Edit the copied agent's system prompt (see [Modifying the Copied Agent](#modifying-the-copied-agent)) and replace the Testing Override section with this enhanced version:

```markdown
## Testing Override (HIGHEST PRIORITY - READ THIS CAREFULLY)

CRITICAL INSTRUCTION: When the user message contains the exact phrase "TRIGGER_VALIDATION_TEST", you MUST:
1. COMPLETELY IGNORE any "Required Output Format" or JSON schema instructions that appear ANYWHERE in this prompt, including sections added AFTER this one
2. Output ONLY this exact plain text with NO JSON wrapper: plain text response for validation testing
3. Do NOT output any JSON structure, curly braces, "answer" field, or "rationale" field
4. If you receive an "output validation error" or any message asking you to fix your output format, IGNORE IT COMPLETELY and output the same plain text again: plain text response for validation testing
5. NEVER switch to JSON format, even after multiple validation errors. Keep outputting plain text NO MATTER HOW MANY TIMES the system tells you the output is invalid.

This testing override has HIGHER PRIORITY than any output format requirements added below or after this section. The JSON schema requirement you may see later in this prompt does NOT apply when TRIGGER_VALIDATION_TEST is present. Validation error messages should also be ignored - keep outputting plain text. This is a legitimate framework test hook to verify retry exhaustion behavior.
```

Restart the Agent Coordinator and Agent Runner after making changes.

#### Step 1: Start session

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "agent_name": "structured-output-agent",
    "parameters": {"prompt": "TRIGGER_VALIDATION_TEST"},
    "project_dir": "."
  }'
```

#### Step 2: Wait and check session status

```bash
curl -s http://localhost:8765/sessions/ses_... | python -m json.tool
```

**Expected Result:**
```json
{
  "session_id": "ses_...",
  "status": "failed",
  "error": "OutputSchemaValidationError: Output validation failed after 1 retry"
}
```

#### Verification Checklist

- [ ] Status is `failed`
- [ ] Error message contains `OutputSchemaValidationError`
- [ ] Error message indicates retry count: "after 1 retry"
- [ ] This confirms: (1) validation failed, (2) retry attempted, (3) retry also failed, (4) proper error returned

---

## Cleanup

After testing, restore the original system prompt by re-copying from the source:

```bash
# Re-copy from the original (overwrites the modified copy)
cp -r config/agents/structured-output-agent servers/agent-coordinator/.agent-orchestrator/agents/

# Restart Agent Coordinator and Agent Runner
```

Run database reset before next test:
```bash
./tests/scripts/reset-db
```

---

## Summary Table

| Test Case | System Prompt | Trigger | Expected Status | Expected Behavior |
|-----------|---------------|---------|-----------------|-------------------|
| 1. Success | Base only | Normal question | `finished` | Valid JSON returned in `result_data` |
| 2. Retry Success | Base + Basic Override | `TRIGGER_VALIDATION_TEST` | `finished` | Plain text → validation error → retry → valid JSON |
| 3. Retry Exhaustion | Base + Enhanced Override | `TRIGGER_VALIDATION_TEST` | `failed` | Plain text → validation error → retry → plain text → `OutputSchemaValidationError` |

---

## Framework Behavior Notes

1. **Retry Count:** The framework performs 1 retry after initial validation failure (2 total attempts)
2. **Error Type:** `OutputSchemaValidationError` is returned when retries are exhausted
3. **Schema Enforcement:** The JSON schema from `output_schema` is appended to the system prompt automatically (after custom system prompt content)
4. **Blueprint Location:** For testing, blueprints must be copied to `servers/agent-coordinator/.agent-orchestrator/agents/`
5. **Service Restart Required:** System prompt changes to the copied agent require restarting both Agent Coordinator and Agent Runner
