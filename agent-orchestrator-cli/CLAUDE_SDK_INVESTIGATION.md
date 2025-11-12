# Claude Python SDK Investigation Results

## Executive Summary

**Recommendation: Use ClaudeSDKClient from the Python SDK** - The Claude Agent SDK for Python with `ClaudeSDKClient` supports all critical requirements and offers superior long-term maintainability.

**Key Decision**: Use `ClaudeSDKClient` (not the simpler `query()` function) because it provides:
- Proper session management with `resume` parameter
- Multi-turn conversation support
- Explicit lifecycle control (connect/disconnect)
- Interrupt capability for long-running tasks
- Hook system for deterministic processing
- Better suited for our orchestrator's session persistence needs

## Requirements Analysis

### ✅ Requirement 1: Session Persistence & Resumption

**SUPPORTED** - The SDK provides full session management via `ClaudeSDKClient`:

```python
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, ResultMessage

# Create new session (captures session_id from ResultMessage)
options = ClaudeAgentOptions(
    cwd="/path/to/project",
    permission_mode="bypassPermissions"
)

async with ClaudeSDKClient(options=options) as client:
    await client.query("Design user auth system")

    async for message in client.receive_response():
        if isinstance(message, ResultMessage):
            session_id = message.session_id
            result = message.result
            print(f"Session ID: {session_id}")

# Resume existing session
resume_options = ClaudeAgentOptions(
    resume=session_id,  # Resume by session ID
    cwd="/path/to/project",
    permission_mode="bypassPermissions"
)

async with ClaudeSDKClient(options=resume_options) as client:
    await client.query("Continue with API design")

    async for message in client.receive_response():
        if isinstance(message, ResultMessage):
            print(f"Resumed session: {message.session_id}")
```

**Key Parameters:**
- `resume: str` - Resume specific session by ID
- `fork_session: bool` - Create branching session from resume point

**Key Message Types:**
- `ResultMessage` - Contains `session_id`, `result`, `total_cost_usd`, `duration_ms`, `num_turns`

### ✅ Requirement 2: Working Directory Context

**SUPPORTED** - Full working directory control:

```python
ClaudeAgentOptions(
    cwd="/path/to/project",  # Current working directory
    add_dirs=["/additional/path"]  # Additional accessible directories
)
```

The SDK runs all file operations within the specified `cwd`, maintaining consistency across the session lifecycle.

### ✅ Requirement 3: MCP Tool Integration

**SUPPORTED** - Multiple MCP integration methods:

**Method 1: External MCP Config File**
```python
# SDK automatically discovers .mcp.json in project root
ClaudeAgentOptions(cwd="/project/with/.mcp.json")
```

**Method 2: Programmatic MCP Configuration**
```python
ClaudeAgentOptions(
    mcp_servers={
        "filesystem": {
            "command": "npx",
            "args": ["@modelcontextprotocol/server-filesystem"],
            "env": {"ALLOWED_PATHS": "/Users/me/projects"}
        }
    },
    allowed_tools=["mcp__filesystem__list_files"]
)
```

**Method 3: In-Process SDK MCP Servers**
```python
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool("custom_tool", "Description", {"param": str})
async def my_tool(args):
    return {"content": [{"type": "text", "text": "Result"}]}

server = create_sdk_mcp_server(
    name="my-tools",
    version="1.0.0",
    tools=[my_tool]
)

options = ClaudeAgentOptions(
    mcp_servers={"tools": server},
    allowed_tools=["mcp__tools__custom_tool"]
)
```

### ✅ Requirement 4: Response Streaming to Files

**SUPPORTED** - Async streaming with JSON output using `ClaudeSDKClient`:

```python
import json
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, ResultMessage

session_file = "/path/to/session.jsonl"
options = ClaudeAgentOptions(
    cwd="/path/to/project",
    permission_mode="bypassPermissions"
)

session_id = None
result = None

async with ClaudeSDKClient(options=options) as client:
    await client.query("Your prompt here")

    async for message in client.receive_response():
        # Write each message to JSONL file
        with open(session_file, 'a') as f:
            json.dump(message.model_dump(), f)
            f.write('\n')

        # Extract session_id and result from ResultMessage
        if isinstance(message, ResultMessage):
            session_id = message.session_id
            result = message.result

print(f"Session ID: {session_id}")
print(f"Result: {result}")
```

## Bash Script Analysis

The current bash script uses the Claude CLI as follows:

### New Session
```bash
cd "$PROJECT_DIR" && \
claude -p "$prompt" \
  --mcp-config "$mcp_config_path" \
  --output-format stream-json \
  --permission-mode bypassPermissions \
  >> "$session_file" 2>&1
```

### Resume Session
```bash
cd "$PROJECT_DIR" && \
claude -r "$session_id" \
  -p "$prompt" \
  --mcp-config "$mcp_config_path" \
  --output-format stream-json \
  --permission-mode bypassPermissions \
  >> "$session_file" 2>&1
```

### Session File Format
- **File**: `{session_name}.jsonl` (JSON Lines format)
- **First line**: Contains `session_id`
- **Last line**: Contains `result`
- **All lines**: Stream-JSON formatted messages

### Metadata File Format
```json
{
  "session_name": "architect",
  "agent": "system-architect",
  "created": "2025-01-15T10:30:00Z",
  "updated": "2025-01-15T11:45:00Z",
  "project_dir": "/path/to/project",
  "agents_dir": "/path/to/agents"
}
```

## SDK Implementation Strategy

### Architecture Mapping

| Bash Behavior | Python SDK Equivalent |
|---------------|----------------------|
| `claude -p "$prompt"` | `async with ClaudeSDKClient(options) as client: await client.query(prompt)` |
| `claude -r "$session_id"` | `ClaudeAgentOptions(resume=session_id)` |
| `--mcp-config "$path"` | Load JSON, pass to `mcp_servers` param |
| `--output-format stream-json` | Built-in: `client.receive_response()` returns async iterator |
| `--permission-mode bypassPermissions` | `permission_mode="bypassPermissions"` |
| `cd "$PROJECT_DIR" &&` | `cwd="/path/to/project"` |
| `>> "$session_file"` | Manually write streamed messages to file |

### Key Differences from CLI Approach

**Advantages of ClaudeSDKClient:**
1. **Native Python integration** - No subprocess overhead
2. **Better error handling** - Typed exceptions (ClaudeSDKError, CLIConnectionError, etc.)
3. **Programmatic control** - Full access to typed message objects
4. **Type safety** - Type hints for all configuration and messages
5. **Multi-turn conversations** - Maintain context across multiple queries in same session
6. **Interrupt support** - Can stop Claude mid-execution with `await client.interrupt()`
7. **Hook system** - Deterministic processing and automated feedback
8. **Custom tools** - In-process MCP servers via `@tool()` decorator
9. **Lifecycle management** - Explicit connect/disconnect control
10. **Future-proof** - SDK evolves with new features

**Considerations:**
1. **Session file management** - Must manually write to `.jsonl` files
2. **Session ID extraction** - Must check for `ResultMessage` type
3. **Result extraction** - Extract from `ResultMessage.result` property

### Recommended Implementation Pattern

```python
# lib/claude_client.py

import json
from pathlib import Path
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, ResultMessage
from typing import Optional

async def run_claude_session(
    prompt: str,
    session_file: Path,
    project_dir: Path,
    mcp_config: Optional[dict] = None,
    resume_session_id: Optional[str] = None
) -> tuple[str, str]:
    """
    Run Claude session and stream to file using ClaudeSDKClient.

    Args:
        prompt: The prompt to send to Claude
        session_file: Path to .jsonl file for storing messages
        project_dir: Working directory for Claude
        mcp_config: Optional MCP configuration dict
        resume_session_id: Optional session ID to resume

    Returns: (session_id, result)
    """

    # Build options
    options = ClaudeAgentOptions(
        cwd=str(project_dir.resolve()),
        permission_mode="bypassPermissions",
    )

    if resume_session_id:
        options.resume = resume_session_id

    if mcp_config:
        options.mcp_servers = mcp_config.get("mcpServers", {})
        # Extract allowed tools from MCP config if needed
        # options.allowed_tools = [...]

    # Initialize tracking variables
    session_id = None
    result = None

    # Use ClaudeSDKClient context manager for proper lifecycle
    async with ClaudeSDKClient(options=options) as client:
        # Send the prompt
        await client.query(prompt)

        # Stream messages and write to file
        async for message in client.receive_response():
            # Write each message to JSONL file
            with open(session_file, 'a') as f:
                json.dump(message.model_dump(), f)
                f.write('\n')

            # Extract session_id and result from ResultMessage
            if isinstance(message, ResultMessage):
                session_id = message.session_id
                result = message.result

    # Validate we received required data
    if not session_id:
        raise ValueError("No session_id received from Claude")

    if not result:
        raise ValueError("No result received from Claude")

    return session_id, result
```

## File Format Compatibility

### 100% Compatibility Maintained

The SDK implementation can maintain exact file format compatibility:

1. **Session files** (`.jsonl`) - Manually write stream-json format
2. **Metadata files** (`.meta.json`) - Python handles this natively
3. **Session ID extraction** - Parse from first message
4. **Result extraction** - Parse from last message
5. **Agent structure** - Load `agent.json`, `agent.system-prompt.md`, `agent.mcp.json`

### State Detection Algorithm

The bash script's state detection logic can be replicated exactly:

```python
def get_session_status(session_name: str) -> str:
    """Returns: 'running', 'finished', or 'not_existent'"""
    meta_file = sessions_dir / f"{session_name}.meta.json"
    session_file = sessions_dir / f"{session_name}.jsonl"

    if not meta_file.exists():
        return "not_existent"

    if not session_file.exists():
        return "running"  # Initializing

    # Check if last line has result
    with open(session_file, 'rb') as f:
        # Read last line
        try:
            f.seek(-2, os.SEEK_END)
            while f.read(1) != b'\n':
                f.seek(-2, os.SEEK_CUR)
            last_line = f.readline().decode()
        except:
            return "running"

    try:
        last_msg = json.loads(last_line)
        if 'result' in last_msg:
            return "finished"
    except:
        pass

    return "running"
```

## Additional SDK Features

Beyond the bash script's capabilities, the ClaudeSDKClient offers:

### ClaudeSDKClient-Specific Features
1. **Multi-turn conversations** - Maintain context across multiple `client.query()` calls in same session
2. **Interrupt capability** - Stop Claude mid-execution: `await client.interrupt()`
3. **Hook system** - Deterministic processing and automated feedback via hooks
4. **Custom tools** - In-process MCP servers using `@tool()` decorator and `create_sdk_mcp_server()`
5. **Lifecycle management** - Explicit control via `connect()` and `disconnect()` methods
6. **Bidirectional communication** - Interactive conversations with context preservation

### ClaudeAgentOptions Parameters
7. **Custom tool callbacks** - `can_use_tool` parameter for permission control
8. **Partial message streaming** - `include_partial_messages` for real-time progress
9. **System prompt customization** - `system_prompt` parameter to shape behavior
10. **Model selection** - `model` parameter for choosing Claude model
11. **Settings file support** - `settings` parameter for configuration
12. **Stderr callbacks** - `stderr` parameter for debugging output

### Message Types Available
- **UserMessage** - User input messages
- **AssistantMessage** - Claude's responses (with TextBlock, ThinkingBlock, ToolUseBlock)
- **SystemMessage** - System-level notifications
- **ResultMessage** - Final result with session_id, cost, duration, num_turns

## Conclusion

**The Claude Agent SDK for Python with ClaudeSDKClient fully supports all requirements** and offers a superior implementation path:

✅ Session persistence & resumption via `resume` parameter
✅ Working directory context with `cwd` option
✅ MCP tool integration (external, programmatic, and in-process)
✅ Response streaming to files with typed message objects
✅ Session ID extraction from `ResultMessage.session_id`
✅ Result extraction from `ResultMessage.result`
✅ Better error handling with typed exceptions
✅ Native Python integration with async/await
✅ Multi-turn conversation support
✅ Interrupt capability for long-running tasks
✅ Hook system for deterministic processing
✅ Long-term maintainability

## Next Steps

1. **Implement `lib/claude_client.py`** using the ClaudeSDKClient pattern above
2. **Add proper imports** - `ClaudeSDKClient`, `ClaudeAgentOptions`, `ResultMessage`
3. **Test with simple session** - Verify JSONL output and session_id extraction
4. **Test session resumption** - Verify `resume` parameter works correctly
5. **Test MCP integration** - Load agent MCP configs programmatically
6. **Validate message types** - Ensure `isinstance(message, ResultMessage)` works
7. **Test interrupt capability** - Verify `await client.interrupt()` functionality
8. **Validate compatibility** - Ensure session files are properly structured

## References

- **Claude Agent SDK Python**: https://github.com/anthropics/claude-agent-sdk-python
- **SDK Documentation**: https://docs.claude.com/en/docs/agent-sdk/python
- **MCP Integration**: https://docs.claude.com/en/docs/agent-sdk/mcp
