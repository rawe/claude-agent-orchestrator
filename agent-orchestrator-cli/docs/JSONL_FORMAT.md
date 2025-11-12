# Session JSONL Format

## Overview

Session files (`.jsonl`) contain the complete conversation history between user and Claude, with one JSON object per line.

## Message Types

### 1. User Message (Custom)
```json
{
  "type": "user_message",
  "content": "What is 2+2?",
  "timestamp": "2025-11-12T13:54:29.687393Z"
}
```
- **When**: Written before each SDK interaction (ao-new, ao-resume)
- **Purpose**: Records user prompts for conversation replay

### 2. System Message - Init (SDK)
```json
{
  "subtype": "init",
  "data": {
    "session_id": "d796e8ba-ef3c-453f-97d7-b644930563f5",
    "cwd": "/path/to/project",
    "model": "claude-sonnet-4-5-20250929",
    "tools": ["Task", "Bash", "Grep", ...],
    "permissionMode": "bypassPermissions"
  }
}
```
- **When**: First message from SDK per interaction
- **Purpose**: Session configuration and environment setup

### 3. Assistant Text Message (SDK)
```json
{
  "content": [{"text": "4"}],
  "model": "claude-sonnet-4-5-20250929",
  "parent_tool_use_id": null
}
```
- **When**: During SDK streaming
- **Purpose**: Claude's response text
- **Identify by**: `content[0]` has `"text"` field

### 4. Tool Use Message (SDK)
```json
{
  "content": [{
    "id": "toolu_01Q8nLngDXta4w5NvP6L9KZg",
    "name": "Bash",
    "input": {
      "command": "tree -L 2 commands/",
      "description": "Show directory structure"
    }
  }],
  "model": "claude-sonnet-4-5-20250929",
  "parent_tool_use_id": null
}
```
- **When**: During SDK streaming when Claude invokes a tool
- **Purpose**: Records tool invocation with parameters
- **Identify by**: `content[0]` has `"id"`, `"name"`, and `"input"` fields

### 5. Tool Result Message (SDK)
```json
{
  "content": [{
    "tool_use_id": "toolu_01Q8nLngDXta4w5NvP6L9KZg",
    "content": "commands/\n├── ao-clean\n├── ao-get-result\n...",
    "is_error": false
  }],
  "parent_tool_use_id": null
}
```
- **When**: During SDK streaming after tool execution
- **Purpose**: Records tool execution output
- **Identify by**: `content[0]` has `"tool_use_id"` and `"is_error"` fields

### 6. Result Message (SDK)
```json
{
  "subtype": "success",
  "duration_ms": 3322,
  "session_id": "d796e8ba-ef3c-453f-97d7-b644930563f5",
  "total_cost_usd": 0.0051445,
  "usage": {
    "input_tokens": 3,
    "output_tokens": 5
  },
  "result": "4"
}
```
- **When**: Final message from SDK per interaction
- **Purpose**: Metrics, cost tracking, final result

## Message Flow Patterns

### Simple Interaction (No Tool Use)
Each interaction adds 4 messages:

```
User Message     → "What is 2+2?"
System Init      → Session configuration
Assistant Text   → "4"
Result Summary   → Metrics + cost
```

### Interaction with Tool Use
Each interaction adds 7 messages:

```
User Message     → "Use the Bash tool to run tree..."
System Init      → Session configuration
Assistant Text   → "I'll run the tree command..."
Tool Use         → Bash invocation with parameters
Tool Result      → Tree command output
Assistant Text   → "The directory has the following structure..."
Result Summary   → Metrics + cost
```

**Note**: Multiple tool calls will add more Tool Use + Tool Result pairs.

## Parsing Examples

**Extract conversation only:**
```bash
grep -E '(user_message|"text":)' session.jsonl
```

**Get user prompts:**
```bash
grep '"type": "user_message"' session.jsonl | jq -r '.content'
```

**Get assistant responses:**
```bash
grep '"text":' session.jsonl | jq -r '.content[0].text'
```

**Get tool invocations:**
```bash
grep '"name":' session.jsonl | grep '"input":' | jq '.content[0] | {tool: .name, input: .input}'
```

**Get tool results:**
```bash
grep '"tool_use_id":' session.jsonl | jq -r '.content[0].content'
```

**Calculate total cost:**
```bash
grep '"total_cost_usd"' session.jsonl | jq -s 'map(.total_cost_usd) | add'
```

**Count tool uses per session:**
```bash
grep -c '"name":' session.jsonl | grep '"input":'
```
