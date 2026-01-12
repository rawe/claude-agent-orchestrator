# Slide: Customer Integration - The API as the Bridge

## Title
**"Your Brand. Our Brains."**

## Key Message
Customers see their own application, not our infrastructure. The API is the invisible bridge between their world and the agent platform.

## Visual Description

**Layout:** Two-world split with bridge/API in the middle

**Design:**
```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│   CUSTOMER WORLD                    │        OUR PLATFORM            │
│   (what they see)                   │        (hidden)                │
│                                     │                                │
│   ┌───────────────────┐             │    ┌────────────────────┐      │
│   │   ╭─────────────╮ │             │    │                    │      │
│   │   │  ACME Corp  │ │             │    │   COORDINATOR      │      │
│   │   │  Dashboard  │ │             │    │   ┌──┐ ┌──┐ ┌──┐   │      │
│   │   │             │ │◄═══ API ═══►│    │   │A │ │B │ │C │   │      │
│   │   │  [custom    │ │             │    │   └──┘ └──┘ └──┘   │      │
│   │   │   content]  │ │             │    │     Agents         │      │
│   │   ╰─────────────╯ │             │    │                    │      │
│   │    Their brand    │             │    │   ┌────────────┐   │      │
│   │    Their colors   │             │    │   │ MCP: Jira  │   │      │
│   │    Their workflow │             │    │   │ MCP: Slack │   │      │
│   └───────────────────┘             │    │   │ MCP: ...   │   │      │
│                                     │    │   └────────────┘   │      │
│                                     │    └────────────────────┘      │
│                                     │                                │
└─────────────────────────────────────────────────────────────────────┘

         VISIBLE                    API              INVISIBLE
```

**Visual Style:**
- **Left side (Customer World):** Bright, clean, branded mockup of a custom app
  - Teal/blue tones (#1ABC9C, #3498DB)
  - Placeholder for "their logo"
  - Clean UI elements
- **Center (API):**
  - Thick double-line with arrows both ways
  - Labeled "API" in simple text
  - Acts as a clear divider
- **Right side (Our Platform):**
  - Gray/muted background (#7F8C8D)
  - Shows Coordinator and agent boxes
  - Connected to MCP boxes
  - Deliberately "infrastructure-looking"

**Key visual element:** A **curtain or wall metaphor** - the API is like a service window. Customer hands in requests, gets results back. Never sees the kitchen.

**Alternative metaphor (if preferred):**
Restaurant analogy with:
- Customer: Diner at table (nice tablecloth, their menu)
- API: Service window
- Platform: Kitchen (organized chaos, tools, processes)

## Text on Slide

**Left side labels:**
- "Customer's Application"
- "Their brand"
- "Their workflow"
- "Their users"

**Center:**
- "API" (large)
- "Requests in / Results out"

**Right side labels:**
- "Agent Platform"
- "Coordinator"
- "Agents"
- "Connections (MCPs)"

**Bottom callout:**
"We control complexity. They get value."

## Why This Visualization Works

1. **Two-world split** - instantly shows separation of concerns
2. **Branded mockup on left** - makes it concrete, not abstract
3. **Muted colors on right** - visual cue for "backend/hidden"
4. **API as clear divider** - shows this is the only touchpoint
5. **"Their brand" emphasis** - addresses white-label concerns
6. **MCP boxes visible** - shows we connect to their systems too
7. **"We control complexity"** - reassures that they don't need to understand internals

## Presenter Notes
This slide answers the question: "How do our customers actually use this?" The answer is: they don't see Agent Orchestrator at all. They see their own app, with their own brand, that happens to be powered by intelligent agents behind the scenes.

Key point: The API is the contract. Everything behind it can evolve without affecting the customer experience.
