# Solution C: New session_resume Event Type

## Approach

Create a dedicated `session_resume` event type that the frontend handles separately from `session_start`. This provides clear semantic distinction between new and resumed sessions.

## Implementation

### Step 1: Send Resume Event from Backend

**File:** `plugins/agent-orchestrator/skills/agent-orchestrator/commands/lib/claude_client.py`

```diff
  else:
      # Resume: update last_resumed_at
      session_client.update_session(
          session_id=session_id,
          last_resumed_at=datetime.now(UTC).isoformat()
      )
+     # Send session_resume event
+     session_client.add_event(
+         session_id=session_id,
+         event_type="session_resume",
+         event_data={
+             "resumed_at": datetime.now(UTC).isoformat()
+         }
+     )
```

### Step 2: Handle in Frontend

**File:** `agent-orchestrator-frontend/src/hooks/useSessions.ts`

```diff
  if (event.event_type === 'session_start') {
    setSessions((prev) =>
      prev.map((s) =>
        s.session_id === event.session_id ? { ...s, status: 'running' } : s
      )
    );
  }
+ if (event.event_type === 'session_resume') {
+   setSessions((prev) =>
+     prev.map((s) =>
+       s.session_id === event.session_id ? { ...s, status: 'running' } : s
+     )
+   );
+ }
```

### Step 3: Update Event Filters (Optional)

**File:** `agent-orchestrator-frontend/src/components/features/sessions/EventTimeline.tsx`

```diff
  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
-     if (event.event_type === 'session_start' || event.event_type === 'session_stop') {
+     if (event.event_type === 'session_start' || event.event_type === 'session_stop' || event.event_type === 'session_resume') {
        return filters.session;
      }
      return true;
    });
  }, [events, filters]);
```

## Pros

- **Clear semantics** - Distinct event types for distinct actions
- **Better analytics** - Can track resumes separately from starts
- **Event history** - Resume is recorded in timeline with dedicated type
- **Extensible** - Can add resume-specific data/behavior later

## Cons

- **More changes** - Requires both backend and frontend updates
- **Duplicate logic** - Frontend handler is nearly identical to `session_start`
- **Filter updates** - Need to update event filtering logic

## Recommendation

**Not recommended for initial fix.** While semantically cleaner, this requires more changes. Solution A achieves the same result with less code. Consider this approach for a future refactor if distinct resume tracking is needed.
