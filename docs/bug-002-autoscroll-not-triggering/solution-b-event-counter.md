# Solution B: Separate Event Counter with useRef

## Approach

Use a ref to track the previous event count and trigger scroll when ANY new event arrives, decoupling the scroll trigger from the filtered events computation.

## Implementation

**File:** `agent-orchestrator-frontend/src/components/features/sessions/EventTimeline.tsx`

```typescript
const bottomRef = useRef<HTMLDivElement>(null);
const prevEventCountRef = useRef<number>(0);

const scrollToBottom = useCallback(() => {
  bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
}, []);

// Auto-scroll to bottom when new events come in
useEffect(() => {
  if (events.length > prevEventCountRef.current) {
    prevEventCountRef.current = events.length;
    if (autoScroll && isRunning) {
      scrollToBottom();
    }
  }
}, [events.length, autoScroll, isRunning, scrollToBottom]);
```

## Pros

- Explicit tracking of event count changes
- Only scrolls when count increases (not on re-renders)
- Clear intent in code

## Cons

- More complex than Solution A
- Additional ref to maintain
- Essentially achieves the same result with more code

## Recommendation

**Not recommended.** Adds unnecessary complexity. Solution A achieves the same goal with less code.
