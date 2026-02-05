# Claude SDK Executor - Changelog

Concise log of refactoring changes. Each entry includes test status.

## [Unreleased]

### 2026-02-05: Switch from ClaudeSDKClient to query()

**Fix resume regression with SDK 0.1.30 (CLI 2.1.32)**

- Replaced `ClaudeSDKClient` (streaming mode) with `query()` (print mode)
- Root cause: `--resume` + `--input-format stream-json` broken in bundled CLI 2.1.32
- Output schema retry now resumes the session via `query()` instead of sending a second message in the same streaming connection

**Tests**: All 49 tests pass (full suite)

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
