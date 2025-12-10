# Work Package 6: Callback Queue for Busy Parents

**Status**: ✅ Complete

**Reference**: [agent-callback-architecture.md](./agent-callback-architecture.md), [05-callback-integration.md](./05-callback-integration.md)

## Problem Statement

When a parent agent is busy (executing a blocking operation like `sleep 20`), callbacks from completed child agents are lost. The current implementation in `agent-launcher/supervisor.py` creates resume jobs immediately without checking parent status.

**Scenario:**
1. Parent starts children with `callback=true`, then executes blocking command
2. Children complete while parent is busy
3. Resume jobs are created but fail (cannot resume already-running session)
4. Callbacks are silently lost

## Goal

Guarantee callback delivery by queuing notifications when parent is busy, then delivering them when parent becomes idle.

## Architecture Overview

```
CURRENT (BROKEN)                          FIXED
════════════════                          ═════

Child completes                           Child completes
      │                                         │
      ▼                                         ▼
┌─────────────┐                         ┌─────────────────────┐
│ LAUNCHER    │                         │ AGENT-RUNTIME       │
│ supervisor  │                         │ callback_processor  │
│             │                         │                     │
│ Creates     │                         │ Check parent status │
│ resume job  │                         │         │           │
│ immediately │                         │    ┌────┴────┐      │
└──────┬──────┘                         │    ▼         ▼      │
       │                                │  IDLE      BUSY     │
       ▼                                │    │         │      │
┌─────────────┐                         │ Create    Queue     │
│ Job fails   │                         │ job     notification│
│ (parent     │                         │    │         │      │
│  running)   │                         └────┼─────────┼──────┘
│             │                              │         │
│ CALLBACK    │                              ▼         ▼
│ LOST!       │                         Job runs   Parent stops
└─────────────┘                              │         │
                                             │    ┌────┘
                                             │    ▼
                                             │ Flush queue
                                             │ Create job
                                             │    │
                                             ▼    ▼
                                        ┌─────────────┐
                                        │ CALLBACK    │
                                        │ DELIVERED   │
                                        └─────────────┘
```

## Key Insight

Callback coordination must happen in **agent-runtime** (not agent-launcher) because:
- Agent-runtime has authoritative session status
- Agent-runtime receives all `session_stop` events
- Centralized queue survives launcher restarts

## Component Changes

### Primary: agent-runtime

| File | Change |
|------|--------|
| `servers/agent-runtime/services/callback_processor.py` | **NEW** - Core logic |
| `servers/agent-runtime/main.py` | Wire processor to `session_stop` events |

### Secondary: agent-launcher

| File | Change |
|------|--------|
| `servers/agent-launcher/lib/supervisor.py` | Remove callback logic (move to runtime) |

## Implementation

### 1. Callback Processor (`services/callback_processor.py`)

```python
"""
Callback Processor - queues and delivers child completion notifications.
"""
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

# In-memory queue: parent_session_name -> [child_names]
pending_notifications: Dict[str, List[str]] = {}


def on_child_completed(child_name: str, parent_name: str, parent_status: str):
    """Handle child session completion."""
    if parent_status == "finished":  # Parent idle
        create_resume_job(parent_name, [child_name])
    else:  # Parent busy
        queue_notification(parent_name, child_name)


def on_session_stopped(session_name: str):
    """Handle any session stopping - check for pending callbacks."""
    if session_name in pending_notifications:
        children = pending_notifications.pop(session_name)
        create_resume_job(session_name, children)


def queue_notification(parent_name: str, child_name: str):
    """Queue callback for later delivery."""
    if parent_name not in pending_notifications:
        pending_notifications[parent_name] = []
    pending_notifications[parent_name].append(child_name)
    logger.info(f"Queued callback: {child_name} -> {parent_name}")


def create_resume_job(parent_name: str, children: List[str]):
    """Create resume job with aggregated child results."""
    from services.job_queue import job_queue, JobCreate
    # Build prompt with child results
    # Add job to queue
    pass  # See 05-callback-integration.md for message format
```

### 2. Wire into main.py

In `POST /sessions/{session_id}/events`, after handling `session_stop`:

```python
if event.event_type == "session_stop":
    update_session_status(session_id, "finished")
    session = get_session_by_id(session_id)

    # Callback processing
    from services.callback_processor import on_child_completed, on_session_stopped

    parent_name = session.get("parent_session_name")
    if parent_name:
        # This is a child completing
        parent = get_session_by_name(parent_name)
        parent_status = parent["status"] if parent else "not_found"
        on_child_completed(session["session_name"], parent_name, parent_status)

    # Check if this session has pending child callbacks
    on_session_stopped(session["session_name"])
```

### 3. Remove from supervisor.py

Delete or disable `_trigger_callback_if_needed()` method. The supervisor should only report job completion to agent-runtime, not handle callback logic.

## Flow Diagram

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    Parent    │     │   Child 1    │     │   Child 2    │
│   Session    │     │   Session    │     │   Session    │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │ starts children    │                    │
       ├───────────────────►│                    │
       ├────────────────────┼───────────────────►│
       │                    │                    │
       │ executes           │                    │
       │ blocking cmd       │                    │
       │ (busy)             │                    │
       │                    │                    │
       │              completes                  │
       │                    │                    │
       │                    ▼                    │
       │        ┌───────────────────────┐        │
       │        │   CALLBACK PROCESSOR  │        │
       │        │                       │        │
       │        │ parent busy?          │        │
       │        │ YES -> queue          │        │
       │        │                       │        │
       │        │ pending["parent"] =   │        │
       │        │   ["child1"]          │        │
       │        └───────────────────────┘        │
       │                                         │
       │                               completes │
       │                                         │
       │                    ┌────────────────────┘
       │                    ▼
       │        ┌───────────────────────┐
       │        │   CALLBACK PROCESSOR  │
       │        │                       │
       │        │ parent busy?          │
       │        │ YES -> queue          │
       │        │                       │
       │        │ pending["parent"] =   │
       │        │   ["child1","child2"] │
       │        └───────────────────────┘
       │
       │ blocking cmd
       │ finishes
       │
       ▼
┌───────────────────────┐
│   CALLBACK PROCESSOR  │
│                       │
│ session stopped:      │
│ check pending queue   │
│                       │
│ found ["child1",      │
│        "child2"]      │
│                       │
│ CREATE RESUME JOB     │
│ with both results     │
└───────────────────────┘
       │
       ▼
┌──────────────┐
│    Parent    │
│   resumed    │
│              │
│ receives     │
│ aggregated   │
│ callback     │
└──────────────┘
```

## Investigation Tips

Before implementing, investigate:

1. **Session status lifecycle**: When exactly does status change to "finished"?
   - Check `POST /sessions/{id}/events` handling of `session_stop`
   - Trace through `database.py:update_session_status()`

2. **Current supervisor behavior**: Understand what happens now
   - Read `supervisor.py:_trigger_callback_if_needed()` completely
   - Check `api_client.py:create_resume_job()` implementation

3. **Job queue behavior**: How are resume jobs processed?
   - Check `services/job_queue.py` for job lifecycle
   - Understand `JobStatus` transitions

4. **Race conditions**: Multiple children completing simultaneously
   - How to handle concurrent `session_stop` events?
   - Consider thread safety of `pending_notifications` dict

5. **Edge cases to handle**:
   - Parent deleted while children running
   - Parent never stops (infinite loop)
   - Launcher restarts (in-memory queue lost)

## Testing Checklist

- [x] Child completes while parent idle -> immediate resume
- [x] Child completes while parent busy -> notification queued
- [x] Parent stops -> queued notifications delivered
- [x] Multiple children complete while busy -> aggregated in single resume
- [ ] Parent deleted -> graceful failure (no crash)
- [ ] Verify no duplicate deliveries

## Files Reference

```
servers/agent-runtime/
├── main.py                    # Wire callback processor here
├── database.py                # Session status queries
├── services/
│   ├── job_queue.py           # Job creation
│   └── callback_processor.py  # NEW: Core callback logic

servers/agent-launcher/
└── lib/
    ├── supervisor.py          # MODIFY: Remove callback logic
    └── api_client.py          # HTTP client (for reference)
```

## Notes

- In-memory queue is acceptable for POC (lost on restart)
- Session status "finished" means idle (available for resume)
- Aggregated messages help orchestrator know which results to fetch
- See `05-callback-integration.md` for message format template