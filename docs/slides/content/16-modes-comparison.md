---
id: modes-comparison
title: "Execution Modes Comparison"
subtitle: "Choose the right pattern for your use case"
---

## Mode Comparison

| Mode | Blocking | Gets Result | Complexity | Best For |
|------|----------|-------------|------------|----------|
| **Synchronous** | Yes | Immediate | Simple | Short-lived tasks, no timeout risk |
| **Async + Polling** | Yes (busy wait) | Via polling | Medium | Avoids timeout, but wastes tokens |
| **Fire & Forget** | No | Never | Simplest | Side effects, logging, notifications |
| **Callback** | No | Auto-notify | Advanced | Long tasks, efficient, no polling |

## Synchronous

Parent waits (blocked) while child executes. Gets result immediately. Not suitable for long-running tasks due to timeout issues.

## Async + Polling

Parent enters busy-wait loop, repeatedly checking if child is done. Avoids timeout issues but consumes tokens.

## Fire & Forget

Parent launches child and never looks back. No result is ever returned.

## Callback

Parent continues working freely. When child completes, Coordinator automatically resumes parent with the result. Most efficient for long-running tasks.
