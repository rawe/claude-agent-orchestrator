# Solution C: Watch Both Filtered and Total Event Length

## Approach

Include both `events.length` and `filteredEvents.length` in the dependency array to ensure scroll triggers on any event change.

## Implementation

**File:** `agent-orchestrator-frontend/src/components/features/sessions/EventTimeline.tsx`

```diff
  // Auto-scroll to bottom when new events come in
  useEffect(() => {
    if (autoScroll && isRunning) {
      scrollToBottom();
    }
- }, [filteredEvents.length, autoScroll, isRunning]);
+ }, [events.length, filteredEvents.length, autoScroll, isRunning]);
```

## Pros

- Covers all cases (filtered and unfiltered events)
- Minimal change
- Triggers on filter changes as well

## Cons

- Redundant dependency - `events.length` alone is sufficient
- May cause double-scroll in some edge cases when both change
- Slightly confusing intent

## Recommendation

**Not recommended.** Redundant and potentially confusing. If `events.length` changes, we want to scroll. Adding `filteredEvents.length` provides no additional benefit since it's derived from `events`.

Solution A is cleaner and achieves the same result.
