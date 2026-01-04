---
id: mode-callback
title: "Callback Mode"
subtitle: "Child notifies parent when done"
---

## How It Works

The parent agent starts a child with `callback=true` and continues working on other tasks. When the child completes, the Coordinator automatically resumes the parent with the result.

- **Parent**: Starts child, works on other tasks, gets notified when child finishes
- **Child**: Processes task independently, completion triggers callback

The **Coordinator** handles the resume mechanism.

## Characteristics

- **Parent is not blocked** - Free to do other work
- **Automatic notification** on completion - No polling needed
- **Coordinator handles the resume** - Built-in orchestration support

## Best For

Long-running tasks where the parent needs the result but shouldn't poll.
