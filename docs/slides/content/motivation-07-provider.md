---
id: motivation-provider
title: "Provider Independence"
subtitle: "No vendor lock-in"
section: motivation
status: implemented
---

## Key Message

Don't bet everything on one AI provider. Agent Runners abstract the underlying provider - you can switch without rewriting your agents.

**The problem it solves:** Most AI frameworks tie you to one provider (OpenAI, Anthropic, etc.). Switching means rewriting code, changing APIs, updating prompts.

**The solution:** The framework doesn't care which provider runs the agent. That's the runner's job.

## Diagram Description

**Visual: Abstraction Layer**

Show three layers:

**Top: "Your Agents"**
- Agent boxes that don't show any provider branding
- They're provider-agnostic

**Middle: "Agent Runners"**
- Multiple runner boxes
- Each labeled with a provider: "Claude Runner", "OpenAI Runner", "Local LLM Runner"

**Bottom: "AI Providers"**
- Provider logos/boxes: Anthropic, OpenAI, Ollama, etc.

Arrows flow down: Agents → Runners → Providers

The key visual: Agents at the top are ISOLATED from providers at the bottom.

## The Balance

Abstraction has costs. Too much abstraction:
- Hides provider-specific capabilities
- Adds complexity
- Makes debugging harder

Our approach:
- Abstract at the runner level
- Keep provider optimizations in executors
- Know when to stop

## Status

Implemented

## Talking Points

- "Currently running on Claude, but not locked in"
- "If a better provider emerges, we can switch"
- "The agents don't need to change"
