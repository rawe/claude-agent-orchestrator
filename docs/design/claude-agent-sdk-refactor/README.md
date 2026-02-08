# Claude Agent SDK Executor — Design Documents

## Overview

Multi-turn architecture for the Claude SDK executor. The executor keeps a `ClaudeSDKClient`
alive across multiple turns, replacing the broken `--resume` CLI approach.

## Document Index

### Implementation Plan
- **`PHASE2-IMPLEMENTATION-PLAN.md`** — The master plan. Start here.

### Phase 2 Architecture Documents (authoritative)
| Document | Scope |
|----------|-------|
| `REGISTRY-REDESIGN.md` | Session-primary process registry (`_sessions` + `_run_index`) |
| `STOP-COMMAND-REDESIGN.md` | Stop commands flow as session_id |
| `SESSION-STATUS-REDESIGN.md` | 7 session statuses: pending, running, idle, stopping, finished, stopped, failed |
| `NDJSON-PROTOCOL-SIMPLIFICATION.md` | Remove run_id from executor NDJSON protocol |
| `EXECUTOR-SESSION-ID-SCOPE.md` | Bind stays, executor_session_id kept but not used for resume |

### Reference Documents
| Document | Scope |
|----------|-------|
| `PHASE1-IMPLEMENTATION-SUMMARY.md` | Phase 1 completed work and test results |
| `MULTI-TURN-EXECUTOR-ARCHITECTURE.md` | Executor process lifecycle, SDK internals |
| `NDJSON-PROTOCOL-REFERENCE.md` | NDJSON stdin/stdout protocol spec (being updated for run_id removal) |
| `MULTI-TURN-DESIGN.md` | Original design (Phase 1 sections accurate, Phase 2 superseded) |
| `PHASE2-RUNNER-ARCHITECTURE.md` | Original Phase 2 draft (partially superseded, lifecycle sections valid) |
| `BLOCKER.md` | Origin story: why we moved to multi-turn |
| `HANDOVER-INSTRUCTIONS.md` | How to write handover documents |
