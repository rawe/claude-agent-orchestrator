# Slide: Core Architecture

## Title
**"4 Building Blocks, Infinite Possibilities"**

## Key Message
The Agent Orchestrator has just 4 parts that work together. Your application talks to the Coordinator, which manages agents that do the actual work.

## Visual Description

**Layout:** Vertical stack diagram, top-to-bottom flow

**Design:**
```
┌─────────────────────────────────────────┐
│  YOUR APP                               │  ← Blue rounded rectangle (familiar)
│  [icon: laptop/screen]                  │
└────────────────┬────────────────────────┘
                 │ ← Gray dashed line labeled "API"
                 ▼
┌─────────────────────────────────────────┐
│  COORDINATOR                            │  ← Green rounded rectangle (hub)
│  [icon: traffic light / hub symbol]     │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  RUNNER                                 │  ← Orange rounded rectangle
│  [icon: running person / gear]          │
└────────────────┬────────────────────────┘
                 │
         ┌───────┼───────┐
         ▼       ▼       ▼
      ┌─────┐ ┌─────┐ ┌─────┐             ← Purple circles (workers)
      │ AI  │ │ AI  │ │Script│
      └─────┘ └─────┘ └─────┘
      EXECUTORS
```

**Colors:**
- Your App: Soft blue (#4A90D9) - represents the customer's world
- Coordinator: Green (#2ECC71) - the brain/hub
- Runner: Orange (#E67E22) - action/movement
- Executors: Purple circles (#9B59B6) - the workers

**Visual metaphor:** Like a company org chart. CEO (Your App) gives direction, Manager (Coordinator) organizes work, Team Lead (Runner) assigns tasks, Workers (Executors) do the job.

## Text on Slide

**Labels only:**
- "Your App" - "Custom UI or existing system"
- "Coordinator" - "Manages sessions & orchestration"
- "Runner" - "Picks up and delegates work"
- "Executors" - "AI or scripts - pluggable"

**No bullet points. Just labeled boxes.**

## Why This Visualization Works

1. **Top-to-bottom flow** is intuitive - shows clear chain of command
2. **Color coding** makes each layer instantly distinguishable
3. **The split at the bottom** (3 executors) shows flexibility visually without explaining it
4. **Familiar pattern** - looks like an org chart, which any PM understands
5. **No technical jargon** - just "Your App", "Coordinator", "Runner", "Executors"
