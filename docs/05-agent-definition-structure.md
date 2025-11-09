# Agent Definition Structure

## Diagram

```mermaid
graph TB
    subgraph "Agent Directory Structure"
        AgentDir[".agent-orchestrator/agents/<br/>&lt;agent-name&gt;/"]

        subgraph "Required Files"
            JSON[agent.json<br/>Configuration Metadata]
        end

        subgraph "Optional Files<br/>(Discovered by Convention)"
            Prompt[agent.system-prompt.md<br/>Role Definition]
            MCP[agent.mcp.json<br/>MCP Server Configuration]
        end

        AgentDir --> JSON
        AgentDir --> Prompt
        AgentDir --> MCP
    end

    subgraph "agent.json Schema"
        JSONSchema["<b>agent.json</b><br/>{<br/>  'name': 'agent-name',<br/>  'description': 'Agent purpose'<br/>}"]

        JSONName["name: string<br/>(must match directory)"]
        JSONDesc["description: string<br/>(human-readable)"]

        JSONSchema --> JSONName
        JSONSchema --> JSONDesc
    end

    subgraph "agent.system-prompt.md"
        PromptContent[Markdown Content]

        subgraph "Typical Sections"
            Role[# Role Definition<br/>Agent's expertise and purpose]
            Expertise[# Expertise Areas<br/>Specialized knowledge]
            Guidelines[# Behavioral Guidelines<br/>How to approach tasks]
            Constraints[# Constraints<br/>What to avoid]
        end

        PromptContent --> Role
        PromptContent --> Expertise
        PromptContent --> Guidelines
        PromptContent --> Constraints
    end

    subgraph "agent.mcp.json Schema"
        MCPSchema["<b>agent.mcp.json</b><br/>{<br/>  'mcpServers': {<br/>    'server-name': {<br/>      'command': '...',<br/>      'args': [...],<br/>      'env': {...}<br/>    }<br/>  }<br/>}"]

        MCPServers[mcpServers: object<br/>Server definitions]
        MCPCommand[command: string<br/>Executable path]
        MCPArgs[args: array<br/>Command arguments]
        MCPEnv[env: object<br/>Environment variables]

        MCPSchema --> MCPServers
        MCPServers --> MCPCommand
        MCPServers --> MCPArgs
        MCPServers --> MCPEnv
    end

    subgraph "Agent Loading Process"
        Load1[1. Read agent.json<br/>Validate required fields]
        Load2[2. Check for system-prompt.md<br/>Load if present]
        Load3[3. Check for mcp.json<br/>Load if present]
        Load4[4. Prepare configuration<br/>for session creation]

        Load1 --> Load2
        Load2 --> Load3
        Load3 --> Load4
    end

    JSON --> JSONSchema
    Prompt --> PromptContent
    MCP --> MCPSchema

    JSONSchema --> Load1
    PromptContent -.optional.-> Load2
    MCPSchema -.optional.-> Load3

    subgraph "Usage in Sessions"
        Session[Session Creation]
        PrepPrompt[Prepend system prompt<br/>to user's prompt]
        PassMCP[Pass MCP config<br/>to Claude CLI --mcp-config]
        StoreMeta[Store agent association<br/>in session meta.json]

        Load4 --> Session
        Session --> PrepPrompt
        Session --> PassMCP
        Session --> StoreMeta
    end

    style JSON fill:#FF6B6B
    style Prompt fill:#4ECDC4
    style MCP fill:#95E1D3
    style AgentDir fill:#F3A683
```

## Architectural Aspects Covered

This diagram illustrates the **agent definition structure and composition** in the Agent Orchestrator Framework, showing:

### 1. **File Organization**
Agents are organized in a directory-per-agent structure:
```
.agent-orchestrator/agents/
├── system-architect/
│   ├── agent.json                 # Required
│   ├── agent.system-prompt.md     # Optional
│   └── agent.mcp.json             # Optional
├── code-reviewer/
│   ├── agent.json
│   ├── agent.system-prompt.md
│   └── agent.mcp.json
└── documentation-writer/
    └── agent.json
```

### 2. **Required Configuration (agent.json)**
Every agent must have an `agent.json` file containing:
- **name**: Agent identifier (must match the directory name)
- **description**: Human-readable description of the agent's purpose

Example:
```json
{
  "name": "browser-tester",
  "description": "Specialist in browser automation and end-to-end testing using Playwright"
}
```

### 3. **Optional System Prompt (agent.system-prompt.md)**
Discovered by convention (no need to reference in agent.json):
- **Markdown format**: Natural language role definition
- **Prepended to prompts**: Automatically added before user's prompt
- **Typical sections**:
  - Role definition and expertise
  - Specialized knowledge areas
  - Behavioral guidelines
  - Constraints and limitations

Example:
```markdown
# Role Definition
You are a system architecture expert specializing in designing scalable, maintainable software systems.

# Expertise Areas
- Microservices architecture
- Distributed systems design
- Cloud-native applications
- API design and integration patterns
```

### 4. **Optional MCP Configuration (agent.mcp.json)**
Discovered by convention (no need to reference in agent.json):
- **Standard MCP format**: Same as Claude Desktop/Code MCP configuration
- **Passed to Claude CLI**: Via `--mcp-config` flag
- **Enables tool access**: Specialized capabilities per agent type

Example:
```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-playwright"],
      "env": {}
    }
  }
}
```

### 5. **Convention-Based Discovery**
The framework uses **convention over configuration**:
- **No explicit file references**: Files discovered by standardized naming
- **Optional components**: System prompt and MCP config are opt-in
- **Fail gracefully**: Missing optional files don't cause errors
- **Consistent naming**: Predictable structure across all agents

### 6. **Agent Loading Process**
When a session uses an agent:
1. **Load agent.json**: Validate required metadata
2. **Check for system-prompt.md**: Load if present
3. **Check for mcp.json**: Load if present
4. **Prepare configuration**: Combine all components
5. **Create session**: Apply configuration to new session

### 7. **Integration with Sessions**
Agent configuration affects session behavior:
- **System Prompt**: Prepended to every prompt (first use and resumes)
- **MCP Configuration**: Enables specialized tools and capabilities
- **Agent Association**: Stored in session metadata for resume operations
- **Conversation Context**: Agent identity maintained across session lifecycle

### 8. **Separation of Concerns**
- **Agent**: Reusable blueprint defining behavior and capabilities
- **Session**: Specific conversation instance using an agent
- One agent can spawn multiple sessions
- Sessions remember their agent association

### 9. **Flexibility**
The structure supports various use cases:
- **Minimal agents**: Just `agent.json` for generic specialized sessions
- **Prompted agents**: Add `system-prompt.md` for role-based behavior
- **Tool-enabled agents**: Add `mcp.json` for specialized capabilities
- **Full-featured agents**: All three files for comprehensive specialization

This design enables creating a library of reusable, specialized agents while keeping the configuration simple and maintainable.
