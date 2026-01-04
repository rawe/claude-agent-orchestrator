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

**Metadata:**
- version: 1.0
- category: development
- timeout: 300s

## Why Blueprints?

- **Reusable** - Define once, use across many sessions
- **Single Source of Truth** - All agents of a type share the same config
- **Version Controlled** - Track changes, rollback when needed
- **Specialized** - Each agent focused on a specific task
