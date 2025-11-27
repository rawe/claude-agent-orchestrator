# Solution A: Watch events.length Instead of filteredEvents.length

## Approach

Change the useEffect dependency from `filteredEvents.length` to `events.length` so autoscroll triggers on ANY new event, regardless of filter state.

## Implementation

**File:** `agent-orchestrator-frontend/src/components/features/sessions/EventTimeline.tsx`

```diff
  // Auto-scroll to bottom when new events come in
  useEffect(() => {
    if (autoScroll && isRunning) {
      scrollToBottom();
    }
- }, [filteredEvents.length, autoScroll, isRunning]);
+ }, [events.length, autoScroll, isRunning]);
```

## Pros

- **Simple fix** - Single line change
- **Consistent behavior** - Autoscroll triggers for every new event
- **No additional state** - Uses existing data

## Cons

- Triggers scroll even when new event isn't visible (filtered out)
- May cause unnecessary scroll operations if many filtered events arrive

## Recommendation

**Recommended as primary fix.** The slight overhead of scrolling on filtered events is negligible, and users expect autoscroll to keep them at the bottom regardless of filter state.
