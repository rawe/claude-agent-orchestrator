---
id: blueprints
title: "Agent Blueprints"
subtitle: "Templates that define what an agent can do"
---

## What is a Blueprint?

A blueprint is a reusable configuration template that defines an agent's identity, capabilities, and behavior.

### Example: code-reviewer

**System Prompt:**
> "You are an expert code reviewer. Analyze code for bugs, security issues, and best practices..."

**MCP Servers:**
- filesystem
- git
- github

**Tags:** (for discovery)
- development
- code-quality

**Demands:** (runner must satisfy)
- tags: docker

## Why Blueprints?

- **Reusable** - Define once, spawn many agent instances from it
- **Consistent** - All instances share the same abilities and MCP servers
- **Specialized** - Each blueprint focused on a specific task
