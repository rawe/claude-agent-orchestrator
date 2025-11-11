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
- [x] Implement `save_session_metadata()` - create `.meta.json` (UPDATED: now includes session_id parameter)
- [x] Implement `load_session_metadata()` - read `.meta.json` (UPDATED: now returns session_id)
- [x] Implement `update_session_metadata()` - update `last_resumed_at` timestamp
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
- [ ] Keep uv script header
- [ ] Add import: `sys.path.insert(0, str(Path(__file__).parent / "lib"))`
- [ ] Import: `load_config`, `list_all_sessions`, `ensure_directory_exists`
- [ ] Parse CLI args: `--sessions-dir`
- [ ] Load configuration
- [ ] Ensure sessions directory exists
- [ ] Call `list_all_sessions()`
- [ ] Output format: `{session_name} (session: {session_id}, project: {project_dir})`
- [ ] If no sessions: print "No sessions found"

**Test plan**:
- [ ] Create multiple test sessions with bash script
- [ ] Run `ao-list-sessions` - should show all sessions
- [ ] Output format should match bash script
- [ ] Test with empty sessions directory - should print "No sessions found"

**Success criteria**:
- Lists all bash-created sessions correctly
- Output format matches bash script

---

### ✅ Step 1.6: Implement ao-show-config Command

**File to implement**: `commands/ao-show-config`

**Reference documentation**:
- `ARCHITECTURE_PLAN.md` - Section 5.7 (bin/ao-show-config)
- Current stub: `commands/ao-show-config`

**Implementation requirements**:
- [ ] Keep uv script header
- [ ] Add import: `sys.path.insert(0, str(Path(__file__).parent / "lib"))`
- [ ] Import: `load_config`, `validate_session_name`, `load_session_metadata`
- [ ] Parse CLI args: `<session-name>`, `--sessions-dir`
- [ ] Load configuration
- [ ] Validate session name
- [ ] Check session exists (`.meta.json` file)
- [ ] Load session metadata
- [ ] Display configuration matching bash format:
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
- [ ] Create test session with bash script
- [ ] Run `ao-show-config <session-name>` - should display config
- [ ] Output format should match bash script
- [ ] Test with non-existent session - should error gracefully

**Success criteria**:
- Displays configuration for bash-created sessions
- Output format matches bash script

---

### ✅ Step 1.7: Implement ao-get-result Command

**File to implement**: `commands/ao-get-result`

**Reference documentation**:
- `ARCHITECTURE_PLAN.md` - Section 5.4 (bin/ao-get-result)
- Current stub: `commands/ao-get-result`

**Implementation requirements**:
- [ ] Keep uv script header
- [ ] Add import: `sys.path.insert(0, str(Path(__file__).parent / "lib"))`
- [ ] Import: `load_config`, `validate_session_name`, `get_session_status`, `extract_result`
- [ ] Parse CLI args: `<session-name>`, `--sessions-dir`
- [ ] Load configuration
- [ ] Validate session name
- [ ] Check session exists
- [ ] Check session status is "finished" (error if not)
- [ ] Extract result from `.jsonl` file
- [ ] Print result to stdout

**Test plan**:
- [ ] Create finished session with bash script
- [ ] Run `ao-get-result <session-name>` - should print result
- [ ] Test with running session - should error
- [ ] Test with non-existent session - should error

**Success criteria**:
- Extracts result from bash-created sessions
- Only works with finished sessions

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
- [ ] Create `AgentConfig` dataclass with fields: `name`, `description`, `system_prompt`, `mcp_config`
- [ ] Implement `load_agent_config()` - load from agent directory
  - Check `agent_dir` exists
  - Parse `agent.json` (required)
  - Load `agent.system-prompt.md` (optional)
  - Load `agent.mcp.json` (optional)
  - Validate name matches directory name
- [ ] Implement `list_all_agents()` - scan agents directory
  - Return list of (name, description) tuples
  - Skip invalid directories
  - Sort by name
- [ ] Implement `build_mcp_servers_dict()` - extract `mcpServers` dict
- [ ] Add full type hints throughout

**Success criteria**:
- Can load agent configurations created for bash script
- Can list all available agents
- Handles optional files correctly

---

### ✅ Step 2.2: Implement ao-list-agents Command

**File to implement**: `commands/ao-list-agents`

**Reference documentation**:
- `ARCHITECTURE_PLAN.md` - Section 5.6 (bin/ao-list-agents)
- Current stub: `commands/ao-list-agents`

**Implementation requirements**:
- [ ] Keep uv script header
- [ ] Add import: `sys.path.insert(0, str(Path(__file__).parent / "lib"))`
- [ ] Import: `load_config`, `list_all_agents`, `ensure_directory_exists`
- [ ] Parse CLI args: `--agents-dir`
- [ ] Load configuration
- [ ] Ensure agents directory exists
- [ ] Call `list_all_agents()`
- [ ] Output format (bash-compatible):
  ```
  {name}:
  {description}

  ---

  {next_name}:
  {next_description}
  ```
- [ ] If no agents: print "No agent definitions found"

**Test plan**:
- [ ] Use existing agent definitions from bash script
- [ ] Run `ao-list-agents` - should show all agents
- [ ] Output format should match bash script
- [ ] Test with empty agents directory - should print "No agent definitions found"

**Success criteria**:
- Lists all bash-compatible agents
- Output format matches bash script

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

**Implementation requirements**:
- [ ] Add dependency: `claude_agent_sdk` (check if available or use correct package name)
- [ ] Import: `from claude_agent_sdk import query, ClaudeAgentOptions`
- [ ] Implement `async run_claude_session()`:
  - Build `ClaudeAgentOptions` with:
    - `cwd=str(project_dir.resolve())`
    - `permission_mode="bypassPermissions"`
    - `resume=session_id` (if resuming)
    - `mcp_servers=mcp_servers` (if provided)
  - Stream messages via `async for message in query(prompt=prompt, options=options)`
  - Write each message to `.jsonl` file: `json.dump(message.model_dump(), f); f.write('\n')`
  - Capture `session_id` from first message with `session_id` attribute
  - Capture `result` from last message with `result` attribute
  - Return tuple: `(session_id, result)`
- [ ] Implement `run_session_sync()` - synchronous wrapper using `asyncio.run()`
- [ ] Add full type hints throughout

**Test plan**:
- [ ] Create simple test session without agent
- [ ] Verify `.jsonl` file format matches bash output
- [ ] Check first line contains `session_id`
- [ ] Check last line contains `result`
- [ ] Test with MCP configuration
- [ ] Test session resumption

**Success criteria**:
- Creates `.jsonl` files compatible with bash script
- Session ID extraction works
- Result extraction works

---

## Phase 4: Write Operations

**Goal**: Implement commands that create and modify sessions.

### ✅ Step 4.1: Implement ao-new Command

**File to implement**: `commands/ao-new`

**Reference documentation**:
- `PROJECT_CONTEXT.md` - Command Mapping table (bash → Python), Architecture section
- `ARCHITECTURE_PLAN.md` - Section 5.1 (bin/ao-new) - has complete implementation template
- Current stub: `commands/ao-new`
- `../agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh` - Lines 682-764 (cmd_new)

**Implementation requirements**:
- [ ] Keep uv script header
- [ ] Add import: `sys.path.insert(0, str(Path(__file__).parent / "lib"))`
- [ ] Import all required modules
- [ ] Parse CLI args: `<session-name>`, `--agent`, `-p`, `--project-dir`, `--sessions-dir`, `--agents-dir`
- [ ] Validate session name
- [ ] Load configuration
- [ ] Check session doesn't already exist
- [ ] Get prompt (from `-p` and/or stdin)
- [ ] If agent specified:
  - Load agent configuration
  - Prepend system prompt to user prompt
  - Build MCP servers dict
- [ ] Ensure directories exist
- [ ] Save session metadata
- [ ] Log command (if logging enabled)
- [ ] Run Claude session via `run_session_sync()`
- [ ] Log result (if logging enabled)
- [ ] Print result to stdout

**Test plan**:
- [ ] Create session without agent: `ao-new test-session -p "Hello"`
- [ ] Create session with agent: `ao-new test-agent --agent system-architect -p "Design system"`
- [ ] Test prompt from stdin: `echo "Hello" | ao-new test-stdin`
- [ ] Test combined prompt: `echo "Context" | ao-new test-combined -p "Question:"`
- [ ] Verify `.jsonl` and `.meta.json` files created
- [ ] Verify bash script can resume Python-created sessions

**Success criteria**:
- Creates sessions compatible with bash script
- Bash can resume Python-created sessions
- All file formats match exactly

---

### ✅ Step 4.2: Implement ao-resume Command

**File to implement**: `commands/ao-resume`

**Reference documentation**:
- `ARCHITECTURE_PLAN.md` - Section 5.2 (bin/ao-resume) - has complete implementation template
- Current stub: `commands/ao-resume`
- `../agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh` - Lines 766-830 (cmd_resume)

**Implementation requirements**:
- [ ] Keep uv script header
- [ ] Add import: `sys.path.insert(0, str(Path(__file__).parent / "lib"))`
- [ ] Import all required modules
- [ ] Parse CLI args: `<session-name>`, `-p`, `--project-dir`, `--sessions-dir`, `--agents-dir`
- [ ] Validate session name
- [ ] Load configuration
- [ ] Check session exists
- [ ] Load session metadata
- [ ] Validate context consistency (warn if CLI overrides differ from metadata)
- [ ] Extract session_id from `.jsonl` file
- [ ] Get prompt (from `-p` and/or stdin)
- [ ] If session has agent:
  - Load agent configuration
  - Build MCP servers dict
- [ ] Log command (if logging enabled)
- [ ] Run Claude session with resume via `run_session_sync(resume_session_id=session_id)`
- [ ] Update session metadata timestamp
- [ ] Log result (if logging enabled)
- [ ] Print result to stdout

**Test plan**:
- [ ] Create session with `ao-new`, then resume with `ao-resume`
- [ ] Resume bash-created session with Python
- [ ] Resume Python-created session with bash
- [ ] Verify context is preserved
- [ ] Verify `last_resumed_at` timestamp updates

**Success criteria**:
- Can resume bash-created sessions
- Bash can resume Python-resumed sessions
- Context preservation works correctly

---

### ✅ Step 4.3: Implement ao-clean Command

**File to implement**: `commands/ao-clean`

**Reference documentation**:
- `ARCHITECTURE_PLAN.md` - Section 5.8 (bin/ao-clean)
- Current stub: `commands/ao-clean`

**Implementation requirements**:
- [ ] Keep uv script header
- [ ] Add import: `sys.path.insert(0, str(Path(__file__).parent / "lib"))`
- [ ] Import: `load_config`, `shutil`
- [ ] Parse CLI args: `--sessions-dir`
- [ ] Load configuration
- [ ] If sessions directory exists:
  - Remove entire directory: `shutil.rmtree(config.sessions_dir)`
  - Print "All sessions removed"
- [ ] Else: print "No sessions to remove"

**Test plan**:
- [ ] Create test sessions
- [ ] Run `ao-clean`
- [ ] Verify all sessions removed
- [ ] Run `ao-clean` again - should say "No sessions to remove"

**Success criteria**:
- Removes all sessions cleanly
- Safe to run multiple times

---

## Phase 5: Testing & Validation

**Goal**: Comprehensive interoperability testing and documentation.

### ✅ Step 5.1: Bash/Python Interoperability Tests

**Reference documentation**:
- `ARCHITECTURE_PLAN.md` - Section 8 (Testing Strategy)

**Test scenarios**:
- [ ] **Bash creates, Python operates**:
  - Create session with bash `new` command
  - Check status with Python `ao-status`
  - Resume with Python `ao-resume`
  - Get result with Python `ao-get-result`
- [ ] **Python creates, Bash operates**:
  - Create session with Python `ao-new`
  - Check status with bash `status` command
  - Resume with bash `resume` command
  - Get result with bash `get-result` command
- [ ] **Cross-tool listing**:
  - Create sessions with both tools
  - List with both tools - should show all sessions
- [ ] **Agent-based sessions**:
  - Create with agent using bash
  - Resume with Python - verify agent config loaded
  - Create with agent using Python
  - Resume with bash - verify agent config loaded

**Success criteria**:
- 100% interoperability confirmed
- No compatibility issues found

---

### ✅ Step 5.2: File Format Validation

**Reference documentation**:
- `ARCHITECTURE_PLAN.md` - Section 7 (File Format Compatibility)

**Validation checks**:
- [ ] **Session files (`.jsonl`)**:
  - Compare bash vs Python output structure
  - Verify first line has `session_id`
  - Verify last line has `type: "result"` and `result`
  - Check JSON parsing works both ways
- [ ] **Metadata files (`.meta.json`)**:
  - Compare bash vs Python structure
  - Verify all required fields present
  - Check timestamp format matches
  - Verify schema version compatibility
- [ ] **Agent structure**:
  - Verify Python loads bash-style agents correctly
  - Check all optional files handled correctly

**Success criteria**:
- All file formats match exactly
- No parsing errors in either direction

---

### ✅ Step 5.3: Documentation Updates

**Files to update**:
- [ ] `README.md` - Update with Python usage instructions
- [ ] `docs/architecture.md` - Mark as legacy if needed
- [ ] `docs/development.md` - Update development instructions
- [ ] Add usage examples to main README

**Success criteria**:
- Documentation complete and accurate
- Usage examples work as documented

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
