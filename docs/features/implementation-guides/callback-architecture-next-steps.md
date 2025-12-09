# Callback Architecture - Next Steps

## Context

This document outlines the remaining work needed to complete the Agent Callback Architecture feature. The core callback flow has been implemented and tested (see `callback-flow-test-plan.md`), but there are frontend enhancements and a critical bug that need attention.

### Related Documentation
- [MCP Server API Refactor](./mcp-server-api-refactor.md) - Architecture and implementation details
- [Implementation Report](./mcp-server-api-refactor-report.md) - Phase completion status
- [Known Bugs](./mcp-server-api-refactor-bugs.md) - Bug tracking
- [Callback Flow Test Plan](./callback-flow-test-plan.md) - Testing procedures

---

## Task 1: Chat Window Does Not React to Callback Resume (BUG) - RESOLVED

### Problem
The callback architecture works correctly in the **Sessions tab** - when a child session completes and triggers a callback, the parent session is automatically resumed and the UI updates properly.

However, in the **Chat tab**, the parent session did NOT react to the callback. After the child session returns and the parent is resumed, the Chat window stopped and did not show any updates.

### Root Causes Identified

1. **Stale Closure**: The `agentStatus` variable was read directly in the `handleWebSocketMessage` callback, but since the callback had an empty dependency array `[]`, it captured the initial value and never updated.

2. **Wrong Signal**: The original code tried to detect callback resume via `session_updated` status changes, but the backend doesn't change the session status back to `running` on callback resume. Instead, a `session_start` event is emitted (same mechanism used by the Sessions tab).

3. **Session Matching**: The original code only matched sessions by `session_name`, missing matches by `session_id` or `linkedSessionId`.

### Solution Implemented

1. **Added `agentStatusRef`**: Uses a ref to track agent status, keeping it in sync with state via `useEffect`. This ensures the WebSocket callback always has the current value.

2. **Listen for `session_start` events**: Added handler for `event_type === 'session_start'` to detect when a callback resumes the session (same approach as Sessions tab in `useSessions.ts`).

3. **Improved session matching**: Now matches sessions by `session_id`, `linkedSessionId`, or `session_name`.

4. **Fetch and display messages**: When callback resume is detected:
   - Fetches all session events from the API
   - Converts events to chat messages (includes user message that triggered callback)
   - Adds a pending message indicator for the assistant response
   - Displays the assistant response when it arrives

### Files Changed
- `dashboard/src/contexts/ChatContext.tsx` - Main fix
- `dashboard/docs/CHAT-TAB.md` - Documentation updated with callback feature details

### Acceptance Criteria
- [x] Chat tab reacts to callback resume (parent session continues after child returns)
- [x] Pending message indicator shows when parent is resumed via callback
- [x] Agent response from callback resume is displayed in Chat tab

---

## Task 2: Display Parent Session in Dashboard

### Problem
The dashboard does not currently display the `parent_session_name` field for sessions. When a child session is created with `callback=true`, users cannot see which parent session triggered it.

### Current State
- **Backend**: The `parent_session_name` field exists in the database and is returned by the API
  - Database schema: `servers/agent-runtime/database.py:22`
  - API returns all session fields via `get_sessions()`: `servers/agent-runtime/database.py:148-158`
- **Frontend**: The `Session` type does not include `parent_session_name`
  - Type definition: `dashboard/src/types/session.ts:3-11`
  - Session card display: `dashboard/src/components/features/sessions/SessionCard.tsx`

### Required Changes

1. **Update Session Type** (`dashboard/src/types/session.ts`)
   ```typescript
   export interface Session {
     session_id: string;
     session_name?: string;
     status: SessionStatus;
     created_at: string;
     modified_at?: string;
     project_dir?: string;
     agent_name?: string;
     parent_session_name?: string;  // ADD THIS
   }
   ```

2. **Update SessionCard Component** (`dashboard/src/components/features/sessions/SessionCard.tsx`)
   - Add a "Parent Session" row similar to how `agent_name` is displayed
   - Use a suitable icon (e.g., `GitBranch` or `Link` from lucide-react)
   - Display format: Show parent session name with a link/click to navigate to parent

### Acceptance Criteria
- [ ] `parent_session_name` field visible in session card when present
- [ ] Label must say "Parent Session" (not "parent_session_name")
- [ ] Clicking parent session name navigates to/highlights that session

---

## Task 3: Cleanup Bug Documentation

### Problem
Bug 2 in `mcp-server-api-refactor-bugs.md` documents a missing `callback` parameter in the REST API. This should be verified and either:
- Fixed if still relevant
- Marked as resolved/won't-fix if not needed

### File Reference
`docs/features/implementation-guides/mcp-server-api-refactor-bugs.md:35-52`

---

## Priority Order

1. **Critical**: Task 1 (Chat Tab Callback Bug) - Core functionality broken
2. **High**: Task 2 (Parent Session Display) - Essential for callback visibility
3. **Low**: Task 3 (Bug Cleanup) - Documentation hygiene

---

## Notes

- All frontend changes are in `dashboard/src/`
- Backend API is in `servers/agent-runtime/`
- MCP server is in `interfaces/agent-orchestrator-mcp-server/`
