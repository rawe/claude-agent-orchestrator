---
id: solution
title: "The Solution Architecture"
subtitle: "Four components solving three challenges"
---

## Coordinator

The central brain that manages sessions, orchestrates agent lifecycles, and handles execution modes (sync, async, callback).

**Solves:** Multi-Agent Coordination

## Runner

Executes agents via pluggable executors. Abstracts the AI provider, enabling Claude, OpenAI, or local LLMs.

**Solves:** Multi-Agent Coordination, Provider Lock-in

## Context Store

Shared document storage with IDs. Agents pass references, not full content. Saves context window, enables efficient handover.

**Solves:** Context Sharing

## Dashboard

Real-time visibility into all agents. Monitor progress, view events, and control execution across the system.

**Provides:** Observability
