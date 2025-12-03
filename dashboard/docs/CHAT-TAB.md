# Chat Tab

The Chat tab provides a live chat interface for interacting with AI agents using the Agent Orchestration Framework.

## Architecture

```
┌─────────────────┐     REST API      ┌──────────────────────┐
│                 │ ───────────────►  │  Agent Orchestrator  │
│    Chat Tab     │   start/resume    │     API Server       │
│                 │                   │   (port 9500)        │
└─────────────────┘                   └──────────────────────┘
         │                                      │
         │                                      │
         ▼                                      │
┌─────────────────┐                             │
│  ChatContext    │ ◄───────────────────────────┘
│  (App level)    │       WebSocket
│                 │    (message events)
└─────────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `src/contexts/ChatContext.tsx` | Global chat state and WebSocket message handling |
| `src/pages/Chat.tsx` | Chat UI component |
| `src/services/chatService.ts` | API client for Agent Orchestrator |
| `src/services/api.ts` | Axios instance (`agentOrchestratorApi`) |
| `src/utils/constants.ts` | `AGENT_ORCHESTRATOR_URL` (default: `http://localhost:9500`) |

## API Usage

The Chat tab uses the **Agent Orchestrator REST API** for two operations only:

### 1. List Blueprints
```
GET /api/blueprints
```
Fetches available agent blueprints for the dropdown selector. A refresh button allows reloading the list.

### 2. Start Session
```
POST /api/sessions
{
  "session_name": "chat-1234567890-abc123",
  "prompt": "user message",
  "agent_blueprint_name": "web-researcher",  // optional
  "async_mode": true
}
```
Creates a new agent session. Always uses `async_mode: true`.

### 3. Resume Session
```
POST /api/sessions/{session_name}/resume
{
  "prompt": "follow-up message",
  "async_mode": true
}
```
Continues an existing session with a new prompt.

## WebSocket Integration

The Chat tab reuses the **existing WebSocket connection** from the dashboard. The WebSocket subscription is managed in `ChatContext` at the App level, ensuring messages are received even when navigating to other tabs.

### Event Flow

1. **Capture session_id**: Listen for `session_created` or `session_updated` events matching our `session_name`
2. **Receive response**: Listen for `event` messages where:
   - `data.event_type === 'message'`
   - `data.role === 'assistant'`
   - `data.session_id` matches our session
3. **Extract content**: Get text from `data.content[].text`

### WebSocket Message Types Used

```typescript
// Capture session_id
{ type: 'session_created', session: { session_id, session_name, status } }
{ type: 'session_updated', session: { session_id, session_name, status } }

// Receive agent response
{ type: 'event', data: {
    session_id,
    event_type: 'message',
    role: 'assistant',
    content: [{ type: 'text', text: '...' }]
  }
}
```

## State Management

### ChatContext (App Level)

Chat state is managed in `ChatContext` which is mounted at the App level. This provides:

- **Tab navigation persistence**: Chat state persists when switching between dashboard tabs
- **Background message handling**: WebSocket messages are processed even when on other tabs
- **Refs for callbacks**: Uses refs to avoid stale closures in WebSocket handlers

### What IS Persisted (in memory)
- Chat messages displayed in the UI
- Current session name and ID
- Selected agent blueprint
- Agent status

### What is NOT Persisted (across page refresh)
- Chat UI state is stored in React state only
- Refreshing the page clears the chat UI
- The `session_name` is lost on refresh (no localStorage)

### Session Naming
Sessions are auto-generated with the pattern:
```
chat-{timestamp}-{random}
Example: chat-1733263200000-x7k9m2
```

## Features

- **Agent Selection**: Dropdown to choose agent blueprint (or "Generic Agent") with refresh button
- **Connection Status**: Shows WebSocket connected/disconnected state
- **New Chat**: Clears UI and starts fresh session
- **Markdown Rendering**: Agent responses rendered with ReactMarkdown
- **Auto-scroll**: Messages area scrolls to bottom on new messages
- **Tab Persistence**: Chat state maintained when navigating between tabs

## Configuration

Set the Agent Orchestrator URL via environment variable:
```bash
VITE_AGENT_ORCHESTRATOR_URL=http://localhost:9500
```

Or it defaults to `http://localhost:9500`.
