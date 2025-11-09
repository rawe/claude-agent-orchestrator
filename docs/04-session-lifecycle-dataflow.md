# Agent Session Lifecycle and Data Flow

## Diagram

```mermaid
stateDiagram-v2
    [*] --> SessionRequest: User initiates<br/>(start command)

    state "Session Request" as SessionRequest {
        [*] --> ValidateName: Check session name
        ValidateName --> CheckExisting: Name valid
        CheckExisting --> LoadAgent: Session doesn't exist
        LoadAgent --> PreparePrompt: Agent loaded (optional)
        PreparePrompt --> [*]: Request ready
    }

    SessionRequest --> SessionCreation

    state "Session Creation" as SessionCreation {
        [*] --> CreateDirectory: Make session folder
        CreateDirectory --> InitMetadata: Create meta.json
        InitMetadata --> PrepareSystemPrompt: Associate agent
        PrepareSystemPrompt --> PrepareMCPConfig: Load agent.system-prompt.md
        PrepareMCPConfig --> InvokeCLI: Load agent.mcp.json
        InvokeCLI --> [*]: Claude CLI launched
    }

    SessionCreation --> Initializing

    state "Initializing" as Initializing {
        note right of Initializing
            Session starting up
            Waiting for Claude CLI
            to establish connection
        end note
    }

    Initializing --> Active: Session ID received

    state "Active Execution" as Active {
        [*] --> ProcessingPrompt: Claude processes
        ProcessingPrompt --> GeneratingResponse: Agent thinking
        GeneratingResponse --> ExecutingTools: Using MCP tools (optional)
        ExecutingTools --> WritingResult: Task complete
        WritingResult --> [*]: Response ready
    }

    Active --> ResultExtraction

    state "Result Extraction" as ResultExtraction {
        [*] --> ReadJSONL: Parse session JSONL
        ReadJSONL --> ExtractMessages: Get conversation
        ExtractMessages --> FormatOutput: Clean formatting
        FormatOutput --> StoreResult: Save to meta
        StoreResult --> [*]: Result ready
    }

    ResultExtraction --> Completed: Task finished

    state "Completed" as Completed {
        note right of Completed
            Session in completed state
            Can be resumed with
            new prompts or archived
        end note
    }

    Completed --> Resume: User resumes<br/>(resume command)

    state "Resume Session" as Resume {
        [*] --> LoadSession: Read existing JSONL
        LoadSession --> LoadAssociatedAgent: Get conversation history
        LoadAssociatedAgent --> AppendPrompt: Load agent config
        AppendPrompt --> ReInvokeCLI: Add new prompt
        ReInvokeCLI --> [*]: Continue conversation
    }

    Resume --> Active

    Completed --> [*]: clean command<br/>deletes session

    state ErrorHandling <<choice>>
    SessionRequest --> ErrorHandling: Validation fails
    SessionCreation --> ErrorHandling: Creation fails
    Active --> ErrorHandling: Execution fails
    ErrorHandling --> [*]: Error reported to user
```

## Architectural Aspects Covered

This diagram illustrates the **session lifecycle and data flow** through the Agent Orchestrator Framework, showing:

### 1. **Session States**
- **Session Request**: Initial validation and preparation phase
- **Session Creation**: Setting up directory structure and configuration
- **Initializing**: Waiting for Claude CLI to establish session
- **Active Execution**: Agent processing the prompt and generating responses
- **Result Extraction**: Parsing and formatting agent output
- **Completed**: Terminal state, ready for resume or cleanup

### 2. **State Transitions**

#### Creating New Sessions
1. User initiates with `start` command
2. Validate session name (alphanumeric, dash, underscore; max 60 chars)
3. Check if session already exists (prevent duplicates)
4. Load agent definition (if specified)
5. Prepare system prompt and MCP configuration
6. Invoke Claude CLI with prepared configuration
7. Wait for session initialization
8. Process task to completion
9. Extract and store results

#### Resuming Existing Sessions
1. User initiates with `resume` command
2. Load existing session JSONL file
3. Load associated agent configuration
4. Append new prompt to conversation history
5. Re-invoke Claude CLI with continuation
6. Return to Active Execution state

### 3. **Data Flow at Each Stage**

#### Session Request
- **Input**: User prompt, session name, optional agent name
- **Processing**: Name validation, existence check, agent lookup
- **Output**: Validated request ready for creation

#### Session Creation
- **Input**: Validated request
- **Processing**: Directory creation, metadata initialization, agent configuration loading
- **Output**: Session environment ready for CLI invocation

#### Active Execution
- **Input**: System prompt + user prompt, MCP configuration
- **Processing**: Claude processes task, executes tools, generates response
- **Output**: Completed task result in JSONL format

#### Result Extraction
- **Input**: Session JSONL file
- **Processing**: Parse conversation, extract final messages, format output
- **Output**: Clean result stored in metadata, returned to user

### 4. **Agent Integration Points**
- **System Prompt**: Loaded from `agent.system-prompt.md` and prepended to user prompt
- **MCP Configuration**: Passed to Claude CLI via `--mcp-config` flag
- **Agent Association**: Stored in `meta.json` for resume operations
- **Conversation Context**: Maintained across multiple resume cycles

### 5. **Error Handling**
The framework handles errors at multiple points:
- Session name validation failures
- Non-existent session on resume
- Agent definition not found
- CLI execution failures
- JSONL parsing errors

All errors are reported clearly to the user with actionable messages.

### 6. **Persistence Strategy**
- **JSONL files**: Full conversation history in Claude Code format
- **Meta files**: Session metadata, agent associations, timestamps
- **Stateless script**: All state externalized to file system
- **Resume capability**: Complete conversation context preserved

This lifecycle design enables long-running tasks, iterative refinement, and stateful conversations while maintaining a simple, file-based persistence model.
