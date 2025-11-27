# BUG-002: Autoscroll Not Triggering on New Events

## Problem

Autoscroll in the Event Timeline (session list event card) stopped working when new events (messages/tools/system messages) arrive. The scroll-to-bottom functionality fails to trigger for newly arriving events.

## Symptom

When a session is running and `autoScroll` is enabled:
- New events arrive and are added to the event list
- The view does NOT automatically scroll to show the new events
- User must manually scroll to see latest events

## Root Cause

The autoscroll `useEffect` watches `filteredEvents.length` instead of `events.length`:

```typescript
// Current (broken):
useEffect(() => {
  if (autoScroll && isRunning) {
    scrollToBottom();
  }
}, [filteredEvents.length, autoScroll, isRunning]);
```

**Why this breaks:**
1. New event arrives via WebSocket and is added to `events` array
2. If the event is filtered out by current filter settings (e.g., a message arrives but "Messages" filter is disabled), `filteredEvents.length` stays unchanged
3. Since the dependency didn't change, the `useEffect` doesn't run
4. `scrollToBottom()` is never called

## Files

**Affected Component:**
- `agent-orchestrator-frontend/src/components/features/sessions/EventTimeline.tsx:44-57` - Autoscroll useEffect

**Related Files:**
- `agent-orchestrator-frontend/src/hooks/useSessions.ts:136-158` - Event subscription hook
- `agent-orchestrator-frontend/src/contexts/WebSocketContext.tsx` - WebSocket event delivery
- `agent-orchestrator-frontend/src/components/features/sessions/AgentSessions.tsx:106` - `isRunning` prop source

## Additional Issue

Secondary condition requires `isRunning === true`:
```typescript
if (autoScroll && isRunning) {
```
If session status isn't properly updated to `'running'`, autoscroll won't work regardless of the primary fix.

## Solution Proposals

See:
- [Solution A: Watch events.length](./solution-a-watch-events-length.md)
- [Solution B: Separate event counter](./solution-b-event-counter.md)
- [Solution C: Watch both filtered and total](./solution-c-watch-both.md)
