---
id: chat-overview
title: "Your First Chat"
subtitle: "From message to AI response in 4 simple steps"
---

## The Message Flow

### Step 1: You

Type a message in the Dashboard chat interface.

Example: "Help me review code"

### Step 2: Dashboard

Sends your message to the Coordinator via HTTP.

### Step 3: Coordinator

Receives the message and queues an agent run for execution.

### Step 4: Runner

Picks up the queued run and executes the AI agent (Claude Code) to process your request.

## What Happens Behind the Scenes

The entire flow is designed to be:
- **Asynchronous** - You don't wait for the agent to finish
- **Observable** - Every step is visible in the Dashboard
- **Scalable** - Multiple runners can process work in parallel
