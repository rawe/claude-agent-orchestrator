---
id: provider
title: "Provider Lock-in"
subtitle: "The challenge of building provider-agnostic agent systems"
parentId: motivation-problem
---

## The Lock-in Problem

All agents (Orchestrator, Research Agent, Coding Agent, Testing Agent) become chained to a single cloud provider.

## Direct API Coupling

Agent code directly imports and calls **provider-specific SDKs** (OpenAI, Anthropic). Changing provider means rewriting agent code.

## No Local LLM Option

Can't run **Ollama, LM Studio, or local models** for cost-sensitive or privacy-critical agents. Cloud-only architecture.

## Can't Mix Providers

What if you want **Claude for coding** but **GPT-4 for research**? Currently impossible without major refactoring.

## No A/B Testing

Hard to compare providers. Can't easily test if **switching to a cheaper model** degrades quality.

## What We Need

- Abstraction layer between agents and providers
- Pluggable executors (Claude, OpenAI, Local)
- Per-agent provider configuration
- Same agent blueprint, different backends
