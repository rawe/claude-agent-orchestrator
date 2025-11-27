# BUG-003: Resumed Session Does Not Show Running Status

## Problem

When an agent session is resumed, the frontend does not update to show `"running"` status. The session remains displayed as `"finished"` even though it is actively running.

## Symptom

1. User has a previously completed session (status: `"finished"`)
2. User resumes the session
3. Session is actively running in the backend
4. Frontend still shows status as `"finished"`
5. Autoscroll and other running-state features don't work (requires `isRunning === true`)

## Root Cause

**Backend issue.** When a session is resumed, only the `last_resumed_at` metadata is updated. No event is sent to change the session status to `"running"`.

### New Session vs Resumed Session Flow

| Session Type | What Happens | Status Update |
|--------------|--------------|---------------|
| **New** | SDK sends `session_start` event | Frontend sets `status: 'running'` ✓ |
| **Resumed** | Only `last_resumed_at` metadata updated | No status change ✗ |

## Files

**Backend (where the bug is):**

- `plugins/agent-orchestrator/skills/agent-orchestrator/commands/lib/claude_client.py:218-223`
  ```python
  else:
      # Resume: update last_resumed_at
      session_client.update_session(
          session_id=session_id,
          last_resumed_at=datetime.now(UTC).isoformat()
      )
  ```
  Only metadata is updated, no status change.

- `plugins/agent-orchestrator/skills/agent-orchestrator/commands/lib/session_client.py:100-114`
  `update_session()` method doesn't support updating `status` field.

**Frontend (works correctly, waiting for events that never arrive):**

- `agent-orchestrator-frontend/src/hooks/useSessions.ts:42-45` - Handles `session_updated` messages
- `agent-orchestrator-frontend/src/hooks/useSessions.ts:48-78` - Handles `session_start` events and sets `status: 'running'`

## Impact

- Session status badge shows wrong state
- `isRunning` check fails in `EventTimeline.tsx` → autoscroll disabled
- User cannot tell if resumed session is active

## Related

- BUG-002: Autoscroll relies on `isRunning` which depends on correct session status

## Solution Proposals

See:
- [Solution A: Send session_start event on resume](./solution-a-send-session-start.md)
- [Solution B: Add status field to update_session](./solution-b-update-status-field.md)
- [Solution C: New session_resume event type](./solution-c-session-resume-event.md)
