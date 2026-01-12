# Agent Orchestrator: Core Value Proposition

## What It Is

A **small core with extension points** for building AI-powered solutions.

The core does one thing: **coordinate agents**. Everything else is an extension.

---

## The Architecture (4 Parts)

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR APPLICATION                         │
│         (Custom UI, existing system, API client)            │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP API
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  AGENT COORDINATOR                          │
│            Sessions, Runs, Orchestration                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ Executor │    │ Executor │    │ Executor │
    │ Claude   │    │ OpenAI   │    │Procedural│
    └──────────┘    └──────────┘    └──────────┘
```

| Component | What It Does |
|-----------|--------------|
| **Agent Coordinator** | The core. Manages sessions, coordinates agent runs, provides the API. |
| **Agent Runner** | Picks up work, delegates to executors. Can run anywhere. |
| **Executors** | Pluggable. Claude Code today. OpenAI tomorrow. Or existing scripts. |
| **Your App** | Uses the Coordinator API. Dashboard is just one example. |

---

## The 4 Extension Points

### 1. Agent Definitions (Blueprints)

Text files. No code required.

- `agent.json` — Name, description, capabilities
- `agent.system-prompt.md` — What the agent does, in plain language

**Who can contribute:** PMs, concept people, domain experts — anyone who can write.

### 2. Executors

What actually runs the agent.

- **Autonomous** (AI-powered): Claude Code, OpenAI, local LLMs
- **Procedural** (deterministic): Existing scripts, CLI tools, APIs

Add a new executor = support a new provider or integrate existing tools.

### 3. MCP Servers (Tool Adapters)

Connect agents to external services.

- Context Store — shared documents between agents
- Neo4j — knowledge graphs
- Jira, Confluence — project management
- Any service with an API

Each MCP is an adapter. Add more as needed.

### 4. Custom Applications

The Coordinator exposes an API. Build any frontend:

- Customer-specific UI for their use case
- Integration into existing systems
- Embedded in other applications

The Dashboard is just one example app.

---

## Progressive Refinement: POC to Production

This is the key pattern. Start fast, refine over time.

### Phase 1: High-Level Agent (POC)

```
┌─────────────────────────┐
│     "Research Agent"    │  ← One agent does everything
│   (autonomous, AI)      │
└─────────────────────────┘
```

Quick to build. Prove the concept.

### Phase 2: Break Into Sub-Agents

```
┌─────────────────────────┐
│   "Research Agent"      │  ← Same interface to the outside
└───────────┬─────────────┘
            │ orchestrates
    ┌───────┼───────┐
    ▼       ▼       ▼
┌───────┐┌───────┐┌───────┐
│Search ││Analyze││Summary│  ← Specialized sub-agents
└───────┘└───────┘└───────┘
```

**The contract stays the same.** Internal structure changes.

### Phase 3: Replace with Procedural Agents

```
┌─────────────────────────┐
│   "Research Agent"      │
└───────────┬─────────────┘
            │
    ┌───────┼───────┐
    ▼       ▼       ▼
┌───────┐┌───────┐┌───────┐
│Search ││Analyze││Summary│
│(script)│ (AI)  │ (AI)  │
└───────┘└───────┘└───────┘
     ↑
  Faster, cheaper, deterministic
```

Replace AI with code where it makes sense. Keep AI where flexibility matters.

**Result:** Same interface. Better performance. Lower cost. More reliability.

---

## Why This Matters

| Benefit | How |
|---------|-----|
| **Fast start** | POC with autonomous agents in hours |
| **Stable interfaces** | Refine internals without breaking consumers |
| **Gradual optimization** | Replace AI with code piece by piece |
| **Provider independence** | Swap executors, keep everything else |
| **Team contribution** | Text-based agent definitions |
| **Integration ready** | API-first, connect to anything |

---

## For Customers

The Coordinator API is the integration point.

We build a **custom application** for their use case. Behind it, agents do the work. The customer sees their UI, not our infrastructure.

- Their branding, their workflow
- Agents tailored to their domain
- Connected to their systems via MCPs
- We control the complexity, they get the value
