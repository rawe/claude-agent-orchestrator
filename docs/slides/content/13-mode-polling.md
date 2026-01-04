---
id: mode-polling
title: "Async + Polling"
subtitle: "Busy waiting with controlled intervals"
---

## Mode 3 of 4: Asynchronous with Polling

The parent starts a child agent and then enters a busy-wait loop, repeatedly checking for completion.

### Timeline

1. **Parent starts child** asynchronously (no timeout dependency)
2. **Child processes** the delegated task
3. **Parent polls** in a loop: "Not ready... Not ready... Not ready..."
4. **Child completes** and parent's next poll returns: "Done!"
5. **Parent receives result** and continues

## Characteristics

- **Parent is blocked** - busy waiting in a polling loop
- **Avoids MCP timeout issues** - no dependency on tool call timeouts (unlike sync mode)
- **Consumes tokens** - each poll is an LLM call
- **Requires tuning** - polling interval affects token cost and latency

## Trade-offs

Compared to **Sync mode**: Avoids timeout problems but wastes tokens on polling.

Compared to **Callback mode**: More token-expensive and still blocks the parent.

### When to Use

- When sync mode timeouts are a problem
- When callback mode is not available
- Short-to-medium tasks where polling overhead is acceptable
