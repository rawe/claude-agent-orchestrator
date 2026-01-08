---
id: infrastructure
title: "Infrastructure Overhead"
subtitle: "Rebuilding the same foundation for every project"
parentId: motivation-problem
---

## The Repetition Problem

Every agentic tool project starts the same way:

1. **Set up orchestration** - How do agents communicate?
2. **Build execution layer** - How do we run agents?
3. **Add monitoring** - How do we see what's happening?
4. **Handle state** - How do we persist conversations?

Each team solves these problems from scratch. Again and again.

## What Gets Rebuilt

### Orchestration Logic
- Session management
- Message routing
- Agent lifecycle

### Execution Infrastructure
- Process spawning
- Health checks
- Error handling

### Observability
- Event streaming
- Logging
- Dashboards

### State Management
- Conversation history
- Context persistence
- Recovery mechanisms

## The Cost

- **Time**: Weeks spent on infrastructure before any agent logic
- **Bugs**: Each reimplementation introduces new issues
- **Maintenance**: Every team maintains their own version
- **Knowledge silos**: Solutions don't transfer between projects

## The Pattern

Frameworks like LangChain and AutoGen help, but:
- Still require significant setup
- Opinionated structures that may not fit
- Deep programming knowledge required
- Often too generic or too specific

**We need a reusable foundation that handles the common parts.**
