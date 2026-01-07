# Agent Orchestrator - Vision & Concepts

This document explains the core pillars of the Agent Orchestrator framework, providing detailed descriptions and visualizations to convey the vision.

## Overview

```mermaid
graph TB
    subgraph "Core Pillars"
        RF[Reusable Foundation]
        PR[Progressive Refinement]
        HE[Hybrid Execution]
        CI[Clean Interfaces]
        PI[Provider Independence]
        DC[Decentralized Collaboration]
    end

    RF --> PR
    PR --> HE
    HE --> CI
    CI --> PI
    PI --> DC

    style HE fill:#e1f5fe,stroke:#01579b,stroke-width:3px
```

The highlighted pillar (Hybrid Execution) is the current focus.

---

## 1. Reusable Foundation

**The Problem:** Every time a team wants to build an agentic tool, they start from scratch - building orchestration, execution management, monitoring, and integration layers all over again.

**The Solution:** Agent Orchestrator provides a reusable core that handles the infrastructure, so teams can focus on their specific use case.

```mermaid
graph TB
    subgraph "Team-Specific Layer"
        A1[Knowledge Agent]
        A2[Research Agent]
        A3[Support Agent]
    end

    subgraph "Agent Orchestrator Core"
        C[Coordinator]
        R[Runner]
        M[Monitoring]
        S[State Management]
    end

    A1 --> C
    A2 --> C
    A3 --> C
    C --> R
    C --> M
    C --> S
```

**What this enables:**
- Build POCs quickly without infrastructure overhead
- Transition POCs to production on the same foundation
- Share learnings and patterns across projects

**Status:** Implemented

---

## 2. Progressive Refinement

**The Problem:** When starting with AI agents, the tendency is to build one large agent that "does everything." This works initially but becomes hard to maintain, debug, and improve.

**The Solution:** Start simple, then progressively break down agents into specialized, orchestrated components. This is a process for refining ideas - not just running them.

```mermaid
graph LR
    subgraph "Stage 1: Monolithic"
        M[Single Agent<br/>Does Everything]
    end

    subgraph "Stage 2: Specialized"
        O[Orchestrator]
        S1[Research<br/>Agent]
        S2[Analysis<br/>Agent]
        S3[Writing<br/>Agent]
        O --> S1
        O --> S2
        O --> S3
    end

    M -.->|Refine| O
```

**The refinement journey:**
1. Start with a simple, high-level agent ("AI can do everything")
2. Observe where it struggles or is inefficient
3. Extract that capability into a specialized agent
4. Orchestrate the specialists together
5. Repeat - each iteration adds focus and reliability

**Status:** Implemented

---

## 3. Hybrid Execution

**The Problem:** AI agents are powerful but non-deterministic and can be slow for certain tasks. Traditional programs are fast and reliable but can't reason. Currently, there's no clean way to combine both in the same orchestration.

**The Solution:** Treat AI agents and deterministic agents as peers. Both can be orchestrated, both can call each other, and a translation bridge handles the schema gap between unstructured and structured data.

### Architecture

```mermaid
graph TB
    subgraph "Coordinator"
        COORD[Agent Coordinator]
        BRIDGE[Schema Bridge]
    end

    subgraph "AI Agents"
        AI1[Research Agent]
        AI2[Analysis Agent]
    end

    subgraph "Deterministic Agents"
        D1[Crawler Agent]
        D2[Indexer Agent]
        D3[Database Agent]
    end

    COORD --> AI1
    COORD --> AI2
    COORD --> D1
    COORD --> D2
    COORD --> D3

    AI1 <-.->|via Bridge| D1
    D1 <-.->|via Bridge| AI2

    BRIDGE -.-> AI1
    BRIDGE -.-> D1
```

### The Schema Bridge

The core challenge is translating between two worlds:

```mermaid
graph LR
    subgraph "AI World"
        UP[Unstructured<br/>Prompt/Response]
    end

    subgraph "Bridge"
        T1[Output Schema<br/>Enforcement]
        T2[Input Schema<br/>Mapping]
    end

    subgraph "Deterministic World"
        SI[Structured<br/>Input]
        SO[Structured<br/>Output]
    end

    UP -->|AI Output| T1
    T1 -->|Structured| SI
    SO -->|Structured| T2
    T2 -->|Context| UP
```

**Key insight:** The framework owns the schema, not the agent. The coordinator knows:
- Which agent is calling
- What output schema is expected
- How to transform between formats

### Example: Research with Crawler

```mermaid
sequenceDiagram
    participant User
    participant Coord as Coordinator
    participant Research as Research Agent (AI)
    participant Crawler as Crawler (Deterministic)
    participant DB as Document Store

    User->>Coord: Research topic X
    Coord->>Research: Start research
    Research->>Coord: Need website data from example.com
    Coord->>Crawler: Crawl example.com (structured config)
    Crawler->>DB: Store crawled pages
    Crawler->>Coord: Complete (structured result)
    Coord->>Research: Data available in store
    Research->>DB: Query relevant content
    Research->>Coord: Research complete
    Coord->>User: Results
```

**Why deterministic agents?**
- **Faster:** No LLM inference overhead
- **Reliable:** Same input = same output
- **Efficient:** Optimized for specific tasks
- **Predictable:** Easier to debug and monitor

**Status:** Next Priority (Vision)

---

## 4. Clean Interfaces

**The Problem:** Integrating external systems with agent frameworks often requires deep knowledge of the framework internals. Each integration is custom.

**The Solution:** Provide uniform, well-defined connection points that external systems can plug into easily.

```mermaid
graph TB
    subgraph "External Systems"
        E1[Web App]
        E2[CLI Tool]
        E3[Webhook]
        E4[Other Framework]
    end

    subgraph "Agent Orchestrator"
        API[Unified API]
        WS[WebSocket Events]
        CB[Callbacks]

        subgraph "Core"
            C[Coordinator]
            R[Runners]
        end
    end

    E1 --> API
    E2 --> API
    E3 --> CB
    E4 --> API

    API --> C
    WS --> C
    CB --> C
```

**Interface principles:**
- Simple to understand, simple to use
- Consistent patterns across all connection types
- Easy to adapt without framework changes

**Status:** Implemented

---

## 5. Provider Independence

**The Problem:** AI frameworks often lock you into a specific provider (OpenAI, Anthropic, etc.). Switching providers means rewriting significant code.

**The Solution:** Agent Runners abstract the AI provider. The core framework doesn't know or care which provider executes the agent.

```mermaid
graph TB
    subgraph "Agent Orchestrator Core"
        C[Coordinator]
    end

    subgraph "Agent Runners"
        R1[Runner: Claude]
        R2[Runner: OpenAI]
        R3[Runner: Local LLM]
    end

    subgraph "AI Providers"
        P1[Anthropic API]
        P2[OpenAI API]
        P3[Ollama]
    end

    C --> R1
    C --> R2
    C --> R3

    R1 --> P1
    R2 --> P2
    R3 --> P3
```

**The balance:** Abstraction has costs. Too much abstraction adds complexity and hides provider-specific capabilities. The current approach:
- Abstract at the runner level
- Keep provider-specific optimizations in executors
- Don't over-abstract - know when to stop

**Status:** Implemented

---

## 6. Decentralized Collaboration

**The Problem:** Agent systems are typically centralized. One team controls the agents, one server runs them. This doesn't match how real teams work - distributed, with different expertise and access.

**The Solution:** Allow agent runners on different machines to contribute to a shared orchestration. Each team member can provide specialized agents.

```mermaid
graph TB
    subgraph "Shared Infrastructure"
        C[Agent Coordinator]
        K[(Knowledge Base)]
    end

    subgraph "Developer Machine"
        R1[Runner]
        A1[Code Agent]
        A2[Test Agent]
    end

    subgraph "Designer Machine"
        R2[Runner]
        A3[Design Review Agent]
    end

    subgraph "PM Machine"
        R3[Runner]
        A4[Requirements Agent]
    end

    R1 --> C
    R2 --> C
    R3 --> C

    A1 --> R1
    A2 --> R1
    A3 --> R2
    A4 --> R3

    C --> K
```

**The vision:**
- A project team shares an orchestrator and knowledge base
- Developer contributes code-related agents
- Designer contributes design review agents
- PM contributes requirements and process agents
- All agents can collaborate and share context
- Domain experts describe agents; programmers build capabilities

**Status:** Early Vision

---

## Current Focus

The immediate priority is **Hybrid Execution** - creating the bridge between AI agents and deterministic agents.

**Why this first:**
1. Enables structured data flow through the system
2. Makes external service integration cleaner and more reliable
3. Lays groundwork for knowledge management (structured = queryable)
4. Combines the strengths of AI reasoning with deterministic efficiency

---

## Long-term Vision

A unified knowledge hub where all project disciplines - designers, developers, PMs, product owners - contribute and collaborate through specialized agents.

```mermaid
graph TB
    subgraph "The Vision"
        K[(Unified<br/>Knowledge Hub)]

        subgraph "Contributors"
            DEV[Developers]
            DES[Designers]
            PM[Product Managers]
            PO[Product Owners]
        end

        subgraph "Their Agents"
            A1[Code Agents]
            A2[Design Agents]
            A3[Process Agents]
            A4[Domain Agents]
        end

        DEV --> A1
        DES --> A2
        PM --> A3
        PO --> A4

        A1 --> K
        A2 --> K
        A3 --> K
        A4 --> K
    end
```

**Characteristics:**
- Programmers build capabilities (MCP servers, skills)
- Domain experts describe agents and add requirements
- Knowledge base covers all dimensions of a project
- Accessible to everyone, not just programmers
- Agents collaborate, humans collaborate through agents

This is the north star - a long-term goal that guides decisions today.
