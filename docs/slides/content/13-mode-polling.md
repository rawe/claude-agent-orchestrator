---
id: mode-polling
title: "Async + Polling"
subtitle: "Parent works and checks periodically"
---

## Mode 2 of 4: Asynchronous with Polling

In async + polling mode, the parent continues working while periodically checking if the child has completed.

### Timeline

1. **Parent starts child** and continues working on other tasks
2. **Child processes** the delegated task in parallel
3. **Parent polls** periodically: "Not ready... Not ready... Not ready..."
4. **Child completes** and parent's next poll returns: "Done!"
5. **Parent receives result** and can use it

## Characteristics

- **Parent is not blocked** - continues doing useful work
- **Requires active checking** for completion
- **Can do other work** while waiting

## Best For

Long-running tasks where the parent has other work to do but still needs the result.

### When to Use

- Tasks that take significant time to complete
- When the parent can make progress on other work
- When you need the result eventually but not immediately
- Batch processing scenarios
