---
id: motivation-interfaces
title: "Clean Interfaces"
subtitle: "Easy to connect, easy to adapt"
section: motivation
status: implemented
---

## Key Message

External systems should plug into the framework easily - without needing to understand its internals. Simple, uniform connection points.

**The problem it solves:** Integrating with agent frameworks often requires deep knowledge of how they work. Each integration is custom, brittle, and hard to maintain.

**The solution:** Well-defined APIs and patterns. Connect once, adapt as needed.

## Diagram Description

**Visual: Hub with Spokes**

Show Agent Orchestrator as a central hub with standardized connection points:

**Center: "Agent Orchestrator"**
- A rounded box or hexagon
- Shows: "API", "WebSocket", "Callbacks"

**Around it: External Systems**
- "Web App" connecting via API
- "CLI Tool" connecting via API
- "Webhook Service" connecting via Callbacks
- "Other Framework" connecting via API

All connections use the SAME interface pattern - no special handling per system.

The visual should convey: "One way to connect, works for everyone."

## Interface Principles

- **Simple:** Understand in minutes, not hours
- **Consistent:** Same patterns everywhere
- **Adaptable:** Extend without framework changes

## Status

Implemented

## Talking Points

- "You don't need to be a framework expert"
- "Standard REST API, standard WebSocket events"
- "If you've built a web app, you can integrate with this"
