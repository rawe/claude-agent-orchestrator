# Post-Migration Fixes

Issues discovered and fixed after the Phase 4 migration was completed.

## Fix 1: Restore Hook Implementation

**Date:** 2025-11-26

**Problem:** Phase 4 removed SDK hooks entirely when migrating to direct API calls, causing:
- User message events (`message` with `role: "user"`) not captured
- Post tool events (`post_tool`) not captured

**Root Cause:** The migration plan (phase-4-event-flow.md) suggested removing hooks, but `post_tool` events require hooks as they're triggered by the SDK during tool execution.

**Solution:** Reimplemented hooks in `claude_client.py`:
1. Added module-level state for hook context (`_session_client`, `_current_session_id`, `_current_session_name`)
2. Added `_set_hook_context()` to share session client with hooks
3. Reimplemented `post_tool_hook` using `SessionClient.add_event()`
4. Registered `PostToolUse` hook with SDK via `HookMatcher`
5. Added user message event sending after session creation

**Files Changed:**
- `plugins/agent-orchestrator/skills/agent-orchestrator/commands/lib/claude_client.py`

**Verification:**
```bash
# Session with tool usage captures all events:
# - message (user)
# - post_tool (with tool_name, tool_input, tool_output)
# - message (assistant)
# - session_stop
curl http://localhost:8765/sessions/{id}/events
```

## Fix 2: Frontend WebSocket Missing session_created Handler

**Date:** 2025-11-26

**Problem:** New sessions created via `POST /sessions` API don't appear in real-time in the unified frontend. Users must switch tabs or refresh to see new sessions.

**Root Cause:** Phase 4 changed session creation from:
- **Before:** `POST /events` with `event_type: "session_start"` → broadcasts `{"type": "event", "data": {...}}`
- **After:** `POST /sessions` → broadcasts `{"type": "session_created", "session": {...}}`

The frontend `WebSocketMessage` type and `useSessions` hook only handled `init`, `event`, `session_updated`, and `session_deleted` - not the new `session_created` message type.

**Solution:**
1. Added `session_created` to `WebSocketMessage` type union in `types/event.ts`
2. Added handler for `session_created` in `useSessions.ts` that adds new sessions to state

**Files Changed:**
- `agent-orchestrator-frontend/src/types/event.ts`
- `agent-orchestrator-frontend/src/hooks/useSessions.ts`

**Verification:**
```bash
# Start a new agent session and verify it appears in frontend without refresh
ao-new math-test -p "Calculate 2+2"
# Session should appear immediately in the frontend session list
```
