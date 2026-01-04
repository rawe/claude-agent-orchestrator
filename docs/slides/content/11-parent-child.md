---
id: execution-strategies
title: "Execution Strategies"
subtitle: "How should the parent wait for child results?"
---

## The Fundamental Question

When a parent agent spawns a child, it faces a choice:

- **Wait and block?** Simple, but what if the child takes a long time?
- **Continue working?** Efficient, but how do we get the result back?

## The Trade-offs

| Concern | Question |
|---------|----------|
| **Blocking** | Can the parent do other work while waiting? |
| **Timeouts** | Will long-running children cause failures? |
| **Token cost** | How much does waiting/polling cost? |
| **Result delivery** | How does the parent receive the child's output? |

## Four Strategies

Different answers to these questions lead to four execution modes:

1. **Synchronous** - Block and wait
2. **Fire & Forget** - Don't wait, no result needed
3. **Polling** - Check periodically
4. **Callback** - Get notified when done

Let's explore each one...
