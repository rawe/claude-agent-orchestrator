# Debugging Hook Input

When adding new hooks or troubleshooting why a hook isn't capturing the expected data, you need to see what Claude Code is actually sending to the hook script.

## Method: Write to Debug Log File

Since hook scripts are invoked by Claude Code (no console access), write debug info to a temporary file.

### 1. Add Debug Logging to Hook Script

```python
import json

def main():
    try:
        hook_input = json.load(sys.stdin)

        # DEBUG: Write input to file
        with open("/tmp/hook_debug.log", "a") as f:
            f.write(f"\n=== {hook_input.get('hook_event_name', 'Unknown')} Hook Debug ===\n")
            f.write(f"Keys: {list(hook_input.keys())}\n")
            f.write(f"Full input:\n{json.dumps(hook_input, indent=2)}\n")

        # ... rest of your hook code
```

### 2. Trigger the Hook

Run a Claude Code session that triggers the hook event:
- **SessionStart**: Start any agent session
- **PreToolUse/PostToolUse**: Use any tool (Read, Write, Bash, etc.)
- **Stop**: Exit a Claude Code session

### 3. Read the Debug Output

```bash
cat /tmp/hook_debug.log
```

### 4. Update Hook Script

Based on the debug output:
1. Identify the correct field names
2. Update your hook to read from those fields
3. Remove the debug logging

### 5. Clean Up

```bash
rm /tmp/hook_debug.log
```

## Example: PostToolUse Hook

**Initial assumption:** Tool output is in `tool_output` field

**Debug output showed:**
```json
{
  "session_id": "...",
  "tool_name": "Read",
  "tool_input": {...},
  "tool_response": {...}  ← Actual field name!
}
```

**Fix:** Change `hook_input.get("tool_output")` to `hook_input.get("tool_response")`

## Common Field Names

Based on actual Claude Code hook data:

| Hook Event | Available Fields |
|------------|------------------|
| SessionStart | `session_id`, `transcript_path`, `cwd`, `permission_mode` |
| PreToolUse | `session_id`, `tool_name`, `tool_input` |
| PostToolUse | `session_id`, `tool_name`, `tool_input`, `tool_response` |
| Stop | `session_id`, `transcript_path`, `cwd`, `stop_hook_active` |

## Tips

- Always use `hook_input.get("field", default)` for safe access
- Claude Code field names may differ from what you expect
- Some fields may be nested objects (e.g., `tool_response.file.content`)
- Debug files persist across runs - use append mode (`"a"`) to see multiple invocations
