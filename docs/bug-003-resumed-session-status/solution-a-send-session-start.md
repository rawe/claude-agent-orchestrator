# Solution A: Send session_start Event on Resume (Recommended)

## Approach

When a session is resumed, send a `session_start` event just like new sessions do. The frontend already handles this event type and will set the status to `"running"`.

## Implementation

**File:** `plugins/agent-orchestrator/skills/agent-orchestrator/commands/lib/claude_client.py`

```diff
  else:
      # Resume: update last_resumed_at
      session_client.update_session(
          session_id=session_id,
          last_resumed_at=datetime.now(UTC).isoformat()
      )
+     # Send session_start event to notify frontend of running state
+     session_client.add_event(session_id, {
+         "event_type": "session_start",
+         "session_id": session_id,
+         "session_name": session_name or session_id,
+         "timestamp": datetime.now(UTC).isoformat(),
+     })
```

## Why No Special Flag Needed

The frontend already handles `session_start` for existing sessions gracefully:

```typescript
// useSessions.ts:52-69
if (event.event_type === 'session_start') {
    setSessions((prev) => {
        const exists = prev.some((s) => s.session_id === event.session_id);
        if (exists) {
            // EXISTS: Just updates status to 'running'
            return prev.map((s) =>
                s.session_id === event.session_id ? { ...s, status: 'running' } : s
            );
        }
        // DOESN'T EXIST: Creates new entry
        return [{ session_id, status: 'running', ... }, ...prev];
    });
}
```

- If session exists → updates status to `'running'`
- If session doesn't exist → creates new entry
- No `resumed: true` flag necessary

## Pros

- **No frontend changes required** - Reuses existing event handler
- **Consistent behavior** - Same event type for new and resumed sessions
- **Event history** - Session start/resume is recorded in events timeline
- **Simple implementation** - Single backend change
- **Idempotent** - Safe to send multiple times

## Cons

- None significant

## Recommendation

**Recommended.** This is the simplest fix with no frontend changes and no special flags needed.
