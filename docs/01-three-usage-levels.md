# Three Usage Levels of Agent Orchestrator Framework

## Diagram

```mermaid
graph TB
    subgraph "Level 1: Core Framework Plugin"
        L1[Claude Code Plugin<br/>agent-orchestrator]
        L1Skills[Skills & Slash Commands]
        L1Script[agent-orchestrator.sh<br/>1,203 lines]

        L1 --> L1Skills
        L1Skills --> L1Script
    end

    subgraph "Level 2: Subagents Extension"
        L2[Claude Code Plugin<br/>agent-orchestrator-subagents]
        L2Agents[Pre-configured Subagents]
        L2Delegation[Natural Language<br/>Delegation Interface]

        L2 --> L2Agents
        L2Agents --> L2Delegation
        L2Delegation -.requires.-> L1
    end

    subgraph "Level 3: MCP Server Protocol"
        L3[MCP Server<br/>TypeScript Implementation]
        L3Tools[5 MCP Tools]
        L3Protocol[Model Context Protocol]

        L3 --> L3Tools
        L3Tools --> L3Protocol
        L3 -.uses.-> L1Script
    end

    subgraph "Core Foundation"
        CoreScript[agent-orchestrator.sh]
        CoreSessions[Session Management]
        CoreAgents[Agent Definitions]

        CoreScript --> CoreSessions
        CoreScript --> CoreAgents
    end

    L1Script -.implements.-> CoreScript
    L3 -.invokes.-> CoreScript

    User1[User: Direct Control] --> L1
    User2[User: Simplified Workflow] --> L2
    User3[User: Any MCP Client] --> L3

    style L1 fill:#e1f5ff
    style L2 fill:#fff4e1
    style L3 fill:#e8f5e1
    style CoreScript fill:#ffe1f5
```

## Architectural Aspects Covered

This diagram illustrates the **three-tier usage model** of the Agent Orchestrator Framework (AOF), showing:

### 1. **Progressive Enhancement Architecture**
- **Level 1**: Direct, low-level control through Claude Code plugin with skills and slash commands
- **Level 2**: Higher-level abstraction with pre-configured subagents for delegation-based workflows
- **Level 3**: Protocol-level abstraction enabling any MCP-compatible system to orchestrate agents

### 2. **Dependency Relationships**
- Level 2 **requires** Level 1 (both must be installed as Claude Code plugins)
- Level 3 is **independent** and directly invokes the core script
- All levels share the same foundational `agent-orchestrator.sh` script

### 3. **User Interaction Models**
- **Level 1**: Command-line style with slash commands (`/agent-orchestrator-init`)
- **Level 2**: Natural language delegation ("Use the orchestrated-agent-launcher subagent...")
- **Level 3**: MCP tools accessible from any compatible client (Claude Desktop, Claude Code, etc.)

### 4. **Integration Scope**
- **Levels 1 & 2**: Claude Code only
- **Level 3**: Any MCP-compatible AI system (Claude Desktop, other tools)

### 5. **Core Foundation**
The `agent-orchestrator.sh` bash script (1,203 lines) is the single source of truth for:
- Session lifecycle management
- Agent definition handling
- MCP configuration injection
- Result extraction and formatting

This architecture enables users to choose the integration approach that best fits their needs while maintaining a unified core implementation.
