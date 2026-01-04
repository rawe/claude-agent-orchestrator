---
id: mode-sync
title: "Synchronous Mode"
subtitle: "Parent waits for child to complete"
---

## Mode 1 of 4: Synchronous Execution

In synchronous mode, the parent agent is blocked while waiting for the child to complete.

### Timeline

1. **Parent works** on initial tasks
2. **Parent starts child** and enters waiting state
3. **Child processes** the delegated task
4. **Child completes** and returns result
5. **Parent continues** with the result

## Characteristics

- **Parent is blocked** while child runs
- **Result returned immediately** when done
- **Simplest mental model** - easy to reason about
- **Not for long-running tasks** - subject to timeout issues

## Best For

Short-lived sub-agents where the result is needed immediately to continue.

### When to Use

- Short-running operations
- Tasks where the result is required for the next step
- Simple delegation scenarios
- When parallel work is not possible
