# Design: Rename Session Events to Run Events

**Status:** IMPLEMENTED
**Created:** 2026-01-06
**Completed:** 2026-01-06

All code changes implemented and verified. Builds pass for Python backend, Dashboard, and Chat-UI.

---

## Context

### Background

The Agent Orchestrator uses **events** to track session lifecycle. These events are:
- Stored in the coordinator's SQLite database (`events` table, `event_type` TEXT column)
- Broadcast via Server-Sent Events (SSE) to connected clients
- Consumed by the Dashboard and Chat-UI for real-time updates

### The Problem

Two lifecycle events are misnamed:

| Current Name | When It Fires | Why It's Wrong |
|--------------|---------------|----------------|
| `session_start` | When `report_run_started` is called | Fires on EVERY run (start + resume), not just session creation |
| `session_stop` | When `report_run_completed` is called | Fires on EVERY run completion, not when session ends permanently |

A **session** can have multiple **runs**:
- 1st run: `start_session` (creates session)
- 2nd run: `resume_session` (continues session)
- 3rd run: `resume_session` (continues session)
- etc.

Each run triggers `session_start` and `session_stop`, which is semantically incorrect.

### Recent Refactoring

We just moved lifecycle event emission from the **executor** to the **agent runner**:
- `report_run_started` endpoint now emits `session_start` event
- `report_run_completed` endpoint now emits `session_stop` event

This is the right time to fix the naming.

---

## Decision

Rename the event types:

| Old Value | New Value |
|-----------|-----------|
| `session_start` | `run_start` |
| `session_stop` | `run_completed` |

---

## Architecture: Where Events Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EVENT FLOW                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Agent Runner                                                               │
│       │                                                                     │
│       ├── POST /runner/runs/{id}/started ──────┐                           │
│       │                                        │                           │
│       └── POST /runner/runs/{id}/completed ────┼──► Agent Coordinator      │
│                                                │    (Python/FastAPI)       │
│                                                │         │                 │
│                                                │         ├─► SQLite DB     │
│                                                │         │   (events table)│
│                                                │         │                 │
│                                                │         └─► SSE Broadcast │
│                                                │              │            │
│                                                │              ▼            │
│                                                │         ┌─────────────┐   │
│                                                │         │  Dashboard  │   │
│                                                │         │  (React/TS) │   │
│                                                │         └─────────────┘   │
│                                                │              │            │
│                                                │              ▼            │
│                                                │         ┌─────────────┐   │
│                                                │         │  Chat-UI    │   │
│                                                │         │  (React/TS) │   │
│                                                │         └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Components Affected

### 1. Agent Coordinator (Backend - Python)

**Source of truth for event types.**

| File | What Changes |
|------|--------------|
| `servers/agent-coordinator/models.py` | `SessionEventType` enum: rename `SESSION_START` → `RUN_START`, `SESSION_STOP` → `RUN_COMPLETED` |
| `servers/agent-coordinator/main.py` | Event creation in `report_run_started` and `report_run_completed` endpoints |

### 2. Dashboard (Frontend - React/TypeScript)

**Consumes SSE events, displays event timeline.**

| File | What Changes |
|------|--------------|
| `dashboard/src/types/event.ts` | `EventType` union type |
| `dashboard/src/utils/constants.ts` | Event type icon mapping |
| `dashboard/src/services/unifiedViewTypes.ts` | `EventTypeValues` constants |
| `dashboard/src/services/unifiedViewService.ts` | Switch cases for event handling |
| `dashboard/src/contexts/ChatContext.tsx` | SSE event type comparisons |
| `dashboard/src/contexts/SessionsContext.tsx` | SSE event type comparisons |
| `dashboard/src/components/features/sessions/EventTimeline.tsx` | Event filtering and styling |
| `dashboard/src/components/features/sessions/EventCard.tsx` | Event config and rendering |
| `dashboard/src/pages/unified-view/utils.ts` | Event styling utilities |

### 3. Chat-UI (Frontend - React/TypeScript)

**Standalone chat interface, consumes SSE events.**

| File | What Changes |
|------|--------------|
| `interfaces/chat-ui/src/types/index.ts` | Event type in `SessionEvent` interface |
| `interfaces/chat-ui/src/contexts/ChatContext.tsx` | Switch cases for event handling |

### 4. Integration Tests (Markdown)

**Expected event sequences in test documentation.**

| File | What Changes |
|------|--------------|
| `tests/integration/01-basic-session-start.md` | Expected `session_start` → `run_start`, `session_stop` → `run_completed` |
| `tests/integration/02-session-resume.md` | Same |
| `tests/integration/03-session-with-agent.md` | Same |
| `tests/integration/04-child-agent-sync.md` | Same |
| `tests/integration/06-concurrent-callbacks.md` | Same |

### 5. Documentation (Markdown)

**API docs, data models, feature docs.**

Files containing `session_start` or `session_stop` string literals:
- `docs/components/agent-coordinator/API.md`
- `docs/components/agent-coordinator/DATA_MODELS.md`
- `docs/components/agent-coordinator/DATABASE_SCHEMA.md`
- `docs/components/agent-coordinator/USAGE.md`
- `docs/features/agent-callback-architecture.md`
- `docs/features/unified-session-run-view.md`
- `docs/adr/ADR-003-callback-based-async.md`
- `docs/refactoring/*.md`
- `dashboard/docs/CHAT-TAB.md`

### 6. Comments Only (No Functional Change)

Files with references in comments only:
- `servers/agent-runner/lib/supervisor.py` - Comments about event handling
- `servers/agent-coordinator/services/callback_processor.py` - Function `on_session_stopped` (name references old terminology but logic is correct)

---

## Implementation Plan

### Phase 1: Backend (Coordinator)

1. **Update enum** in `models.py`:
   ```python
   class SessionEventType(str, Enum):
       RUN_START = "run_start"          # was SESSION_START = "session_start"
       RUN_COMPLETED = "run_completed"  # was SESSION_STOP = "session_stop"
       PRE_TOOL = "pre_tool"
       POST_TOOL = "post_tool"
       MESSAGE = "message"
   ```

2. **Update event creation** in `main.py`:
   - `report_run_started`: Use `SessionEventType.RUN_START.value`
   - `report_run_completed`: Use `SessionEventType.RUN_COMPLETED.value`

3. **Verify**: Run coordinator, check events are created with new names.

### Phase 2: Dashboard

1. **Update types** in `dashboard/src/types/event.ts`
2. **Update constants** in `dashboard/src/utils/constants.ts` and `dashboard/src/services/unifiedViewTypes.ts`
3. **Update all event handlers** (contexts, components, utils)
4. **Build and test**: `npm run build` in dashboard

### Phase 3: Chat-UI

1. **Update types** in `interfaces/chat-ui/src/types/index.ts`
2. **Update event handlers** in `interfaces/chat-ui/src/contexts/ChatContext.tsx`
3. **Build and test**

### Phase 4: Tests & Documentation

1. **Update integration tests** with new expected event names
2. **Update documentation** (can be done incrementally)

---

## Migration Notes

### Database

- `event_type` is a TEXT column - no schema migration needed
- Old events remain with old names (`session_start`, `session_stop`)
- New events use new names (`run_start`, `run_completed`)
- Queries should handle both during transition (or accept mixed data)

### Breaking Change

This is a **breaking change** for SSE consumers:
- Dashboard must be updated before/with coordinator
- Chat-UI must be updated before/with coordinator
- Any external SSE consumers will break

### Rollback

If issues occur:
1. Revert coordinator changes (enum + main.py)
2. Frontends will continue working with old event names

---

## Summary

| Component | Files | Effort |
|-----------|-------|--------|
| Coordinator | 2 | Small |
| Dashboard | 9 | Medium |
| Chat-UI | 2 | Small |
| Tests | 5 | Small |
| Docs | 10+ | Medium |
| **Total** | **~28+ files** | **Medium** |

**Recommendation**: Implement in a single PR with all code changes. Documentation can follow.
