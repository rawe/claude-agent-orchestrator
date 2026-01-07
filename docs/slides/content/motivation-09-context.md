---
id: motivation-context
title: "Context Engineering"
subtitle: "Right information at the right time"
section: motivation
status: implemented
---

## Key Message

When agents collaborate, information gets passed repeatedly through the orchestrator - costly in tokens, prone to hallucination. Instead of passing full content, pass references. Let agents retrieve what they need directly.

**The problem it solves:** Research agent finds 50K tokens of data. Returns it to orchestrator. Orchestrator passes it to worker agent. Same content processed 3 times = 3x token cost + summarization errors.

**The solution:** Store documents, pass only IDs. Agents retrieve directly when needed. Orchestrator stays lightweight.

## Diagram Description

**Visual: Token Flow Comparison**

Split view - Before vs After:

**Left (Before): "The Token Problem"**
- Research Agent → (50K tokens) → Orchestrator → (50K tokens) → Worker Agent
- Show tokens as heavy blocks being passed
- Label: "150K tokens, multiple summaries, risk of hallucination"

**Right (After): "Context Store"**
- Research Agent → stores → Context Store → returns ID (tiny)
- Orchestrator passes only ID (tiny arrow)
- Worker Agent → retrieves directly from Context Store
- Label: "~500 tokens for handover, full fidelity"

The visual should show the dramatic difference in data flow.

## Key Benefit

**Eliminate token overhead & hallucination**

- Only the agent that needs content loads it
- No re-summarization required
- Orchestrator coordinates, doesn't need to understand everything
- Semantic search available for intelligent discovery

## Status

Implemented

## Talking Points

- "Context sharing is a hidden cost in multi-agent systems"
- "Pass references, not content"
- "The orchestrator doesn't need to read everything"
