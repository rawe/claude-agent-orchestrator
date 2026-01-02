# Agent Orchestrator - Introduction Presentation Plan

## Target Audience
New developers and users who need to understand the system without being overwhelmed.

---

## Section 1: What Problem Does This Solve?

**Key Message:** You want to run AI agents, but a single agent isn't enough. You need multiple agents working together, monitored, and controlled.

Content to cover:
- Single AI agent limitation: one conversation, no visibility, no coordination
- The need: run multiple agents, see what they're doing, let them talk to each other
- Introduction of three core pieces: something to coordinate (Coordinator), something to execute (Runner), something to observe (Dashboard)

Visual: Simple diagram showing the problem → solution transformation

---

## Section 2: The Three Core Components

**Key Message:** The system has three parts, each with one job.

### 2.1 Agent Coordinator
- The "brain" - knows about all agents, sessions, and what's happening
- Runs as a server (port 8765)
- Stores everything in a database

### 2.2 Agent Runner
- The "worker" - actually runs the AI agents
- Connects to Coordinator, asks "any work for me?"
- Can run on different machines (distributed execution)

### 2.3 Dashboard
- The "window" - see everything happening in real-time
- Monitor agent conversations, view events, manage configurations

Visual: Three boxes with arrows showing registration flow (Runner → Coordinator ← Dashboard)

---

## Section 3: Your First Interaction - The Chat

**Key Message:** Start simple. One agent, one conversation, visible in the dashboard.

Step-by-step walkthrough:
1. Start the Coordinator server
2. Start the Dashboard
3. Start an Agent Runner (registers itself automatically)
4. Open Dashboard → see Runner is connected
5. Go to Chat tab → select an agent blueprint → type a message
6. Watch the conversation unfold in real-time

What happens under the hood:
- Dashboard sends message to Coordinator
- Coordinator creates a "session" and an "agent run"
- Runner picks up the agent run
- Runner spawns Claude Code executor
- Events stream back to Dashboard via SSE

Visual: Sequence diagram showing the message flow

---

## Section 4: From One Agent to Many - Orchestration

**Key Message:** Agents can start other agents. A parent agent can delegate tasks to children.

Why orchestration matters:
- Complex tasks require specialized agents
- Breaking work into subtasks improves quality
- One agent coordinates, others execute

How it works:
- Agents have access to an MCP server (agent-orchestrator-mcp)
- This MCP server provides tools to start/query other agents
- Parent agent decides when to spawn children

Visual: Tree diagram showing parent → children relationship

---

## Section 5: Execution Modes - How Parent and Child Interact

**Key Message:** Different situations need different coordination patterns.

### 5.1 Synchronous Mode
- Parent starts child and waits for completion
- Simplest mental model: "do this, wait, continue"
- Blocking: parent does nothing while waiting
- Use when: task is fast, result needed immediately

### 5.2 Asynchronous with Polling
- Parent starts child and continues working
- Periodically checks: "are you done yet?"
- Non-blocking but requires active checking
- Use when: task takes time, parent has other work

### 5.3 Fire and Forget
- Parent starts child and forgets about it
- No waiting, no checking
- Use when: result doesn't matter to parent, side effects are the goal

### 5.4 Callback Mode
- Parent starts child with `callback=true`
- Parent continues working
- When child completes, Coordinator automatically resumes parent
- Parent receives notification with child's result
- Use when: child task takes time but parent needs the result eventually

Visual: Four small diagrams showing each pattern with timeline

---

## Section 6: Agent Blueprints - Templates for Agents

**Key Message:** Agents are created from blueprints. Blueprints define what an agent can do.

What a blueprint contains:
- System prompt (personality, instructions)
- MCP configuration (which tools are available)
- Metadata (name, description)

Why blueprints matter:
- Reusable across many sessions
- Single source of truth for agent configuration
- Easy to version and manage

---

## Section 7: Capabilities - Modular Agent Configuration

**Key Message:** Instead of copying configuration between blueprints, extract common pieces into reusable "capabilities."

### 7.1 The Problem
- Multiple agents need similar tools (e.g., knowledge graph access)
- Copy-pasting MCP configs leads to inconsistency
- Updating one agent means updating all manually

### 7.2 The Solution: Capabilities
- A capability is a named, reusable configuration fragment
- Contains: allowed tools, MCP servers, environment variables
- Blueprints reference capabilities by name
- Resolution: Blueprint config + Capability configs = Final agent config

### 7.3 Example: Knowledge Graph Capability
- Capability name: `neo4j-knowledge-graph`
- Contains: Neo4j MCP server configuration, connection settings
- Any agent needing graph access just adds this capability
- Change Neo4j credentials once → all agents updated

Visual: Diagram showing Blueprint + Capability → Merged Configuration

---

## Section 8: Putting It All Together

**Key Message:** The system enables complex AI workflows with full visibility.

Recap the journey:
1. Started with basic chat (one agent, one conversation)
2. Added orchestration (agents starting agents)
3. Learned execution patterns (sync, async, polling, callback)
4. Understood configuration (blueprints, capabilities)

What you can build:
- Multi-agent research systems
- Automated code review pipelines
- Complex task decomposition workflows
- Specialized agent teams with shared capabilities

---

## Slide Count Estimate

| Section | Slides |
|---------|--------|
| 1. Problem | 2 |
| 2. Core Components | 3-4 |
| 3. First Chat | 3-4 |
| 4. Orchestration | 2-3 |
| 5. Execution Modes | 4-5 |
| 6. Blueprints | 2 |
| 7. Capabilities | 3-4 |
| 8. Summary | 1-2 |
| **Total** | **20-25** |

---

## Visual Assets Needed

1. Problem/Solution comparison diagram
2. Three-component architecture diagram
3. Chat flow sequence diagram
4. Parent-child agent tree
5. Four execution mode timeline diagrams
6. Blueprint structure diagram
7. Capability merging diagram
8. Full system overview (final slide)
