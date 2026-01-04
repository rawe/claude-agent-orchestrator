---
id: context-store
title: "Context Store"
subtitle: "Shared document storage for efficient agent handover"
---

## How It Works

Agents share data through a central document store:

1. **Research Agent** stores documents in the Context Store
2. **Orchestrator** receives lightweight references (document IDs)
3. **Worker Agent** retrieves full content when needed

## Key Benefits

### Pass References, Not Content

Agents exchange **document IDs** instead of full text. The orchestrator stays lightweight and doesn't need to pass large documents through its context window.

### Save Context Window

Only the agent that **needs** the content loads it. No duplication across agents.

- **Before**: 150K tokens passed between agents
- **After**: ~500 tokens (just the document IDs)

### Semantic Search

Agents can **search** stored documents by meaning, not just retrieve by ID. This enables intelligent document discovery and retrieval.
