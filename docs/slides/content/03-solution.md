---
id: solution
title: "The Solution Architecture"
subtitle: "Four components addressing the core challenges"
---

## Coordinator

The central brain that manages sessions, orchestrates agent lifecycles, and handles execution modes (sync, async, callback).

**Solves:** Agent Overload, Coordination, Infrastructure

## Runner

Executes agents via pluggable executors. Abstracts the AI provider, enabling Claude, OpenAI, or local LLMs.

**Solves:** Provider Lock-in, Infrastructure

## Context Store

Shared document storage with IDs. Agents pass references, not full content. Saves context window, enables efficient handover.

**Solves:** Context Sharing

## Dashboard

Real-time visibility into all agents. Monitor progress, view events, and control execution across the system.

**Provides:** Observability, Accessibility
