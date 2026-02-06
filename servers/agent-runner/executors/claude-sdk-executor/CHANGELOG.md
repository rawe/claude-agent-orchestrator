# Claude SDK Executor - Changelog

Concise log of refactoring changes. Each entry includes test status.

## [Unreleased]

### 2026-02-05: Refactor entry point and extract executor module

**Extract `run_start`/`run_resume` from entry point into `lib/executor.py`**

- Extracted: `executor.py` — `run_start()`, `run_resume()` (~200 lines)
- Slimmed: `ao-claude-code-exec` now only handles CLI parsing and dispatch

### 2026-02-05: Extract modules and rename sdk_client

**Split monolithic `claude_client.py` into focused modules**

- Extracted: `mcp_transform.py` — `transform_mcp_servers_for_claude_code()`
- Extracted: `claude_config.py` — `ClaudeConfigKey`, `EXECUTOR_CONFIG_DEFAULTS`, `get_claude_config()`
- Extracted: `session_events.py` — `SessionEventEmitter` class, `post_tool_hook()`, `set_hook_emitter()`
- Renamed: `claude_client.py` → `sdk_client.py` (now contains only SDK session logic)
- Updated: `ao-claude-code-exec` imports from `sdk_client`

**Tests**: All 49 tests pass (full suite)

### 2026-02-05: Use SDK native structured outputs

**Replace ~140 lines of custom output schema code with SDK built-in support**

- Removed: `OutputSchemaValidationError`, `ValidationResult`, `validate_against_schema()`
- Removed: `extract_json_from_response()`, `enrich_system_prompt_with_output_schema()`
- Removed: `build_validation_error_prompt()`, manual retry loop
- Removed: `jsonschema` dependency from script header
- Added: `output_format={"type": "json_schema", "schema": ...}` in `ClaudeAgentOptions`
- Added: `message.structured_output` capture from `ResultMessage`
- SDK handles validation and retries internally

**Tests**: All 49 tests pass (full suite)

### 2026-02-05: Switch from ClaudeSDKClient to query()

**Fix resume regression with SDK 0.1.30 (CLI 2.1.32)**

- Replaced `ClaudeSDKClient` (streaming mode) with `query()` (print mode)
- Root cause: `--resume` + `--input-format stream-json` broken in bundled CLI 2.1.32
- Output schema retry now resumes the session via `query()` instead of sending a second message in the same streaming connection

**Known regression**: PostToolUse hooks do not fire in `query()` mode. The SDK hook
mechanism requires a bidirectional control protocol (stdin kept open) which is only
available in streaming mode. In `query()` mode, stdin is closed after sending the
prompt, so hook callbacks never reach Python. Post_tool events are not sent to the
coordinator. See `docs/design/claude-agent-sdk-refactor/BLOCKER.md` for details.

**Tests**: All 49 tests pass (soft check on post_tool events masks the regression)

### 2026-02-05: Initial Setup

**Created executor copy for refactoring**

- Copied from `executors/claude-code/`
- Files: `ao-claude-code-exec`, `lib/__init__.py`, `lib/claude_client.py`
- Created profile: `profiles/claude-sdk-executor.json`

---

## Test Command

```bash
cd servers/agent-runner
EXECUTOR_UNDER_TEST=executors/claude-sdk-executor/ao-claude-code-exec \
  uv run --with pytest pytest tests/integration/ -v
```
