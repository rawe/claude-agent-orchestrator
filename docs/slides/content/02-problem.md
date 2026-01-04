---
id: problem
title: "The Challenges"
subtitle: "Why building multi-agent systems is hard"
---

## Multi-Agent Coordination

Orchestrating multiple agents is harder than it looks:

- **Starting agents** - How do you spawn and manage multiple agent processes?
- **Waiting efficiently** - How do you wait for results without busy-polling?
- **Proper handover** - How do agents pass work between each other cleanly?
- **No visibility** - Without tooling, you have no insight into what's happening

See the [deep dive on Multi-Agent Coordination](02a-problem-multiagent.html) for more details.

## Context Sharing

Getting agents to share information efficiently is challenging:

- **Agents can't share documents** - Each agent operates in isolation
- **Full content wastes context window** - Passing entire files eats up tokens
- **No efficient handover mechanism** - No standard way to pass references
- **Orchestrator becomes bottleneck** - Everything must flow through one point

See the [deep dive on Context Sharing](02b-problem-context.html) for more details.

## Provider Lock-in

Being stuck with one AI provider limits flexibility:

- **Tightly coupled to one AI provider** - Code is built around one API
- **Can't mix cloud and local LLMs** - No way to use different models for different tasks
- **No abstraction layer** - Changing providers means rewriting code
- **Hard to switch or compare** - Testing alternatives requires significant effort

See the [deep dive on Provider Lock-in](02c-problem-provider.html) for more details.
