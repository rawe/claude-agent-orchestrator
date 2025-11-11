# Claude Python SDK Investigation Results

## Executive Summary

**Recommendation: Use Option B (Python SDK)** - The Claude Agent SDK for Python supports all critical requirements and offers superior long-term maintainability.

## Requirements Analysis

### ✅ Requirement 1: Session Persistence & Resumption

**SUPPORTED** - The SDK provides full session management:

```python
from claude_agent_sdk import ClaudeAgentOptions, query

# Create new session (captures session_id from response)
async for message in query(
    prompt="Design user auth system",
    options=ClaudeAgentOptions(
        cwd="/path/to/project",
        permission_mode="bypassPermissions"
    )
):
    # First message contains session_id
    if hasattr(message, 'session_id'):
        session_id = message.session_id

# Resume existing session
async for message in query(
    prompt="Continue with API design",
    options=ClaudeAgentOptions(
        resume=session_id,  # Resume by session ID
        cwd="/path/to/project"
    )
):
    process_message(message)
```

**Key Parameters:**
- `resume: str` - Resume specific session by ID
- `continue_conversation: bool` - Resume most recent conversation
- `fork_session: bool` - Create branching session from resume point

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

**SUPPORTED** - Async streaming with JSON output:

```python
import json

session_file = "/path/to/session.jsonl"

async for message in query(prompt="...", options=options):
    # Each message is streamed progressively
    with open(session_file, 'a') as f:
        # Messages come in stream-json format
        json.dump(message.model_dump(), f)
        f.write('\n')

    # Extract session_id from first message
    if hasattr(message, 'session_id'):
        session_id = message.session_id

    # Extract final result from last message
    if hasattr(message, 'result'):
        result = message.result
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
| `claude -p "$prompt"` | `query(prompt=..., options=...)` |
| `claude -r "$session_id"` | `query(options=ClaudeAgentOptions(resume=session_id))` |
| `--mcp-config "$path"` | Load JSON, pass to `mcp_servers` param |
| `--output-format stream-json` | Built-in: `query()` returns async iterator |
| `--permission-mode bypassPermissions` | `permission_mode="bypassPermissions"` |
| `cd "$PROJECT_DIR" &&` | `cwd="/path/to/project"` |
| `>> "$session_file"` | Manually write streamed messages to file |

### Key Differences from CLI Approach

**Advantages of SDK:**
1. **Native Python integration** - No subprocess overhead
2. **Better error handling** - Exceptions vs exit codes
3. **Programmatic control** - Full access to message objects
4. **Type safety** - Type hints for configuration
5. **Flexibility** - Easy to customize behavior
6. **Future-proof** - SDK evolves with new features

**Considerations:**
1. **Session file management** - Must manually write to `.jsonl` files
2. **Session ID extraction** - Must parse from message stream
3. **Result extraction** - Must track last message result

### Recommended Implementation Pattern

```python
# lib/claude_client.py

import json
from pathlib import Path
from claude_agent_sdk import query, ClaudeAgentOptions
from typing import AsyncIterator, Optional

async def run_claude_session(
    prompt: str,
    session_file: Path,
    project_dir: Path,
    mcp_config: Optional[dict] = None,
    resume_session_id: Optional[str] = None
) -> tuple[str, str]:
    """
    Run Claude session and stream to file.

    Returns: (session_id, result)
    """

    # Build options
    options = ClaudeAgentOptions(
        cwd=str(project_dir),
        permission_mode="bypassPermissions",
    )

    if resume_session_id:
        options.resume = resume_session_id

    if mcp_config:
        options.mcp_servers = mcp_config.get("mcpServers", {})
        # Extract allowed tools from MCP config if needed
        # options.allowed_tools = [...]

    # Stream session to file
    session_id = None
    result = None

    async for message in query(prompt=prompt, options=options):
        # Write each message to JSONL file
        with open(session_file, 'a') as f:
            json.dump(message.model_dump(), f)
            f.write('\n')

        # Capture session_id from first message
        if session_id is None and hasattr(message, 'session_id'):
            session_id = message.session_id

        # Capture result from last message
        if hasattr(message, 'result'):
            result = message.result

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

Beyond the bash script's capabilities, the SDK offers:

1. **Custom tool callbacks** - `can_use_tool` parameter
2. **Partial message streaming** - `include_partial_messages`
3. **System prompt customization** - `system_prompt` parameter
4. **Model selection** - `model` parameter
5. **Settings file support** - `settings` parameter
6. **Stderr callbacks** - `stderr` parameter

## Conclusion

**The Claude Agent SDK for Python fully supports all requirements** and offers a superior implementation path:

✅ Session persistence & resumption
✅ Working directory context
✅ MCP tool integration
✅ Response streaming to files
✅ 100% file format compatibility
✅ Better error handling
✅ Native Python integration
✅ Long-term maintainability

## Next Steps

1. **Implement `lib/claude_client.py`** using the SDK pattern above
2. **Test with simple session** - Verify JSONL output matches bash format
3. **Implement session ID extraction** - Parse from first message
4. **Implement result extraction** - Parse from last message
5. **Test MCP integration** - Load agent MCP configs
6. **Validate compatibility** - Ensure bash and Python sessions are interoperable

## References

- **Claude Agent SDK Python**: https://github.com/anthropics/claude-agent-sdk-python
- **SDK Documentation**: https://docs.claude.com/en/docs/agent-sdk/python
- **MCP Integration**: https://docs.claude.com/en/docs/agent-sdk/mcp
