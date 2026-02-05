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

**Resolved** - Switched from `ClaudeSDKClient` (streaming mode) to `query()` (print mode) in the new executor. All 49 tests pass. The bug is `--resume` + `--input-format stream-json` in CLI 2.1.32. Using `query()` avoids this by using `--print` mode instead.
