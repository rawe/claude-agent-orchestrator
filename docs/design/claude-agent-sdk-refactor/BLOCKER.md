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

## Resolution Options

1. **Report bug** to Claude Code CLI team (resume regression in 2.1.x)
2. **Pin SDK version** to 0.1.16 temporarily (`claude-agent-sdk==0.1.16`)
3. **Investigate CLI changes** between 2.0.68 and 2.1.32 for resume handling
4. **Force system CLI** by setting `cli_path` in `ClaudeAgentOptions` to bypass bundled CLI

## Status

**Partially resolved** - Switched from `ClaudeSDKClient` (streaming mode) to `query()` (print mode) in the new executor. Resume works again. However, this introduced a new regression:

### New Issue: PostToolUse Hooks Do Not Fire in `query()` Mode

The SDK's hook mechanism requires a **bidirectional control protocol** between Python and the CLI subprocess. In `query()` mode (`--print`), stdin is closed after sending the prompt, so there is no channel for the CLI to send hook callbacks back to Python.

- `ClaudeSDKClient` (streaming): keeps stdin open, enables control protocol, hooks fire
- `query()` (print): closes stdin after prompt, no control protocol, **hooks never fire**

This means **post_tool events are no longer sent to the coordinator**. Tool calls still execute, but the executor cannot observe or report them.

The integration test `test_post_tool_events_sent` masked this because it uses a soft check:
```python
if len(post_tool_events) > 0:  # silently passes with 0 events
```

**Impact**: No tool call visibility in the dashboard or session event history.

**TODO**: Add a strict integration test that asserts post_tool events are actually sent (not a soft `if` check). This must fail when hooks are not firing so we catch regressions immediately.

### Resolution Path

The underlying problem is two SDK limitations that conflict:
1. Resume is broken in streaming mode (CLI 2.1.32)
2. Hooks only work in streaming mode

Both need to be resolved in the SDK before we can have resume + hooks working together. Options:
1. **Report hook limitation** to Claude Agent SDK team
2. **Pin SDK to older version** where both resume and streaming work (if such a version exists)
3. **Wait for SDK fix** for resume in streaming mode, then switch back to `ClaudeSDKClient`
