---
id: orchestrator-capability
title: "The Orchestrator Capability"
subtitle: "Enabling agents to spawn and manage sub-agents"
accentColor: capability
---

# The Orchestrator Capability

After defining **what** an agent can do through blueprints and capabilities, there's one special capability that unlocks **multi-agent workflows**: the **Agent Orchestrator Capability**.

## What Is It?

An embedded MCP server that runs inside each Agent Runner, providing tools for agents to programmatically start and manage other agents.

## What It Enables

Agents can:
- **Discover** available agent blueprints
- **Start** new child agent sessions
- **Resume** existing sessions
- **Check status** of running agents
- **Get results** from completed agents

## The 7 MCP Tools

| Tool | Purpose |
|------|---------|
| `list_agent_blueprints` | Discover available agents (filter by tags) |
| `list_agent_sessions` | View all active sessions |
| `start_agent_session` | Launch a new child agent with a prompt |
| `resume_agent_session` | Continue an existing child session |
| `get_agent_session_status` | Check if a child is running/finished |
| `get_agent_session_result` | Retrieve results from completed agents |
| `delete_all_agent_sessions` | Clean up all sessions |

## How It Works (High Level)

```
Parent Agent → Calls MCP Tool (e.g., start_agent_session)
                    ↓
            Embedded MCP Server (in Agent Runner)
                    ↓
            Agent Coordinator API
                    ↓
            Queues run for child agent
                    ↓
            Available Runner picks it up
                    ↓
            Child agent executes
                    ↓
            Result flows back to parent
```

## Key Points

- **Embedded in Agent Runner** - No external server needed
- **Automatic authentication** - Uses Runner's credentials
- **Parent-child tracking** - Sessions know their parent for callbacks
- **Multiple execution modes** - Sync, async poll, or callback

## The Bridge to Orchestration

With this capability, a simple agent becomes an **orchestrator** - able to delegate specialized tasks to other agents while maintaining overall control of the workflow.

Next: How parent and child agents work together, and the different execution modes available.
