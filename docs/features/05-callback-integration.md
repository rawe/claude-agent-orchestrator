# Work Package 5: Callback Integration

**Reference**: [agent-callback-architecture.md](./agent-callback-architecture.md)
- Read sections: "Proposed Solution: Callback-Based Async", "Callback Aggregation (POC Behavior)", "Callback Flow", "Implementation Plan > Phase 5"

## Goal

When a child agent completes, automatically resume its parent orchestrator. The Callback Processor detects child completion, checks if parent is idle, and creates a resume job.

## Runnable State After Completion

- Full callback flow operational
- Orchestrator spawns children → goes idle → auto-resumes when children complete
- Multiple children: aggregated notification when parent becomes idle
- Success criteria from spec all met

## Files to Create

| File | Purpose |
|------|---------|
| `servers/agent-runtime/services/callback_processor.py` | Callback detection and job creation |

## Files to Modify

| File | Changes |
|------|---------|
| `servers/agent-runtime/main.py` | Wire callback processor into session events |

## Implementation Tasks

### 1. Callback Processor (`services/callback_processor.py`)

Core service with:

**State:**
```python
# In-memory notification queue (lost on restart - acceptable for POC)
pending_notifications: Dict[str, List[str]] = {}  # parent_session_name -> [child_names]
```

**Methods:**

```python
def on_session_stop(session_name: str, session_data: dict):
    """Called when any session stops (session_stop event)."""
    parent_name = session_data.get("parent_session_name")

    if not parent_name:
        # No parent, check if this session has pending notifications
        check_and_resume_with_pending(session_name)
        return

    # This is a child completing
    handle_child_completion(session_name, parent_name)

def handle_child_completion(child_name: str, parent_name: str):
    """Child completed - check if parent is idle or queue notification."""
    parent_status = get_session_status(parent_name)

    if parent_status == "finished":  # Parent is idle
        create_resume_job(parent_name, [child_name])
    else:
        # Parent still running - queue notification
        if parent_name not in pending_notifications:
            pending_notifications[parent_name] = []
        pending_notifications[parent_name].append(child_name)

def check_and_resume_with_pending(session_name: str):
    """Check if this session has pending child notifications."""
    if session_name in pending_notifications:
        children = pending_notifications.pop(session_name)
        create_resume_job(session_name, children)

def create_resume_job(session_name: str, completed_children: List[str]):
    """Create resume_session job with notification message."""
    message = format_callback_message(completed_children)
    job_queue.add_job(JobCreate(
        type="resume_session",
        session_name=session_name,
        prompt=message,
    ))
```

**Message Format:**
```python
def format_callback_message(children: List[str]) -> str:
    if len(children) == 1:
        return f"""## Agent Callback Notification

Agent session `{children[0]}` has completed.

To retrieve the result: `ao-get-result {children[0]}`"""
    else:
        child_list = "\n".join(f"- `{c}`" for c in children)
        return f"""## Agent Callback Notification

The following agent sessions have completed:
{child_list}

Use `ao-get-result <session-name>` to retrieve results."""
```

### 2. Wire into Session Events (`main.py`)

In the `POST /sessions/{id}/events` endpoint, after storing the event:

```python
@app.post("/sessions/{session_id}/events")
async def add_event(session_id: str, event: Event):
    # ... existing code to store event ...

    # Callback processing
    if event.event_type == "session_stop":
        session = get_session(session_id)
        if session:
            callback_processor.on_session_stop(
                session_name=session["session_name"],
                session_data=session,
            )

    # ... existing broadcast code ...
```

### 3. Handle Edge Cases

**Parent deleted while children running:**
- When creating resume job, verify parent session still exists
- If not, log warning and skip (per spec: graceful failure)

**Launcher not running:**
- Job sits in queue until launcher connects
- No special handling needed

**Multiple children complete simultaneously:**
- Each calls `on_session_stop`
- First one creates resume job (parent was idle)
- Subsequent ones queue (parent now running from first resume)
- When parent stops again, receives aggregated notification

### 4. Logging

Add concise logging for visibility:
```python
logger.info(f"Child '{child_name}' completed, parent '{parent_name}' is idle - creating resume job")
logger.info(f"Child '{child_name}' completed, parent '{parent_name}' still running - queuing notification")
logger.info(f"Session '{session_name}' stopped with {len(children)} pending child notifications")
```

## Testing Checklist

- [ ] Child completes while parent is idle → parent resumes immediately
- [ ] Child completes while parent is running → notification queued
- [ ] Parent stops with queued notifications → receives aggregated resume
- [ ] Multiple children complete → all listed in resume message
- [ ] Resume message includes `ao-get-result` instructions
- [ ] Parent can retrieve child results with `ao-get-result`
- [ ] Parent session deleted → callback fails gracefully (logged, no crash)

## Full Flow Test

1. Start orchestrator session via Dashboard
2. Orchestrator spawns child via `ao-start`
3. Orchestrator's prompt completes (goes idle)
4. Child runs its task
5. Child completes (session_stop event)
6. Callback Processor detects child completion
7. Checks parent status → "finished" (idle)
8. Creates resume_session job
9. Launcher picks up job
10. Orchestrator resumes with callback notification
11. Dashboard shows orchestrator running again

## Notes

- In-memory notification queue: lost on Agent Runtime restart (acceptable for POC)
- Session status "finished" = idle (per existing convention)
- Resume job's `prompt` contains the callback notification
- Child session names in message help orchestrator know which results to fetch
