# Solution A: Send session_start Event on Resume

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
+     session_client.add_event(
+         session_id=session_id,
+         event_type="session_start",
+         event_data={
+             "resumed": True,
+             "resumed_at": datetime.now(UTC).isoformat()
+         }
+     )
```

## Frontend Handling

No changes needed. The existing handler in `useSessions.ts:48-78` already processes `session_start`:

```typescript
if (event.event_type === 'session_start') {
  setSessions((prev) =>
    prev.map((s) =>
      s.session_id === event.session_id ? { ...s, status: 'running' } : s
    )
  );
}
```

## Pros

- **No frontend changes required** - Reuses existing event handler
- **Consistent behavior** - Same event type for new and resumed sessions
- **Event history** - Resume event is recorded in session events
- **Simple implementation** - Single backend change

## Cons

- Slightly overloads meaning of `session_start` (now means "start or resume")
- Event data needs `resumed: true` flag to distinguish from new sessions

## Recommendation

**Recommended.** This is the simplest fix with no frontend changes. The `resumed: true` flag in event data provides clarity while reusing existing infrastructure.
