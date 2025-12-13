# Frontend Session Sync Refactor

**Date:** 2025-12-13
**Scope:** Dashboard frontend - WebSocket synchronization and session state management

## Problem Statement

The user reported several issues with the dashboard:

1. **Stop button not working from Chat tab** - When trying to stop a session from the Chat tab, the backend always returned "session is already finished" even though the UI showed the session as running.

2. **Sessions tab not updating in real-time** - When starting or resuming a session in the Chat tab, the Sessions tab didn't reflect the status changes until a manual refresh.

3. **User messages disappearing on resume** - When resuming a session by sending a new message, the user's message would initially appear but then disappear when "agent is running" was shown.

4. **Message ordering issues** - Resume messages were being placed at the wrong position in the chat history.

5. **System prompt showing in first message** - The first user message was displaying the full system prompt instead of just the user's input.

## Root Cause Analysis

### Issue 1 & 2: No Shared Sessions State

The `useSessions` hook was implemented as a regular React hook, not a context. This meant:

- Each page (Chat, Sessions) had its **own separate instance** of the sessions state
- When on the Chat tab, the Sessions page was not mounted, so its WebSocket listener was not active
- Status updates were not shared between tabs

### Issue 1: Event Handler Matching

The WebSocket event handler in `ChatContext` only matched events by `sessionId` or `linkedSessionId`, but **not by `sessionName`**. For new chats where `sessionId` hasn't been captured yet, events were being silently dropped.

### Issue 3, 4, 5: Callback Resume Block

The `session_start` event handler had a "callback resume" block that would:
- Fetch all messages from the backend
- **Replace** all local messages with backend messages

This caused:
- User messages (added locally) to be lost when backend messages didn't include them yet
- Messages with system prompts (from backend) to overwrite clean local messages
- Message ordering to change during the merge process

### Race Conditions with Refs

Several React refs (`agentStatusRef`, `isLoadingRef`) were being updated via `useEffect` (async) instead of synchronously. This created race conditions where WebSocket events would read stale ref values.

## Changes Made

### New File: `dashboard/src/contexts/SessionsContext.tsx`

Created a new React context for global sessions state that:
- Lives at the App level (always mounted)
- Subscribes to WebSocket for session updates
- Provides shared state to all components
- Exports `SessionsProvider` and `useSessions`

### Modified: `dashboard/src/App.tsx`

- Added `SessionsProvider` to the provider hierarchy
- Order: `NotificationProvider` → `WebSocketProvider` → `SessionsProvider` → `ChatProvider`

### Modified: `dashboard/src/contexts/index.ts`

- Added exports for `SessionsProvider` and `useSessions`

### Modified: `dashboard/src/hooks/useSessions.ts`

- Removed `useSessions` function (now in context)
- Kept only `useSessionEvents` for session-specific event subscriptions

### Modified: `dashboard/src/hooks/index.ts`

- Removed `useSessions` export (now from contexts)

### Modified: `dashboard/src/pages/Chat.tsx`

- Updated import to use `useSessions` from `@/contexts` instead of `@/hooks`

### Modified: `dashboard/src/pages/AgentSessions.tsx`

- Updated import to use `useSessions` from `@/contexts` instead of `@/hooks`

### Modified: `dashboard/src/contexts/ChatContext.tsx`

1. **Synchronous ref updates**: Created wrapper functions for `setAgentStatus` and `setIsLoading` that update both state and ref synchronously (like `setPendingMessageId` already did)

2. **Event handler matching**: Added `sessionName` matching to the event handler, so events can be matched even before `sessionId` is captured

3. **Session stop handler**: Changed to always update `agentStatus` to 'finished' when session stops, regardless of whether there's a pending message

4. **Callback resume block**: Simplified to check the actual messages state (not just refs) for pending messages, and only replace messages for true callback resumes (no user action in progress)

### Modified: `dashboard/src/types/event.ts`

- Added `session_name?: string` to the `SessionEvent` interface to support matching by session name

## Architecture After Changes

```
App.tsx
├── NotificationProvider
├── WebSocketProvider
├── SessionsProvider     ← NEW: Global sessions state, always listening
├── ChatProvider
└── RouterProvider
    ├── /chat → uses useSessions() from context (shared state)
    └── /sessions → uses useSessions() from context (same state)
```

## Result

- Sessions tab now updates in real-time regardless of which tab is active
- Stop button works correctly from the Chat tab
- User messages are preserved when resuming sessions
- Message ordering is maintained
- Local user input is not replaced with backend messages containing system prompts
