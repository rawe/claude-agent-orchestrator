---
id: mode-fire-forget
title: "Fire & Forget"
subtitle: "Start it and move on"
---

## Mode 2 of 4: Fire & Forget

### How It Works

The parent agent launches a child agent and immediately continues working without ever looking back. The child runs independently and completes on its own.

- **Parent**: Continues working, never looks back after launch
- **Child**: Processes independently, finishes on its own

**No result is returned to the parent.**

## Characteristics

- **Parent is completely free** - No blocking at all
- **No result returned** - Parent never receives output from child
- **Side effects only** - Child runs purely for its side effects

## Best For

Logging, notifications, background jobs where the result doesn't matter.
