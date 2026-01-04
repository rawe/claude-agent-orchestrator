---
id: chat-flow
title: "Message Flow Sequence"
subtitle: "Detailed view of a chat message lifecycle"
---

## The Complete Message Journey

A chat message travels through the entire system in seven steps:

### Step 1: Send Message
- **Dashboard** sends `POST /chat` request to the **Coordinator**

### Step 2: Create Session & Queue Run
- **Coordinator** creates a new session
- Queues the agent run for execution

### Step 3: Runner Picks Up Work
- **Agent Runner** long-polls with `GET /runs`
- **Coordinator** returns the agent run to the Runner

### Step 4: Spawn Executor
- **Runner** spawns a subprocess to execute the AI agent (Claude)

### Step 5: AI Processing
- **Claude** processes the request ("AI Thinking...")

### Step 6: Stream Events
- Events flow back through the chain:
  - Claude sends results to Runner
  - Runner forwards to Coordinator
  - Coordinator streams SSE events to Dashboard

### Step 7: Complete
- **Runner** signals completion to the **Coordinator**

## Key Participants

- **Dashboard** - User interface that initiates the chat
- **Coordinator** - Central hub that manages sessions and routing
- **Runner** - Executes agent tasks in isolated environments
- **Claude** - The AI model that processes requests
