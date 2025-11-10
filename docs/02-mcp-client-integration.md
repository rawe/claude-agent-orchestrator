# Level 3: MCP Client Integration

## Diagram

```mermaid
graph TB
    subgraph "MCP Compatible Clients"
        CD[Claude Desktop<br/>Desktop Application]
        CC[Claude Code CLI<br/>Command Line]
        Other[Other MCP Clients<br/>Future Compatible Tools]
    end

    subgraph "MCP Server Layer"
        MCP[Agent Orchestrator<br/>MCP Server<br/>TypeScript]
        Tools[5 MCP Tools]

        MCP --> Tools
    end

    subgraph "MCP Tools Available"
        T1[list_agents<br/>Discover agent definitions]
        T2[list_sessions<br/>View active sessions]
        T3[start_agent<br/>Create new session]
        T4[resume_agent<br/>Continue session]
        T5[clean_sessions<br/>Remove sessions]
    end

    subgraph "Configuration Layer"
        CDConfig[claude_desktop_config.json<br/>Desktop Config]
        CCConfig[.mcp.json +<br/>settings.local.json<br/>Claude Code Config]

        CDEnv[Environment Variables:<br/>PATH, SCRIPT_PATH,<br/>PROJECT_DIR]
        CCEnv[Environment Variables:<br/>SCRIPT_PATH<br/>PROJECT_DIR optional]
    end

    subgraph "Core Orchestration"
        Script[agent-orchestrator.sh<br/>Bash Script]
        Sessions[.agent-orchestrator/<br/>agent-sessions/]
        Agents[.agent-orchestrator/<br/>agents/]
    end

    CD --> CDConfig
    CC --> CCConfig
    Other -.-> MCP

    CDConfig --> CDEnv
    CCConfig --> CCEnv

    CDEnv --> MCP
    CCEnv --> MCP

    Tools --> T1
    Tools --> T2
    Tools --> T3
    Tools --> T4
    Tools --> T5

    T1 --> Script
    T2 --> Script
    T3 --> Script
    T4 --> Script
    T5 --> Script

    Script --> Sessions
    Script --> Agents

    style CD fill:#4A90E2
    style CC fill:#7ED321
    style Other fill:#D0D0D0
    style MCP fill:#F5A623
    style Script fill:#BD10E0
    style T1 fill:#E1F5FF
    style T2 fill:#E1F5FF
    style T3 fill:#E1F5FF
    style T4 fill:#E1F5FF
    style T5 fill:#E1F5FF
```

## Architectural Aspects Covered

This diagram illustrates the **MCP client integration model** for Level 3 usage, showing:

### 1. **Multiple Client Support**
The MCP server provides a universal interface accessible from:
- **Claude Desktop**: Desktop application with GUI
- **Claude Code CLI**: Command-line interface
- **Future MCP Clients**: Any tool implementing the Model Context Protocol

### 2. **Client-Specific Configuration**

#### Claude Desktop
- Configuration file: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
- **Required**: `PATH` environment variable (UI apps don't inherit shell PATH)
- **Required**: `AGENT_ORCHESTRATOR_SCRIPT_PATH`
- **Required**: `AGENT_ORCHESTRATOR_PROJECT_DIR`

#### Claude Code
- Configuration files: `.mcp.json` (committable) + `.claude/settings.local.json` (local)
- **Required**: `AGENT_ORCHESTRATOR_SCRIPT_PATH`
- **Optional**: `AGENT_ORCHESTRATOR_PROJECT_DIR` (defaults to current directory)

### 3. **Unified MCP Tools Interface**
Regardless of client, all get access to the same 5 tools:
1. **list_agents**: Discover available specialized agent definitions
2. **list_sessions**: View all agent sessions and their IDs
3. **start_agent**: Create new agent sessions (generic or specialized)
4. **resume_agent**: Continue work in existing sessions
5. **clean_sessions**: Remove all sessions

### 4. **Protocol Abstraction Benefits**
- **No plugin installation required**: Level 3 doesn't need Claude Code plugins
- **Standardized interface**: MCP provides consistent tool access across clients
- **Client independence**: Same backend works with any MCP-compatible client
- **Type safety**: TypeScript implementation with Zod validation

### 5. **Shared Core Foundation**
All clients, regardless of type, ultimately invoke the same:
- `agent-orchestrator.sh` bash script for orchestration logic
- `.agent-orchestrator/agent-sessions/` for session persistence
- `.agent-orchestrator/agents/` for agent definitions

This architecture enables the Agent Orchestrator Framework to work with any MCP-compatible AI system while maintaining a single, consistent implementation.
