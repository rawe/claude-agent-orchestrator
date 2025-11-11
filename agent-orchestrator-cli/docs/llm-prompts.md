# LLM Implementation Prompts

Templates for getting LLMs to implement the stubs effectively.

## General Pattern

```
Context: [Explain what you're building]
Reference: [Point to bash script or specs]
Requirements: [List specific requirements]
Task: Implement [specific module]
Constraints: [Preserve signatures, error handling, etc.]
```

## Implementing lib/config.py

```markdown
I'm building a Python CLI tool that manages Claude AI agent sessions.

Reference implementation: The bash script at `../agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh` (lines 100-200 show configuration logic).

Requirements:
- Configuration precedence: CLI flags > Environment variables > Defaults (PWD)
- Environment variables:
  - AGENT_ORCHESTRATOR_PROJECT_DIR
  - AGENT_ORCHESTRATOR_SESSIONS_DIR
  - AGENT_ORCHESTRATOR_AGENTS_DIR
  - AGENT_ORCHESTRATOR_ENABLE_LOGGING
- Default locations:
  - project_dir: Current working directory (PWD)
  - sessions_dir: {project_dir}/.agent-orchestrator/sessions
  - agents_dir: {project_dir}/.agent-orchestrator/agents

Task: Implement the functions in `lib/config.py` based on the TODO comments.

Constraints:
- Preserve the function signatures exactly
- Return the Config dataclass with resolved absolute paths
- Validate that directories exist or can be created
- Handle errors gracefully with clear messages
- Follow Python best practices

Please implement the module.
```

## Implementing lib/session.py

```markdown
I need to implement session management for a Claude AI CLI tool.

Reference: See the bash script `../agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh` functions:
- `validate_session_name()` (line ~150)
- `get_session_state()` (line ~200)
- Session file format is documented in bash script comments

Requirements:
- Session names: alphanumeric + dash/underscore, max 60 chars
- Session states: "not_existent", "running", "finished"
- State detection algorithm:
  1. No dir/file = not_existent
  2. File exists but no completion marker = running
  3. File has completion marker = finished
- Session metadata stored in `.metadata.json`
- Session output stored in `session.txt`

Task: Implement all functions in `lib/session.py` based on TODO comments.

Constraints:
- Match bash script behavior exactly
- Preserve function signatures
- Use proper error handling
- Type hints for all functions
- Clear error messages

Please implement the module.
```

## Implementing bin/ao-status

```markdown
I need to implement the `ao-status` command that checks session status.

Reference: The bash script command at line ~400 in `../agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh`

Command behavior:
- Takes session name as argument
- Optional --project-dir and --sessions-dir flags
- Outputs exactly one of: "running", "finished", "not_existent"
- Exit code 0 for all cases (even not_existent)

Implementation plan:
1. Parse arguments using typer
2. Load configuration using lib/config.py
3. Validate session name using lib/session.py
4. Get session state using lib/session.get_session_state()
5. Print state to stdout
6. Exit with code 0

Task: Replace the TODO in `bin/ao-status` with working implementation.

Constraints:
- Use existing shared modules (config, session, utils)
- Match bash script output format exactly
- Keep the uv script header unchanged
- Use typer for argument parsing
- Handle errors with lib/utils.error()

Please implement the command.
```

## Implementing lib/claude_client.py

```markdown
I need to implement Claude API integration for managing persistent sessions.

This wraps the Anthropic Python SDK to:
1. Create new sessions with optional system prompts and MCP config
2. Resume existing sessions with session ID
3. Stream responses to files for persistence

Requirements:
- Use official Anthropic Python SDK
- Support system prompts (for agents)
- Support MCP configuration (for tools)
- Stream responses to file as they arrive
- Return session ID for new sessions
- Handle API errors gracefully

Reference:
- Anthropic SDK docs: https://docs.anthropic.com/
- See bash script calls to `claude` CLI for expected behavior

Task: Implement the functions in `lib/claude_client.py`.

Implementation notes:
- New sessions: Use `client.messages.create()` with system prompt
- Resume sessions: Use session ID from previous call
- Streaming: Use `stream=True` parameter
- MCP config: Pass as tool configuration
- Working directory: Set in API call context

Constraints:
- Preserve function signatures
- Use proper exception handling
- Log to file if logging enabled
- Return clean results

Please implement the module.
```

## Implementing bin/ao-new

```markdown
I need to implement the `ao-new` command that creates new agent sessions.

Reference: Bash script `new` command implementation (line ~500)

Command behavior:
- Arguments: session_name (required)
- Options:
  - -p/--prompt (optional, can combine with stdin)
  - --agent (optional agent name)
  - --project-dir, --sessions-dir, --agents-dir (optional overrides)
- Creates session directory
- Loads agent if specified
- Calls Claude API
- Saves response to session file
- Outputs result to stdout

Implementation flow:
1. Parse arguments
2. Load configuration
3. Validate session name
4. Check session doesn't already exist
5. Read prompt from -p flag and/or stdin (concatenate if both)
6. Load agent if --agent specified
7. Create session directory and metadata
8. Call Claude API (lib/claude_client.create_new_session)
9. Extract and output result
10. Log if logging enabled

Task: Replace TODO in `bin/ao-new` with working implementation.

Constraints:
- Use all relevant shared modules
- Match bash script behavior exactly
- Handle all error cases
- Support stdin + -p flag combination (bash: -p content first, then stdin)
- Set working directory to project_dir

Please implement the command.
```

## Tips for LLM Implementation

### Give Complete Context

```markdown
Include:
- What the tool does (high level)
- Reference implementation (bash script)
- Specific requirements
- File formats and protocols
- Expected behavior
```

### Be Specific About Constraints

```markdown
Preserve:
- Function signatures
- Error handling patterns
- Output formats
- File formats

Match exactly:
- Bash script behavior
- Error messages
- Exit codes
```

### Implement Incrementally

```markdown
Don't ask for everything at once:

❌ "Implement all 8 commands and 5 modules"
✅ "Implement lib/config.py"
✅ Then: "Implement lib/utils.py"
✅ Then: "Implement ao-status using config and utils"
```

### Validate Behavior

```markdown
After each implementation:
1. Test manually
2. Compare output to bash script
3. Check error cases
4. Verify file formats match
```

## Example Full Session

```markdown
Me: [Paste prompt for lib/config.py]
LLM: [Implements config.py]
Me: Let me test this... [tests] Found issue with path resolution
LLM: [Fixes issue]
Me: Great! Now let's do lib/utils.py [paste prompt]
LLM: [Implements utils.py]
Me: Perfect. Now implement ao-status using config and utils [paste prompt]
LLM: [Implements ao-status]
Me: Testing... [tests] Works! Let's move to ao-list
[continue...]
```

## Debugging Prompts

### If Implementation is Wrong

```markdown
The implementation doesn't match the bash script behavior.

Expected: [describe bash behavior]
Got: [describe current behavior]

Reference: See bash script line [X]

Please fix the implementation to match exactly.
```

### If Missing Error Handling

```markdown
The implementation needs better error handling for:
- [Specific error case]
- [Another error case]

Please add try/catch and use lib/utils.error() for user-facing errors.
```

### If Output Format is Wrong

```markdown
The output format doesn't match the bash script.

Bash outputs: [example]
Current code outputs: [example]

Please adjust the formatting to match exactly.
```

---

**Key Takeaway**: Clear, specific prompts with references and constraints produce the best results. Break down the work into manageable chunks.
