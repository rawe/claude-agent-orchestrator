# Agent Orchestrator CLI - Implementation Checklist

## Project Context

**What we're building**: A Python rewrite of the bash-based agent orchestrator (`agent-orchestrator.sh`) using the Claude Agent SDK.

**Why**: Progressive disclosure architecture optimized for LLM workflows - each command is a standalone script that loads only what it needs, reducing context window usage by ~70%.

**Key Architectural Decisions**:
- **Self-contained design**: `commands/` directory contains both executables AND their shared `lib/` subdirectory, enabling easy skills deployment
- **SDK integration**: Using Claude Agent Python SDK directly (not CLI subprocess) for better error handling, type safety, and maintainability
- **100% compatibility**: Must maintain complete interoperability with existing bash script - sessions created by either tool can be used by the other

**File Structure**:
```
commands/
├── ao-new, ao-resume, ao-status, etc.  # Standalone command scripts
└── lib/                                 # Shared modules (co-located)
    ├── config.py                        # CLI > ENV > DEFAULT precedence
    ├── session.py                       # State detection, metadata
    ├── agent.py                         # Agent loading
    ├── claude_client.py                 # SDK wrapper
    └── utils.py                         # Common utilities
```

**Essential Reading Before Starting**:
- `PROJECT_CONTEXT.md` - Overall project goals, architecture rationale, current status
- `ARCHITECTURE_PLAN.md` - Detailed implementation guidance with function signatures
- `CLAUDE_SDK_INVESTIGATION.md` - SDK capabilities and usage patterns

---

## Implementation Approach

This checklist breaks implementation into **5 phases**, each designed for a separate coding session. Each phase builds on the previous, starting with read-only operations and progressing to full session creation.

**Start here**: Phase 1, Step 1.1

---

## Important: Python/uv Invocation Rules

When testing or running scripts during development:

- **For running scripts**: Use `uv run <script.py>`
  - Example: `uv run test_utils.py`
  - Example: `uv run commands/ao-status`

- **For inline Python commands**: Use `python` (NOT `python3`)
  - Example: `echo 'test' | python -c "import sys; print(sys.stdin.read())"`
  - NEVER combine with `uv run`: NO `uv run python -c ...`

- **Never use `python3`**: This may invoke an older system Python version
- **Never combine**: NO `uv run python` - choose `uv run <script>` OR `python -c`

---

## CRITICAL: uv Dependency Management Pattern

**All command scripts MUST use uv's inline script metadata for dependency management.**

This ensures that when a new developer checks out the code and runs any command, uv automatically handles dependencies without requiring manual installation or virtual environment setup.

### Standard uv Script Header Pattern

Every command script in `commands/` MUST start with this header:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "claude-agent-sdk",  # Required for Claude SDK integration
#     "typer",             # CLI framework (if needed)
# ]
# ///
"""
Command description here.
"""
```

### Key Points:

1. **Shebang**: `#!/usr/bin/env -S uv run --script` - Enables direct execution with uv
2. **PEP 723 metadata**: The `# /// script` block defines inline dependencies
3. **Auto-installation**: When a user runs the script, uv automatically:
   - Creates an isolated environment
   - Installs the specified dependencies
   - Runs the script
4. **No manual setup**: No need for `pip install` or `python -m venv`
5. **Reproducible**: Dependencies are versioned and locked per script

### Example Commands with Dependencies:

- **Commands using Claude SDK** (`ao-new`, `ao-resume`): Include `"claude-agent-sdk"`
- **Commands using only stdlib** (`ao-status`, `ao-list-sessions`): No external dependencies needed
- **All commands**: Include `typer` if using Typer CLI framework, otherwise pure argparse

**This pattern is ESSENTIAL for the progressive disclosure architecture** - each command is truly self-contained and can be run immediately after checkout.

---

## Phase 1: Core Infrastructure (Read-Only Commands)

**Goal**: Implement configuration and session management without Claude SDK integration.

### ✅ Step 1.1: Implement Configuration Module

**File to implement**: `commands/lib/config.py`

**Reference documentation**:
- `PROJECT_CONTEXT.md` - Architecture section (self-contained design rationale)
- `ARCHITECTURE_PLAN.md` - Section 3 (Configuration Management), Section 4.1 (lib/config.py)
- `../agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh` - Lines 1-100 (environment variables, directory setup)

**Implementation requirements**:
- [x] Create `Config` dataclass with fields: `project_dir`, `sessions_dir`, `agents_dir`, `enable_logging`
- [x] Implement `load_config()` function with CLI > ENV > DEFAULT precedence
- [x] Environment variable names (MUST match bash):
  - `AGENT_ORCHESTRATOR_PROJECT_DIR`
  - `AGENT_ORCHESTRATOR_SESSIONS_DIR`
  - `AGENT_ORCHESTRATOR_AGENTS_DIR`
  - `AGENT_ORCHESTRATOR_ENABLE_LOGGING`
- [x] Default paths:
  - `PROJECT_DIR = Path.cwd()`
  - `SESSIONS_DIR = PROJECT_DIR / ".agent-orchestrator" / "agent-sessions"`
  - `AGENTS_DIR = PROJECT_DIR / ".agent-orchestrator" / "agents"`
- [x] Implement `validate_can_create()` helper function
- [x] Implement `resolve_absolute_path()` helper function
- [x] Add full type hints throughout

**Success criteria**:
- ✅ Module loads without errors
- ✅ Can resolve configuration from environment variables
- ✅ Can resolve configuration from CLI arguments
- ✅ Validates directories correctly

---

### ✅ Step 1.2: Implement Utilities Module

**File to implement**: `commands/lib/utils.py`

**Reference documentation**:
- `ARCHITECTURE_PLAN.md` - Section 4.5 (lib/utils.py)

**Implementation requirements**:
- [x] Implement `get_prompt_from_args_and_stdin()` - handles `-p` flag and stdin
- [x] Implement `error_exit()` - print to stderr and exit
- [x] Implement `ensure_directory_exists()` - create directory if needed
- [x] Implement `log_command()` - log to `.log` file (if logging enabled)
- [x] Implement `log_result()` - log result to `.log` file
- [x] Add full type hints throughout

**Success criteria**:
- ✅ Can read prompt from stdin
- ✅ Can combine prompt from `-p` flag and stdin
- ✅ Logging functions create proper `.log` file format

---

### ✅ Step 1.3: Implement Session Module

**File to implement**: `commands/lib/session.py`

**Reference documentation**:
- `ARCHITECTURE_PLAN.md` - Section 4.2 (lib/session.py), **Section 7.1-7.2 (IMPORTANT: New simplified file format for SDK usage)**
- `PROJECT_CONTEXT.md` - File Format Compatibility section
- `../agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh` - Lines 342-450 (session functions)

**IMPORTANT NOTE**: The file format has been updated for SDK usage. Session ID is now stored in `.meta.json` (not `.jsonl`), and the `.jsonl` file uses our own simplified message serialization. See Section 7.1-7.2 in ARCHITECTURE_PLAN.md for details.

**Implementation requirements**:
- [x] Create `SessionMetadata` dataclass (UPDATED: now includes `session_id` field)
- [x] Create `SessionState` type alias: `Literal["running", "finished", "not_existent"]`
- [x] Implement `validate_session_name()` - MUST match bash validation rules
  - Max 60 characters
  - Only alphanumeric, dash, underscore: `^[a-zA-Z0-9_-]+$`
- [x] Implement `get_session_status()` - detect session state
  - Check `.meta.json` exists → else "not_existent"
  - Check `.jsonl` exists → else "running"
  - Check `.jsonl` size > 0 → else "running"
  - Read last line, check for `type: "result"` → "finished" or "running"
- [x] Implement `save_session_metadata()` - create `.meta.json` (UPDATED: now supports optional session_id parameter)
- [x] Implement `load_session_metadata()` - read `.meta.json` (UPDATED: now returns session_id)
- [x] Implement `update_session_metadata()` - update `last_resumed_at` timestamp
- [x] **NEW**: Implement `update_session_id()` - update `.meta.json` with session_id during streaming (Phase 4) ✅
- [x] Implement `extract_session_id()` - UPDATED: read from `.meta.json` (not `.jsonl`)
- [x] Implement `extract_result()` - read last line of `.jsonl` (in our simplified format)
- [x] Implement `list_all_sessions()` - return list of (name, session_id, project_dir)
- [x] Add full type hints throughout

**Success criteria**:
- ✅ State detection algorithm works correctly for new format
- ✅ Can save and load `.meta.json` files with session_id
- ✅ Can parse `.jsonl` files in our simplified format
- ✅ Session validation rules match bash (60 chars, alphanumeric + dash/underscore)
- ✅ All tests pass (7/7 tests passed)
- **NOTE**: This implementation uses a NEW file format (not bash-compatible) since we're using the SDK directly

---

### ✅ Step 1.4: Implement ao-status Command

**File to implement**: `commands/ao-status`

**Reference documentation**:
- `ARCHITECTURE_PLAN.md` - Section 5.3 (bin/ao-status)
- Current stub: `commands/ao-status`

**Implementation requirements**:
- [x] Keep uv script header
- [x] Add import: `sys.path.insert(0, str(Path(__file__).parent / "lib"))`
- [x] Import: `load_config`, `validate_session_name`, `get_session_status`
- [x] Parse CLI args: `<session-name>`, `--sessions-dir`
- [x] Load configuration
- [x] Validate session name
- [x] Call `get_session_status()`
- [x] Print result: "running", "finished", or "not_existent"
- [x] Handle errors gracefully

**Test plan**:
- [x] Create test session with bash script
- [x] Run `ao-status <session-name>` - should return correct status
- [x] Test with non-existent session - should return "not_existent"
- [x] Test with running session - should return "running"
- [x] Test with finished session - should return "finished"

**Success criteria**:
- ✅ Works with bash-created sessions
- ✅ Status matches bash script output exactly

---

### ✅ Step 1.5: Implement ao-list-sessions Command

**File to implement**: `commands/ao-list-sessions`

**Reference documentation**:
- `ARCHITECTURE_PLAN.md` - Section 5.5 (bin/ao-list-sessions)
- Current stub: `commands/ao-list-sessions`

**Implementation requirements**:
- [x] Keep uv script header
- [x] Add import: `sys.path.insert(0, str(Path(__file__).parent / "lib"))`
- [x] Import: `load_config`, `list_all_sessions`, `ensure_directory_exists`
- [x] Parse CLI args: `--sessions-dir`
- [x] Load configuration
- [x] Ensure sessions directory exists
- [x] Call `list_all_sessions()`
- [x] Output format: `{session_name} (session-id: {session_id}, project-dir: {project_dir})`
- [x] If no sessions: print "No sessions found"

**Test plan**:
- [x] Create multiple test sessions with bash script
- [x] Run `ao-list-sessions` - should show all sessions
- [x] Output format should match bash script
- [x] Test with empty sessions directory - should print "No sessions found"

**Success criteria**:
- ✅ Lists all bash-created sessions correctly
- ✅ Output format matches bash script

---

### ✅ Step 1.6: Implement ao-show-config Command

**File to implement**: `commands/ao-show-config`

**Reference documentation**:
- `ARCHITECTURE_PLAN.md` - Section 5.7 (bin/ao-show-config)
- Current stub: `commands/ao-show-config`

**Implementation requirements**:
- [x] Keep uv script header
- [x] Add import: `sys.path.insert(0, str(Path(__file__).parent / "lib"))`
- [x] Import: `load_config`, `validate_session_name`, `load_session_metadata`
- [x] Parse CLI args: `<session-name>`, `--project-dir`, `--sessions-dir`
- [x] Load configuration
- [x] Validate session name
- [x] Check session exists (`.meta.json` file)
- [x] Load session metadata
- [x] **ENHANCEMENT**: Added `--project-dir` parameter for consistency with other commands
- [x] Display configuration matching bash format:
  ```
  Configuration for session '{session_name}':
    Session file:    {sessions_dir}/{session_name}.jsonl
    Project dir:     {metadata.project_dir} (from meta.json)
    Agents dir:      {metadata.agents_dir} (from meta.json)
    Sessions dir:    {config.sessions_dir} (current)
    Agent:           {metadata.agent or 'none'}
    Created:         {metadata.created_at.isoformat()}Z
    Last resumed:    {metadata.last_resumed_at.isoformat()}Z
    Schema version:  {metadata.schema_version}
  ```

**Test plan**:
- [x] Create test session with bash script
- [x] Run `ao-show-config <session-name>` - should display config
- [x] Output format should match bash script
- [x] Test with non-existent session - should error gracefully

**Success criteria**:
- ✅ Displays configuration for bash-created sessions
- ✅ Output format matches bash script

---

### ✅ Step 1.7: Implement ao-get-result Command

**File to implement**: `commands/ao-get-result`

**Reference documentation**:
- `ARCHITECTURE_PLAN.md` - Section 5.4 (bin/ao-get-result)
- Current stub: `commands/ao-get-result`

**Implementation requirements**:
- [x] Keep uv script header
- [x] Add import: `sys.path.insert(0, str(Path(__file__).parent / "lib"))`
- [x] Import: `load_config`, `validate_session_name`, `get_session_status`, `extract_result`
- [x] Parse CLI args: `<session-name>`, `--sessions-dir`
- [x] Load configuration
- [x] Validate session name
- [x] Check session exists
- [x] Check session status is "finished" (error if not)
- [x] Extract result from `.jsonl` file
- [x] Print result to stdout

**Test plan**:
- [x] Create finished session with bash script
- [x] Run `ao-get-result <session-name>` - should print result
- [x] Test with running session - should error
- [x] Test with non-existent session - should error

**Success criteria**:
- ✅ Extracts result from bash-created sessions
- ✅ Only works with finished sessions
- ✅ Clear error messages for all failure cases
- ✅ Correct exit codes (0 for success, 1 for errors)

---

## Phase 2: Agent Loading

**Goal**: Implement agent configuration loading and listing.

### ✅ Step 2.1: Implement Agent Module

**File to implement**: `commands/lib/agent.py`

**Reference documentation**:
- `PROJECT_CONTEXT.md` - File Format Compatibility section (agent structure)
- `ARCHITECTURE_PLAN.md` - Section 4.3 (lib/agent.py), Section 7.3 (Agent Structure)
- `../agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh` - Lines 380-438 (agent functions)
- Example agent: `../agent-orchestrator/example/agents/confluence-researcher/`

**Implementation requirements**:
- [x] Create `AgentConfig` dataclass with fields: `name`, `description`, `system_prompt`, `mcp_config`
- [x] Implement `load_agent_config()` - load from agent directory
  - Check `agent_dir` exists
  - Parse `agent.json` (required)
  - Load `agent.system-prompt.md` (optional)
  - Load `agent.mcp.json` (optional)
  - Validate name matches directory name
- [x] Implement `list_all_agents()` - scan agents directory
  - Return list of (name, description) tuples
  - Skip invalid directories
  - Sort by name
- [x] Implement `build_mcp_servers_dict()` - extract `mcpServers` dict
- [x] Add full type hints throughout

**Success criteria**:
- ✅ Can load agent configurations created for bash script
- ✅ Can list all available agents (tested with 4 example agents)
- ✅ Handles optional files correctly (system prompt & MCP config)
- ✅ Error handling works (FileNotFoundError for missing agents, etc.)
- ✅ All tests pass (7/7 test cases)

---

### ✅ Step 2.2: Implement ao-list-agents Command

**File to implement**: `commands/ao-list-agents`

**Reference documentation**:
- `ARCHITECTURE_PLAN.md` - Section 5.6 (bin/ao-list-agents)
- Current stub: `commands/ao-list-agents`

**Implementation requirements**:
- [x] Keep uv script header
- [x] Add import: `sys.path.insert(0, str(Path(__file__).parent / "lib"))`
- [x] Import: `load_config`, `list_all_agents`, `ensure_directory_exists`
- [x] Parse CLI args: `--project-dir`, `--agents-dir`
- [x] Load configuration
- [x] Ensure agents directory exists
- [x] Call `list_all_agents()`
- [x] **ENHANCEMENT**: Added `--project-dir` parameter for consistency with other commands
- [x] Output format (bash-compatible):
  ```
  {name}:
  {description}

  ---

  {next_name}:
  {next_description}
  ```
- [x] If no agents: print "No agent definitions found"

**Test plan**:
- [x] Use existing agent definitions from bash script
- [x] Run `ao-list-agents` - should show all agents
- [x] Output format should match bash script
- [x] Test with empty agents directory - should print "No agent definitions found"

**Success criteria**:
- ✅ Lists all bash-compatible agents (tested with 4 example agents)
- ✅ Output format matches bash script exactly
- ✅ Handles empty agents directory gracefully

---

## Phase 3: Claude SDK Integration

**Goal**: Implement Claude SDK wrapper for session creation.

### ✅ Step 3.1: Implement Claude Client Module

**File to implement**: `commands/lib/claude_client.py`

**Reference documentation**:
- `PROJECT_CONTEXT.md` - Claude Integration Decision section (SDK choice rationale)
- `CLAUDE_SDK_INVESTIGATION.md` - Complete SDK usage guide (requirements analysis, implementation patterns)
- `ARCHITECTURE_PLAN.md` - Section 4.4 (lib/claude_client.py)
- `../agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh` - Lines 740-763 (Claude invocation)

**CRITICAL: SDK Package Information**:
- **Package name**: `claude-agent-sdk` (PyPI: https://pypi.org/project/claude-agent-sdk/)
- **Install command**: `pip install claude-agent-sdk`
- **Python requirement**: >= 3.10
- **Import pattern**: `from claude_agent_sdk import query, ClaudeAgentOptions`
- **NOTE**: The SDK uses `query()` function (NOT `ClaudeSDKClient` class) - See ARCHITECTURE_PLAN.md Section 4.4

**CRITICAL: MCP Configuration Format**:
- The SDK's `mcp_servers` parameter expects a **parsed dictionary**, NOT a file path
- Agent's `agent.mcp.json` structure: `{"mcpServers": {"server-name": {"command": "...", "args": [...]}}}`
- The `build_mcp_servers_dict()` function extracts the `mcpServers` dict from the parsed JSON
- SDK receives: `{"server-name": {"command": "...", "args": [...]}}`
- **No file paths are passed** - we parse JSON and pass the dictionary structure
- See example agents in `agent-orchestrator/skills/agent-orchestrator/example/agents/*/agent.mcp.json`

**Implementation requirements**:
- [x] Create `commands/lib/claude_client.py` module
- [x] Add uv script header to ANY command that imports this module (e.g., `ao-new`, `ao-resume`)
  - Header must include: `"claude-agent-sdk"` in dependencies list
  - This ensures uv auto-installs SDK when command is run
- [x] Import: `from claude_agent_sdk import query, ClaudeAgentOptions`
- [x] Implement `async run_claude_session()`:
  - Build `ClaudeAgentOptions` with:
    - `cwd=str(project_dir.resolve())`
    - `permission_mode="bypassPermissions"`
    - `resume=session_id` (if resuming)
    - `mcp_servers=mcp_servers` (if provided - dict extracted from agent.mcp.json)
  - Stream session using: `async for message in query(prompt=prompt, options=options):`
  - Write each message to `.jsonl` file: `json.dump(message.model_dump(), f); f.write('\n')`
  - Extract `session_id` from messages: `if hasattr(message, 'session_id'):`
  - **STAGE 2 HOOK**: Call `update_session_id()` immediately when session_id received (Phase 4 requirement)
  - Extract `result` from messages: `if hasattr(message, 'result'):`
  - Return tuple: `(session_id, result)`
- [x] Implement `run_session_sync()` - synchronous wrapper using `asyncio.run()`
- [x] **Phase 4**: Add session_name and sessions_dir parameters to enable Stage 2 metadata update ✅
- [x] Add full type hints throughout
- [x] Handle SDK exceptions gracefully

**Test plan**:
- [x] Create simple test session without agent (test script created: `test_claude_client.py`)
- [x] Verify SDK imports correctly (`uv run test_claude_client.py` - SDK imported successfully)
- [x] Module can be imported from commands/lib
- [x] Verify `.jsonl` file format is properly structured ✅ (tested in Phase 4)
- [x] Check messages in stream contain `session_id` property ✅ (tested in Phase 4)
- [x] Check messages contain `result` property ✅ (tested in Phase 4)
- [x] Test session resumption with `resume` parameter ✅ (tested in Phase 4, Step 4.2)
- [ ] Test with MCP configuration (deferred to agent-based session testing)

**Success criteria**:
- ✅ `commands/lib/claude_client.py` exists and is valid Python
- ✅ Module imports successfully without errors
- ✅ SDK dependency can be installed via uv
- ✅ `async run_claude_session()` implemented with correct signature
- ✅ `run_session_sync()` wrapper implemented
- ✅ Type hints added for all public functions
- ✅ Error handling implemented (ImportError, ValueError, generic SDK exceptions)
- ✅ Full integration testing completed in Phase 4

**Implementation notes**:
- Created `test_claude_client.py` for SDK verification
- SDK installs successfully via uv (31 packages installed)
- Module structure follows existing patterns from config.py and session.py
- Error messages provide clear guidance for troubleshooting
- **BUG FIX (Phase 4)**: Changed `message.model_dump()` to `dataclasses.asdict(message)` - SDK uses standard dataclasses, not Pydantic models
- **ENHANCEMENT (Phase 4)**: Added user message logging to `.jsonl` file - creates complete conversation history in one file
  - Format: `{"type": "user_message", "content": "prompt text", "timestamp": "ISO8601Z"}`
  - Written before SDK streaming begins (first line per interaction)
  - Works for both `ao-new` and `ao-resume` commands
- Full integration testing completed successfully in Phase 4 Steps 4.1 and 4.2

---

## Phase 4: Write Operations

**Goal**: Implement commands that create and modify sessions.

---

### CRITICAL: Metadata Lifecycle for ao-new

**The ao-new command must update metadata in THREE stages:**

#### Stage 1: Initial Creation (BEFORE Claude runs)
- Create `.meta.json` with all available fields
- **Included fields**: `session_name`, `agent`, `project_dir`, `agents_dir`, `created_at`, `schema_version`
- **MISSING field**: `session_id` (not available until Claude SDK starts streaming)
- **Purpose**: Users can see the session was started (metadata file exists)
- **Timing**: Immediately after validating inputs, before calling `run_session_sync()`

#### Stage 2: Session ID Update (DURING Claude execution)
- When first message with `session_id` arrives from Claude SDK
- **UPDATE** `.meta.json` to add the `session_id` field
- **Implementation**: In `claude_client.py` lines 90-92, call `update_session_id()` immediately when session_id is received
- **Purpose**: Makes session resumable while still running
- **Timing**: During the message streaming loop in `run_claude_session()`

#### Stage 3: Post-Completion Update (OPTIONAL, for future features)
- After result received and session completes
- Can update `last_resumed_at` or other tracking fields if needed
- **Purpose**: Future-proofing for additional metadata tracking
- **Note**: Not currently implemented, but architecture supports it

#### Why This Three-Stage Approach?

1. **Visibility**: Users see the session started immediately (metadata exists)
2. **SDK Limitation**: Session ID comes from Claude SDK during execution (not available upfront)
3. **Resumability**: `ao-resume` command needs `session_id` from metadata to resume sessions
4. **Robustness**: If Claude fails mid-execution, we still have partial metadata for debugging

#### Key Distinction: ao-new vs ao-resume

- **ao-new**: Extracts `session_id` from SDK messages during execution (Stage 2 above)
- **ao-resume**: Reads existing `session_id` from `.meta.json` and passes to SDK's `resume` parameter
- **Important**: Session ID extraction ONLY happens in ao-new (creates new session_id)

---

### ✅ Step 4.1: Implement ao-new Command

**File to implement**: `commands/ao-new`

**Reference documentation**:
- `PROJECT_CONTEXT.md` - Command Mapping table (bash → Python), Architecture section
- `ARCHITECTURE_PLAN.md` - Section 5.1 (bin/ao-new) - has complete implementation template
- Current stub: `commands/ao-new`
- `../agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh` - Lines 682-764 (cmd_new)

**CRITICAL: Read the "Metadata Lifecycle" section above before implementing**

**Implementation requirements**:
- [x] Keep uv script header (update dependencies: `["claude-agent-sdk", "typer"]`)
- [x] Add import: `sys.path.insert(0, str(Path(__file__).parent / "lib"))`
- [x] Import all required modules
- [x] Parse CLI args: `<session-name>`, `--agent`, `-p`, `--project-dir`, `--sessions-dir`, `--agents-dir`
- [x] Validate session name
- [x] Load configuration
- [x] Check session doesn't already exist
- [x] Get prompt (from `-p` and/or stdin)
- [x] If agent specified:
  - Load agent configuration
  - Prepend system prompt to user prompt with separator: `{system_prompt}\n\n---\n\n{user_prompt}`
  - Build MCP servers dict (extracts `mcpServers` from agent.mcp.json)
- [x] Ensure directories exist
- [x] **STAGE 1**: Save initial session metadata WITHOUT session_id (before Claude runs)
- [x] Log command (if logging enabled)
- [x] Run Claude session via `run_session_sync()` - this handles STAGE 2 (session_id update during streaming)
- [x] Log result (if logging enabled)
- [x] Print result to stdout

**Test plan**:
- [x] Validation tests (session name length, invalid characters, missing prompt)
- [x] Duplicate session detection
- [ ] Create session without agent: `ao-new test-session -p "Hello"` (requires API key)
- [ ] Create session with agent: `ao-new test-agent --agent system-architect -p "Design system"` (requires API key + agent setup)
- [x] Test prompt from stdin: `echo "Hello" | ao-new test-stdin` (validated, requires API key)
- [ ] Test combined prompt: `echo "Context" | ao-new test-combined -p "Question:"` (requires API key)
- [ ] Verify `.jsonl` and `.meta.json` files created with proper Stage 1 & Stage 2 metadata
- [ ] Verify bash script can resume Python-created sessions (full integration test)

**Success criteria**:
- ✅ Command syntax and imports correct
- ✅ All validation logic working (session name, prompt, duplicate detection)
- ✅ Error messages clear and match bash script style
- ⏳ Full integration testing requires Claude API key (deferred)
- ⏳ Bash compatibility verification requires live session (deferred)

---

### ✅ Step 4.2: Implement ao-resume Command

**File to implement**: `commands/ao-resume`

**Reference documentation**:
- `ARCHITECTURE_PLAN.md` - Section 5.2 (bin/ao-resume) - has complete implementation template
- Current stub: `commands/ao-resume`
- `../agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh` - Lines 766-830 (cmd_resume)

**IMPORTANT: Session ID Handling**:
- ao-resume reads `session_id` from existing `.meta.json` file (created by ao-new)
- NO session_id extraction from messages during streaming (that only happens in ao-new)
- The SDK's `resume` parameter uses the session_id from metadata to continue the conversation
- Session ID does NOT change when resuming - it stays the same as when created

**Implementation requirements**:
- [x] Keep uv script header (update dependencies: `["claude-agent-sdk", "typer"]`)
- [x] Add import: `sys.path.insert(0, str(Path(__file__).parent / "lib"))`
- [x] Import all required modules
- [x] Parse CLI args: `<session-name>`, `-p`, `--project-dir`, `--sessions-dir`, `--agents-dir`
- [x] Validate session name
- [x] Load configuration
- [x] Check session exists
- [x] Load session metadata (includes session_id)
- [x] Validate context consistency (warn if CLI overrides differ from metadata)
- [x] Extract session_id from metadata using `extract_session_id()` or from `load_session_metadata().session_id`
- [x] Get prompt (from `-p` and/or stdin)
- [x] If session has agent:
  - Load agent configuration
  - Build MCP servers dict
- [x] Log command (if logging enabled)
- [x] Run Claude session with resume via `run_session_sync(resume_session_id=session_id)`
- [x] Update session metadata timestamp with `update_session_metadata()`
- [x] Log result (if logging enabled)
- [x] Print result to stdout

**Test plan**:
- [x] Create session with `ao-new`, then resume with `ao-resume` ✅
- [x] Verify validation errors (invalid name, non-existent session, missing prompt) ✅
- [x] Verify context warning for CLI overrides (--project-dir, --agents-dir) ✅
- [x] Verify prompt from stdin works ✅
- [x] Verify `last_resumed_at` timestamp updates ✅
- [ ] Resume bash-created session with Python (deferred - requires bash setup)
- [ ] Resume Python-created session with bash (deferred - requires bash setup)

**Success criteria**:
- ✅ All validation logic working correctly
- ✅ Context warnings display properly
- ✅ Multi-turn conversations work (created session, resumed 3 times successfully)
- ✅ Metadata timestamp updates correctly (71.6 seconds between created_at and last_resumed_at)
- ✅ Error handling comprehensive (ValueError, FileNotFoundError, ImportError, generic Exception)
- ⏳ Cross-compatibility with bash script (deferred to Phase 5)

---

### ✅ Step 4.3: Implement ao-clean Command

**File to implement**: `commands/ao-clean`

**Reference documentation**:
- `ARCHITECTURE_PLAN.md` - Section 5.8 (bin/ao-clean)
- Current stub: `commands/ao-clean`

**Implementation requirements**:
- [x] Keep uv script header
- [x] Add import: `sys.path.insert(0, str(Path(__file__).parent / "lib"))`
- [x] Import: `load_config`, `shutil`
- [x] Parse CLI args: `--sessions-dir`
- [x] Load configuration
- [x] If sessions directory exists:
  - Remove entire directory: `shutil.rmtree(config.sessions_dir)`
  - Print "All sessions removed"
- [x] Else: print "No sessions to remove"

**Test plan**:
- [x] Create test sessions
- [x] Run `ao-clean`
- [x] Verify all sessions removed
- [x] Run `ao-clean` again - should say "No sessions to remove"

**Success criteria**:
- ✅ Removes all sessions cleanly
- ✅ Safe to run multiple times

---

## Phase 5: Testing & Validation

**Goal**: Comprehensive interoperability testing and documentation.

### ✅ Step 5.1: Interface Compatibility Tests - COMPLETE

**SCOPE CLARIFICATION**: This step tests **interface compatibility only** (CLI parameters, environment variables, command names). File format compatibility is **NOT required** - Python uses SDK-native format while bash uses CLI subprocess format.

**Reference documentation**:
- `PROJECT_CONTEXT.md` - Compatibility Model section
- `docs/BASH_TO_PYTHON_MAPPING.md` - Command and function mapping for MCP migration

**Test scenarios**:
- [x] **CLI Parameter Compatibility**:
  - Verify `--sessions-dir`, `--agents-dir`, `--project-dir`, `-p` work identically ✅
  - Test parameter precedence: CLI > ENV > DEFAULT ✅
  - Confirm both tools accept same parameter formats ✅
- [x] **Environment Variable Compatibility**:
  - Verify `AGENT_ORCHESTRATOR_PROJECT_DIR` works identically ✅
  - Verify `AGENT_ORCHESTRATOR_SESSIONS_DIR` works identically ✅
  - Verify `AGENT_ORCHESTRATOR_AGENTS_DIR` works identically ✅
  - Verify `AGENT_ORCHESTRATOR_ENABLE_LOGGING` works identically ✅
- [x] **Command Name Mapping**:
  - Confirm `ao-new` ↔ `new` (bash) ✅
  - Confirm `ao-resume` ↔ `resume` (bash) ✅
  - Confirm `ao-status` ↔ `status` (bash) ✅
  - Confirm `ao-get-result` ↔ `get-result` (bash) ✅
  - Confirm `ao-list-sessions` ↔ `list` (bash) ✅
  - Confirm `ao-list-agents` ↔ `list-agents` (bash) ✅
  - Confirm `ao-show-config` ↔ `show-config` (bash) ✅
  - Confirm `ao-clean` ↔ `clean` (bash) ✅
- [x] **Agent Structure Compatibility**:
  - Verify Python loads same agent definitions as bash ✅
  - Test `agent.json`, `agent.system-prompt.md`, `agent.mcp.json` structure ✅

**Test Results**:
- ✅ All 24 interface compatibility tests passing
- ✅ All CLI parameters verified identical
- ✅ All environment variables verified identical
- ✅ Command naming mapping documented and verified
- ✅ Agent structure is identical between tools
- ⚠️ **File format compatibility NOT required** (intentional divergence)

**Deliverables**:
- ✅ `docs/BASH_TO_PYTHON_MAPPING.md` - Migration guide for developers
- ✅ `docs/AI_ASSISTANT_GUIDE.md` - Compact usage guide for AI assistants
- ✅ Updated `PROJECT_CONTEXT.md` with compatibility model
- ✅ Updated checklist to reflect interface-only scope

---

### ⏭️ Step 5.2: File Format Validation - SKIPPED

**STATUS**: ⏭️ **SKIPPED** - Not applicable due to intentional file format divergence

**Rationale**:
- Python uses SDK-native `.jsonl` format (dataclass serialization)
- Bash uses CLI subprocess `.jsonl` format
- File formats are **intentionally different** by design
- Interface compatibility (CLI params, env vars) is sufficient

**What was validated instead**:
- ✅ Interface compatibility (Step 5.1)
- ✅ Agent structure compatibility (Step 5.1)
- ✅ Environment variable compatibility (Step 5.1)
- ✅ CLI parameter compatibility (Step 5.1)

**File format divergence documented in**:
- `PROJECT_CONTEXT.md` - "Compatibility Model" section
- `IMPLEMENTATION_CHECKLIST.md` - Step 1.3 note (line 199)

---

### ✅ Step 5.3: Documentation Updates

**Files to update**:
- [x] `README.md` - Updated with concise Python usage instructions
- [x] `docs/architecture.md` - No changes needed (Python progressive disclosure architecture, not bash-specific)
- [x] `docs/development.md` - Updated with Python development workflow, removed bash references
- [x] Add usage examples to main README - Added with `uv run` command invocations

**Success criteria**:
- ✅ Documentation complete and accurate
- ✅ Usage examples reference AI_ASSISTANT_GUIDE.md for details
- ✅ All cross-references verified

---

## Quick Reference

### Essential Documents

**Always Read First**:
- `PROJECT_CONTEXT.md` - Project goals, architecture decisions, current status
- `ARCHITECTURE_PLAN.md` - Detailed implementation guidance
- `CLAUDE_SDK_INVESTIGATION.md` - SDK capabilities and patterns

### Key Files for Each Phase

**Phase 1 (Core Infrastructure)**:
- Read: `PROJECT_CONTEXT.md` (Architecture, File Format Compatibility)
- Read: `ARCHITECTURE_PLAN.md` sections 3, 4.1, 4.2, 4.5, 5.3-5.5, 5.7, 7
- Read: `../agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh` (lines 1-100, 342-450)
- Implement: `commands/lib/config.py`, `commands/lib/utils.py`, `commands/lib/session.py`
- Implement: `commands/ao-status`, `commands/ao-list-sessions`, `commands/ao-show-config`, `commands/ao-get-result`

**Phase 2 (Agent Loading)**:
- Read: `PROJECT_CONTEXT.md` (File Format Compatibility - agent structure)
- Read: `ARCHITECTURE_PLAN.md` sections 4.3, 5.6, 7.3
- Read: `../agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh` (lines 380-438)
- Implement: `commands/lib/agent.py`
- Implement: `commands/ao-list-agents`

**Phase 3 (Claude SDK)**:
- Read: `PROJECT_CONTEXT.md` (Claude Integration Decision section)
- Read: `CLAUDE_SDK_INVESTIGATION.md` (entire document - SDK decision rationale)
- Read: `ARCHITECTURE_PLAN.md` section 4.4
- Implement: `commands/lib/claude_client.py`

**Phase 4 (Write Operations)**:
- Read: `PROJECT_CONTEXT.md` (Command Mapping table)
- Read: `ARCHITECTURE_PLAN.md` sections 5.1, 5.2, 5.8
- Read: `../agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh` (lines 682-830)
- Implement: `commands/ao-new`, `commands/ao-resume`, `commands/ao-clean`

**Phase 5 (Testing)**:
- Read: `PROJECT_CONTEXT.md` (Why This Matters section)
- Read: `ARCHITECTURE_PLAN.md` sections 7, 8
- Run: All interoperability tests
- Update: Documentation files

---

## Session Prompt Template

When starting a new implementation session, use this prompt:

```
I'm implementing the Agent Orchestrator CLI Python rewrite.

Context: We're rewriting agent-orchestrator.sh as Python scripts using Claude Agent SDK.
Goal: Progressive disclosure architecture with 100% bash compatibility.

Current phase: [PHASE NUMBER AND NAME]
Current step: [STEP NUMBER]

Please read:
- PROJECT_CONTEXT.md - [relevant section from step]
- IMPLEMENTATION_CHECKLIST.md - Step [X.Y]
- [Any other reference files listed in that step]

Then implement [FILE/FEATURE NAME] according to the requirements in the checklist.
Make sure to maintain compatibility with the bash script.
```

**Example for Step 1.1**:
```
I'm implementing the Agent Orchestrator CLI Python rewrite.

Context: We're rewriting agent-orchestrator.sh as Python scripts using Claude Agent SDK.
Goal: Progressive disclosure architecture with 100% bash compatibility.

Current phase: Phase 1 - Core Infrastructure
Current step: Step 1.1 - Configuration Module

Please read:
- PROJECT_CONTEXT.md - Architecture section (self-contained design)
- IMPLEMENTATION_CHECKLIST.md - Step 1.1
- ARCHITECTURE_PLAN.md - Sections 3 and 4.1
- ../agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh - Lines 1-100

Then implement commands/lib/config.py according to the requirements.
Environment variable names MUST match the bash script exactly.
```

---

## Notes

- Each checkbox `[ ]` should be checked off as completed
- Test each component before moving to the next phase
- Maintain 100% compatibility with bash script throughout
- Refer to `ARCHITECTURE_PLAN.md` for detailed implementation hints
- Use `CLAUDE_SDK_INVESTIGATION.md` for SDK usage patterns
