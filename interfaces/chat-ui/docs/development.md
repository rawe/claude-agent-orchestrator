# Development Guide

## Key Files

| File | Purpose |
|------|---------|
| `contexts/ChatContext.tsx` | Chat state, message handling |
| `contexts/SSEContext.tsx` | SSE connection management |
| `services/api.ts` | REST API client |
| `components/Chat.tsx` | Main UI layout |
| `components/ToolCallBadge.tsx` | Tool status display |

## Adding Features

### New Message Type
1. Add type to `types/index.ts`
2. Handle in `ChatContext.tsx` → `handleSSEMessage()`
3. Render in `ChatMessage.tsx`

### New Tool Status
1. Add status config in `ToolCallBadge.tsx` → `statusConfig`
2. Update `ToolCall` type if needed

## Important Patterns

### Avoiding Stale Closures in SSE Callbacks
```typescript
// Store state in refs for SSE callbacks
const sessionNameRef = useRef(sessionName);
useEffect(() => { sessionNameRef.current = sessionName; }, [sessionName]);

// Use ref in callback
const handler = useCallback((msg) => {
  const currentName = sessionNameRef.current; // Always fresh
}, []);
```

### Stable SSE Subscription
```typescript
const handlerRef = useRef(handleMessage);
handlerRef.current = handleMessage;

useEffect(() => {
  const stable = (msg) => handlerRef.current(msg);
  return subscribe(stable);
}, [subscribe]);
```

## Styling

- Tailwind CSS 4 with `@import "tailwindcss"`
- Custom animations in `index.css`
- Prose classes for markdown content
