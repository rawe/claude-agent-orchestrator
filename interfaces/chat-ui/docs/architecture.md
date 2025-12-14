# Architecture

## Project Structure

```
src/
├── components/       # React components
├── contexts/         # React contexts (state management)
├── services/         # API clients
├── config/           # Environment configuration
├── types/            # TypeScript types
└── App.tsx           # Root component
```

## Component Hierarchy

```
App
└── WebSocketProvider      # WebSocket connection
    └── ChatProvider       # Chat state management
        └── Chat           # Main UI
            ├── Header     # Title, status, new chat button
            ├── Messages   # Message list or empty state
            │   └── ChatMessage
            │       ├── ToolCallBadge
            │       └── Markdown content
            └── ChatInput  # Input field + send/stop
```

## Data Flow

```
User Input → ChatContext.sendMessage() → API (POST /jobs)
                                              ↓
WebSocket ← Agent Runtime broadcasts events
    ↓
ChatContext handles event → Updates state → UI re-renders
```

## State Management

**ChatContext** manages:
- `messages[]` - Chat messages
- `sessionName/sessionId` - Current session
- `agentStatus` - idle/starting/running/finished/error
- `currentToolCalls[]` - Tools in progress
- `pendingMessageId` - Message awaiting response

**WebSocketContext** manages:
- Connection state
- Subscriber pattern for message handling
- Auto-reconnect with exponential backoff
