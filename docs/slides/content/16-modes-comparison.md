---
id: modes-comparison
title: "Execution Modes Comparison"
subtitle: "Choose the right pattern for your use case"
---

## Mode Comparison

| Mode | Blocking | Gets Result | Complexity | Best For |
|------|----------|-------------|------------|----------|
| **Synchronous** | Yes | Immediate | Simple | Quick tasks needing immediate results |
| **Async + Polling** | No | Via polling | Medium | Long tasks, parent has other work |
| **Fire & Forget** | No | Never | Simplest | Side effects, logging, notifications |
| **Callback** | No | Auto-notify | Advanced | Long tasks, need result, no polling |

## Synchronous

Parent waits (blocked) while child executes. Gets result immediately when child completes.

## Async + Polling

Parent continues working and periodically checks if child is done. Gets result via polling mechanism.

## Fire & Forget

Parent launches child and never looks back. No result is ever returned.

## Callback

Parent continues working. When child completes, Coordinator automatically notifies parent with the result.
