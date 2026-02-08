# Origin: Why We Moved to Multi-Turn Architecture

## The Problem (2026-02-05)

The Claude CLI does not support `--resume` + `--input-format stream-json` (GitHub #16712).
This combination returns an empty `ResultMessage` in 0ms — no API call is made.

| SDK Version | Bundled CLI | Resume in Streaming Mode |
|-------------|-------------|--------------------------|
| 0.1.16 | 2.0.68 | Worked (by accident) |
| 0.1.30 | 2.1.32 | Broken |
| 0.1.31 | 2.1.33 | Intermittent |

The Python SDK bundles its own CLI binary at `_bundled/claude`. `SubprocessCLITransport._find_cli()`
checks the bundled CLI first, then system `claude`.

## Why Not Use `query()` Instead?

`query()` (print mode) supports resume but **loses PostToolUse hooks** — hooks are
non-negotiable for tool call visibility in the dashboard.

| Mode | Hooks | Resume | Protocol |
|------|:---:|:---:|----------|
| `ClaudeSDKClient` (streaming) | Yes | No | `--input-format stream-json` |
| `query()` (print) | No | Yes | `--print` |

## The Solution

Keep `ClaudeSDKClient` alive across multiple turns within a single process. Resume happens
via `client.query()` on the existing client instance — no CLI `--resume` needed. This is the
multi-turn architecture documented in `MULTI-TURN-DESIGN.md` and implemented in Phase 1.

## Key Insight

What looked like a path-dependent bug was actually a UV environment caching issue.
Old cached environments silently used older SDK versions with working resume. New
environments got the latest SDK with the broken CLI. See `MEMORY.md` for the UV caching
details.
