# Core Components and Architecture

## Diagram

```mermaid
graph TB
    subgraph "User Interfaces"
        UI1[Level 1:<br/>Slash Commands + Skills]
        UI2[Level 2:<br/>Subagent Delegation]
        UI3[Level 3:<br/>MCP Tools]
    end

    subgraph "Interface Layer"
        Plugin1[agent-orchestrator<br/>Claude Code Plugin]
        Plugin2[agent-orchestrator-subagents<br/>Claude Code Plugin]
        MCPServer[agent-orchestrator-mcp-server<br/>TypeScript MCP Server]
    end

    subgraph "Core Orchestration Engine"
        Script[agent-orchestrator.sh<br/>Bash Script - 1,203 lines]

        subgraph "Script Commands"
            CmdStart[start<br/>Create new session]
            CmdResume[resume<br/>Continue session]
            CmdList[list-agents<br/>Show available agents]
            CmdSessions[list-sessions<br/>Show sessions]
            CmdClean[clean<br/>Remove sessions]
        end

        Script --> CmdStart
        Script --> CmdResume
        Script --> CmdList
        Script --> CmdSessions
        Script --> CmdClean
    end

    subgraph "Claude Code Integration"
        CLI[Claude Code CLI]
        CLISession[Session Management]
        CLIMCP[MCP Configuration]

        CLI --> CLISession
        CLI --> CLIMCP
    end

    subgraph "Data Layer"
        Sessions[Session Storage<br/>.agent-orchestrator/sessions/]
        Agents[Agent Definitions<br/>.agent-orchestrator/agents/]

        subgraph "Session Files"
            JSONL[session-name.jsonl<br/>Conversation history]
            Meta[session-name.meta.json<br/>Agent association]
        end

        subgraph "Agent Files"
            AgentJSON[agent.json<br/>Configuration]
            AgentPrompt[agent.system-prompt.md<br/>Role definition]
            AgentMCP[agent.mcp.json<br/>MCP config]
        end

        Sessions --> JSONL
        Sessions --> Meta
        Agents --> AgentJSON
        Agents --> AgentPrompt
        Agents --> AgentMCP
    end

    UI1 --> Plugin1
    UI2 --> Plugin2
    UI3 --> MCPServer

    Plugin1 --> Script
    Plugin2 --> Plugin1
    MCPServer --> Script

    Script --> CLI

    CmdStart --> Sessions
    CmdResume --> Sessions
    CmdList --> Agents
    CmdSessions --> Sessions
    CmdClean --> Sessions

    CLI -.reads.-> Agents
    CLI -.stores.-> Sessions

    style Script fill:#BD10E0
    style CLI fill:#4A90E2
    style Sessions fill:#F5A623
    style Agents fill:#7ED321
    style Plugin1 fill:#E1F5FF
    style Plugin2 fill:#FFF4E1
    style MCPServer fill:#E8F5E1
```

## Architectural Aspects Covered

This diagram illustrates the **core component architecture** of the Agent Orchestrator Framework, showing:

### 1. **Layered Architecture**
The framework follows a clear separation of concerns:
- **User Interface Layer**: Three distinct entry points (slash commands, subagents, MCP tools)
- **Interface Layer**: Platform-specific implementations (plugins, MCP server)
- **Core Engine**: Single unified orchestration script
- **Integration Layer**: Claude Code CLI integration
- **Data Layer**: Persistent storage for sessions and agents

### 2. **Core Orchestration Engine**
The `agent-orchestrator.sh` script is the heart of the framework:
- **1,203 lines of bash**: Single source of truth for orchestration logic
- **Five main commands**: start, resume, list-agents, list-sessions, clean
- **Stateless design**: All state stored in data layer
- **CLI integration**: Manages Claude Code CLI invocations

### 3. **Command Responsibilities**
- **start**: Creates new agent sessions (generic or specialized)
- **resume**: Continues existing sessions with new prompts
- **list-agents**: Discovers available agent definitions
- **list-sessions**: Shows active and completed sessions
- **clean**: Removes all session data

### 4. **Data Persistence Model**

#### Session Storage
- **JSONL files**: Complete conversation history (Claude Code format)
- **Meta files**: Agent associations, timestamps, configuration

#### Agent Definitions
- **agent.json**: Required metadata (name, description)
- **agent.system-prompt.md**: Optional role definition
- **agent.mcp.json**: Optional MCP server configuration

### 5. **Integration Points**
- **Claude Code CLI**: Underlying execution engine for agents
- **MCP Configuration**: Per-agent tool access control
- **Session Management**: Conversation state and history
- **Result Extraction**: Automated parsing of agent outputs

### 6. **Unified Backend**
All three usage levels (direct plugin, subagents, MCP) converge on:
- Same orchestration script
- Same session storage format
- Same agent definition structure
- Same Claude Code CLI integration

This architecture ensures consistency across all usage modes while providing flexibility in how users interact with the framework.
