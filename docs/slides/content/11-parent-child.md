---
id: parent-child
title: "Parent-Child Agents"
subtitle: "The MCP server enables agents to spawn other agents"
---

## Hierarchical Agent Structure

An **Orchestrator Agent** (parent) can spawn multiple specialized **Child Agents** to divide and conquer complex tasks.

### Example Setup

- **Orchestrator Agent** (Parent) - Coordinates the work
  - **Code Reviewer** (Child) - Analyzes PR changes
  - **Test Writer** (Child) - Creates unit tests
  - **Doc Generator** (Child) - Updates README

## How It Works

1. **Parent has MCP server** with orchestration tools
2. **Calls `start_agent` tool** to spawn children
3. **Children run in parallel** as separate sessions
4. **Parent aggregates results** when complete

## The MCP Bridge

The `agent-orchestrator-mcp` server provides the connection between parent and child agents, enabling:

- Agent spawning via MCP tools
- Session isolation for each child
- Result collection and aggregation
