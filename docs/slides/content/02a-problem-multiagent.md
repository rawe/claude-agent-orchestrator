---
id: multiagent
title: "Multi-Agent Coordination"
subtitle: "The challenge of orchestrating multiple AI agents"
parentId: motivation-problem
---

## The Coordination Challenge

When an orchestrator needs to spawn and manage multiple child agents (Research, Coder, Tester), fundamental questions arise:

- How to spawn?
- How to wait?
- How to collect results?
- How to cancel?

## Starting Agents

- **No standard API** to spawn child agents from a parent
- **Session management** - tracking parent-child relationships is difficult

## Waiting for Results

- **Busy-polling** wastes resources and API calls
- **Blocking** prevents parallel execution
- **Callbacks** need infrastructure to receive and route

## Control & Visibility

- **No dashboard** to see what agents are doing
- **No way to stop** runaway or stuck agents
