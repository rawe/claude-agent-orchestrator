# Executor Refactoring Blocker

## Problem

Resume tests fail with SDK 0.1.30. Initially appeared path-dependent, but root cause is a **bundled CLI regression**.

## Symptoms

- Error: `"No result received from Claude SDK"`
- Start works (~5s), resume fails fast (~2s)
- Session files only contain dequeue line, missing conversation data

## Root Cause

**The Python SDK bundles its own Claude CLI binary.** The bundled CLI version changed between SDK releases and introduced a resume regression.

| SDK Version | Bundled CLI Version | Resume Works |
|-------------|---------------------|--------------|
| 0.1.16      | **2.0.68**          | Yes          |
| 0.1.30      | **2.1.32**          | No           |
| 0.1.31      | **2.1.33**          | Intermittent (see below) |

The SDK's `SubprocessCLITransport._find_cli()` checks for a bundled CLI first (`_bundled/claude`) before falling back to the system-wide `claude` binary. Both versions exist at:
```
~/.cache/uv/environments-v2/<env>/lib/python3.12/site-packages/claude_agent_sdk/_bundled/claude
```

### How We Found This

1. Initially appeared path-dependent: copied executor failed, original passed
2. Discovered UV caches environments per script path with unpinned dependencies
3. Clearing UV cache made **both** executors fail (both got SDK 0.1.30)
4. Compared SDK Python source code: 0.1.16 and 0.1.30 are nearly identical
5. Found both SDKs bundle their own CLI binary - different sizes (165MB vs 181MB)
6. Confirmed bundled CLI versions: 2.0.68 (working) vs 2.1.32 (broken)

### UV Environment Behavior

- Each script path gets its own isolated environment (hash of full path)
- Dependencies are resolved at creation time, **not locked**
- Old environments kept working because they cached the older SDK + bundled CLI
- New environments get latest SDK + latest bundled CLI
- UV updates existing environments in-place when dependency specifiers change (e.g. adding `>=0.1.31` pin)

## History of Workarounds

### Attempt 1: Switch to `query()` (2026-02-05)

Switched from `ClaudeSDKClient` (streaming mode) to `query()` (print mode).

- **Result**: Resume works, but **PostToolUse hooks stopped firing**
- **Why**: `query()` closes stdin after sending the prompt, so there is no bidirectional control channel for hooks
- **Impact**: No tool call visibility in dashboard or session event history

### Attempt 2: Switch back to `ClaudeSDKClient` with SDK 0.1.31 (2026-02-06)

SDK 0.1.31 bundles CLI 2.1.33. Switched back to `ClaudeSDKClient` to restore hook support.

- Initially pinned `claude-agent-sdk>=0.1.31` to force UV cache update, but **removed the pin** again — pinning doesn't help since the issue is in streaming mode itself, not the SDK version
- **Result**: Resume works intermittently. An isolated test passed, but resume fails under repeated invocation

### Current Issue: Resume Fails Under Repeated CLI Invocation (CLI 2.1.33)

**Observed behavior with SDK 0.1.31 / CLI 2.1.33:**

| Scenario | Resume Result |
|---|---|
| Single isolated test (first run) | **PASS** |
| Same test run again immediately | **FAIL** |
| Full test suite (49 tests, resume tests run after ~34 others) | **FAIL** (all 7 resume tests) |
| Resume via `query()` mode (same SDK/CLI) | **PASS** (always) |

**Key observations:**
- Start always succeeds (~5s). Resume fails fast (~2s), suggesting the CLI exits immediately without making an API call
- Adding a 1-second sleep between start and resume helped on the first run, but not on subsequent runs
- The `query()` approach with the same SDK 0.1.31 / CLI 2.1.33 does NOT have this problem — all resume tests pass consistently
- This suggests the issue is specific to **streaming mode** (`--input-format stream-json` + `--resume`), not the CLI's resume capability itself

**Hypothesis:** The CLI 2.1.33 streaming mode (`ClaudeSDKClient`) has a session locking or state management issue that manifests under repeated invocation. The `query()` mode (`--print`) spawns a clean process each time and avoids this. This is a different bug from the CLI 2.1.32 regression (which was a total resume failure), but it affects the same code path.

### Why `query()` Doesn't Have This Problem

`query()` uses `--print` mode which:
1. Sends the prompt on stdin, closes stdin immediately
2. Reads stdout until EOF
3. Process exits cleanly

`ClaudeSDKClient` uses `--input-format stream-json` which:
1. Keeps stdin open for bidirectional communication (hooks, multi-turn)
2. Requires proper session file locking/unlocking between invocations
3. May leave session state in a transient condition that blocks subsequent resume

## Current Status

**Code is switched to `ClaudeSDKClient`** (streaming mode) for full hook support. Resume tests are failing intermittently due to CLI 2.1.33 streaming mode issue.

### Test Infrastructure Mitigation

Added `wait_for_session()` to the test harness (`RESUME_DELAY = 2` seconds) between start and resume invocations. This helps but does not fully resolve the issue under repeated invocation.

- `ExecutorTestHarness.RESUME_DELAY` — centrally configurable delay
- `ExecutorTestHarness.wait_for_session()` — called between start→resume in all tests
- `run_start_and_resume()` — helper method includes the delay automatically

### What Needs to Happen

1. **Report streaming resume bug** to Claude Code CLI team — resume with `--input-format stream-json` + `--resume` fails under repeated invocation in CLI 2.1.33
2. **Monitor SDK updates** — a fix in the bundled CLI would resolve this without code changes
3. **Fallback option**: Revert to `query()` if hook support is not immediately needed (loses PostToolUse events)
