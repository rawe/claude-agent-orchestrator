---
id: runner
title: "Agent Runner"
subtitle: "The worker that executes agents"
accentColor: runner
---

## What It Is

The Agent Runner is the worker process that actually executes AI agents. It connects to the Coordinator and processes queued agent runs.

## The Execution Cycle

The runner operates in a continuous cycle:

1. **Poll for Agent Runs** - Check the Coordinator for queued work
2. **Execute via Executor** - Run the agent using the configured executor
3. **Report Status** - Send results and status updates back to the Coordinator
4. **Heartbeat Health Check** - Maintain connection with regular health signals

## Pluggable Executors

The runner uses executors to abstract the actual AI provider:

### Claude Code Executor
Uses the Claude Agent SDK to spawn AI sessions. This is the primary executor for running Claude-based agents.

## Provider Abstraction

By separating the runner from the executor, you can:
- Swap AI providers without changing orchestration logic
- Mix different providers for different agent types
- Run local LLMs alongside cloud providers
- Test with mock executors during development
