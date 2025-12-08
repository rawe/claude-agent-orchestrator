# Callback Architecture - Next Steps

## Context

This document outlines the remaining work needed to complete the Agent Callback Architecture feature. The core callback flow has been implemented and tested (see `callback-flow-test-plan.md`), but there are frontend enhancements and a critical bug that need attention.

### Related Documentation
- [MCP Server API Refactor](./mcp-server-api-refactor.md) - Architecture and implementation details
- [Implementation Report](./mcp-server-api-refactor-report.md) - Phase completion status
- [Known Bugs](./mcp-server-api-refactor-bugs.md) - Bug tracking
- [Callback Flow Test Plan](./callback-flow-test-plan.md) - Testing procedures

---

## Task 1: Chat Window Does Not React to Callback Resume (BUG)

### Problem
The callback architecture works correctly in the **Sessions tab** - when a child session completes and triggers a callback, the parent session is automatically resumed and the UI updates properly.

However, in the **Chat tab**, the parent session does NOT react to the callback. After the child session returns and the parent is resumed, the Chat window stops and does not show any updates. It appears the Chat tab is not properly handling the WebSocket events for callback-triggered session resumes.

### Current State
- **Sessions tab**: Works correctly - parent resumes automatically via callback
- **Chat tab**: Does NOT work - stops after child session returns, no reaction to resume

### Investigation Areas

The issue is likely in the Chat tab's WebSocket event handling:

1. **ChatContext.tsx** (`dashboard/src/contexts/ChatContext.tsx`)
   - Lines 272-417: `handleWebSocketMessage` callback handles WebSocket events
   - Lines 279-316: Handles `session_created` and `session_updated` events
   - Lines 291-312: Logic to detect callback resume (when `wasFinished` and session becomes `running` again)

   **Potential issues:**
   - The `agentStatus` check at line 291 might not be correct - it reads from state but might be stale
   - The condition at line 297 checks `!currentPendingMessageId` but this might not be the right check
   - The session matching at line 280 only checks `session_name`, but callback resumes might have different identifiers

2. **Possible root causes:**
   - Session name mismatch between parent and callback context
   - `agentStatus` state is stale when WebSocket callback fires
   - The `session_updated` event for callback resume is not being received or processed
   - The Chat tab might be filtering out events from resumed sessions

### Required Investigation Steps

1. Add console logging to `handleWebSocketMessage` to trace:
   - What `session_updated` events are received
   - What values `currentSessionName`, `agentStatus`, and `wasFinished` have
   - Whether the callback resume detection logic (lines 291-312) is triggered

2. Compare event flow between Sessions tab and Chat tab for the same callback scenario

3. Check if the WebSocket subscription in Chat tab is correctly receiving all events

### Files to Investigate
- `dashboard/src/contexts/ChatContext.tsx` - Main suspect
- `dashboard/src/contexts/WebSocketContext.tsx` - WebSocket subscription mechanism
- `dashboard/src/hooks/useSessions.ts` - How Sessions tab handles updates (for comparison)

### Acceptance Criteria
- [ ] Chat tab reacts to callback resume (parent session continues after child returns)
- [ ] Pending message indicator shows when parent is resumed via callback
- [ ] Agent response from callback resume is displayed in Chat tab

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
