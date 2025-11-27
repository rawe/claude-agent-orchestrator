# BUG-002: Implementation Report

## Status: RESOLVED

**Date:** 2025-11-27

## Changes

**File:** `agent-orchestrator-frontend/src/components/features/sessions/EventTimeline.tsx`

| Issue | Fix |
|-------|-----|
| `isRunning` gate blocked scroll for non-running sessions | Removed `isRunning` condition |
| Session change not detected | Track `session_id` via ref to detect selection change |
| `filteredEvents.length` missed filtered events | Watch `events` array directly |
| `scrollIntoView` timing unreliable | Use `scrollTop = scrollHeight` on container ref |
| Sentinel div at bottom | Removed, use container ref instead |

## Key Code

```typescript
const scrollContainerRef = useRef<HTMLDivElement>(null);
const prevEventsLengthRef = useRef<number>(0);
const prevFirstEventIdRef = useRef<string | undefined>(undefined);

const scrollToBottom = () => {
  if (scrollContainerRef.current) {
    scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
  }
};

useLayoutEffect(() => {
  const firstEventId = events[0]?.session_id;
  const sessionChanged = firstEventId !== prevFirstEventIdRef.current;
  const eventsAdded = events.length > prevEventsLengthRef.current;

  if (autoScroll && (sessionChanged || eventsAdded)) {
    scrollToBottom();
  }

  prevEventsLengthRef.current = events.length;
  prevFirstEventIdRef.current = firstEventId;
}, [events, autoScroll]);
```

## Autoscroll Now Triggers When

- User selects a different session
- New events arrive
- User enables autoscroll button
