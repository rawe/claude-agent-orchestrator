---
id: agent-overload
title: "Agent Overload"
subtitle: "When a single agent tries to do everything"
parentId: motivation-problem
---

## The Problem: Single Agent Overload

A single agent trying to do everything:
- Review code
- Write tests
- Update docs
- Deploy changes

Result: Overwhelmed, context pollution, sequential execution.

## The Solution: Multi-Agent Orchestration

An **Orchestrator** delegates to specialized child agents:
- **Reviewer** - focuses on code review
- **Tester** - focuses on writing tests
- **Documenter** - focuses on documentation

## Why It Works

- **Parallel Execution** - Tasks run simultaneously, not one after another
- **Specialized Agents** - Each agent focuses on what it does best
- **Focused Context** - Smaller context windows = better results
- **Easy to Scale** - Add more agents as your needs grow
