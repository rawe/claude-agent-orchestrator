---
id: context
title: "Context Sharing Problem"
subtitle: "How agents share knowledge without wasting context windows"
parentId: problem
---

## Typical Research Handover

1. **Orchestrator** starts **Research Agent**
2. Research Agent finds **5 detailed documents** (~50K tokens)
3. **Entire content** returned to Orchestrator (50K tokens!)
4. Orchestrator passes to **Worker Agent** (50K again!)
5. **Context window explodes**, cost skyrockets

## Core Problems

### Full Content Transfer

Without shared storage, the **complete document content** must flow through the orchestrator to reach other agents.

### Context Window Waste

Orchestrator doesn't need to read 50K tokens of research - it just needs to **coordinate the handover**.

### Cost Multiplication

Same content processed multiple times: once by researcher, once by orchestrator, once by worker. **3x the cost**.

### No Selective Sharing

Can't say "here's a summary, details are in doc_abc123" - it's **all or nothing**.
