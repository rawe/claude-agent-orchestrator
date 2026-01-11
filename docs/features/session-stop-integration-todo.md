# Session Stop Integration - Implementation TODO

This document describes the remaining tasks to fully integrate the Session Stop Command feature with the dashboard.

## Background

The backend implementation for stopping sessions is **complete** (see `docs/features/session-stop-command.md`). However, the dashboard integration requires updates to properly use the new endpoint and handle the response format.

## What Was Already Implemented

In the previous coding session, the following backend components were implemented:

### New Files Created
- `servers/agent-coordinator/services/stop_command_queue.py` - Thread-safe queue with asyncio Events

### Modified Backend Files
- `servers/agent-coordinator/services/run_queue.py` - Added `STOPPING` and `STOPPED` run statuses
- `servers/agent-coordinator/main.py`:
  - `POST /sessions/{session_id}/stop` endpoint
  - Modified `GET /runner/runs` to return `stop_runs` and wake up immediately
  - `POST /runner/runs/{run_id}/stopped` endpoint
  - Integrated stop command queue with runner registration

### Modified Runner Files
- `servers/agent-runner/lib/api_client.py` - Added `stop_runs` to `PollResult`, `report_stopped()` method
- `servers/agent-runner/lib/poller.py` - Added `_handle_stop()` with SIGTERM→SIGKILL escalation

### Updated Documentation
- `docs/components/agent-coordinator/API.md` - New endpoints documented
- `docs/components/agent-coordinator/DATA_MODELS.md` - Updated run statuses
- `docs/ARCHITECTURE.md` - Updated to reflect stop capability

### Database Note
The database schema uses TEXT for session status, so 'stopping' can be added without schema migration.
See: `servers/agent-coordinator/database.py` line 80-89 (`update_session_status` accepts any string).

## Current State

### Backend (Complete)
- `POST /sessions/{session_id}/stop` - Stop by session ID (convenience endpoint)
  - Returns: `{ ok, session_id, run_id, session_name, status: "stopping" }`
- `POST /runs/{run_id}/stop` - Stop by run ID (direct control)
  - Returns: `{ ok, run_id, session_name, status: "stopping" }`
- Both endpoints share `_stop_run()` helper function
- Runs transition: `RUNNING` → `STOPPING` → `STOPPED`
- Stop commands wake up runner immediately via asyncio Events

### Dashboard (Needs Updates)
- Has UI for stop button (works, shows on running sessions)
- Has confirmation modal (works)
- `sessionService.stopSession()` exists but expects different response format
- Session type doesn't include `run_id` field
- No visibility into run status for running sessions

---

## Tasks

### Task 1: Update Session Service Response Handling

**File:** `dashboard/src/services/sessionService.ts`

**Current Code (lines 45-57):**
```typescript
async stopSession(sessionId: string): Promise<{ success: boolean; message: string }> {
  try {
    const response = await agentOrchestratorApi.post(`/sessions/${sessionId}/stop`);
    return response.data;
  } catch {
    // Mock response until backend is implemented
    console.warn('Stop session endpoint not implemented, returning mock response');
    return {
      success: false,
      message: 'Stop session feature is not yet implemented in the backend',
    };
  }
}
```

**Required Changes:**
1. Update return type to match backend response
2. Map backend response to expected format
3. Handle specific error cases (session not running, no run found, etc.)

**New Implementation:**
```typescript
interface StopSessionResponse {
  ok: boolean;
  session_id: string;
  run_id: string;
  status: string;
}

async stopSession(sessionId: string): Promise<{ success: boolean; message: string; run_id?: string }> {
  try {
    const response = await agentOrchestratorApi.post<StopSessionResponse>(`/sessions/${sessionId}/stop`);
    return {
      success: response.data.ok,
      message: `Session stop initiated (run: ${response.data.run_id})`,
      run_id: response.data.run_id,
    };
  } catch (error: unknown) {
    if (axios.isAxiosError(error) && error.response) {
      const detail = error.response.data?.detail || 'Failed to stop session';
      return {
        success: false,
        message: detail,
      };
    }
    return {
      success: false,
      message: 'Failed to stop session',
    };
  }
}
```

---

### Task 2: Add Run Info to Session Display (Optional Enhancement)

To show users which run is running a session, we need to track run-session relationships.

**Option A: Extend Session Type**

**File:** `dashboard/src/types/session.ts`

Add optional run_id field:
```typescript
export interface Session {
  session_id: string;
  session_name?: string;
  status: SessionStatus;
  created_at: string;
  modified_at?: string;
  project_dir?: string;
  agent_name?: string;
  parent_session_name?: string;
  run_id?: string;  // NEW: Associated run ID for running sessions
}
```

**Backend Change Required:**
- `GET /sessions` would need to include `run_id` for running sessions
- This requires looking up runs by `session_name` for sessions with `status='running'`

**Option B: Separate Run Lookup (Simpler)**

Keep session and run separate, only fetch run info when needed (e.g., on stop action).

---

### Task 3: Handle Stop Status in UI

When a session is being stopped, it transitions through `STOPPING` state. The UI should reflect this.

**File:** `dashboard/src/types/session.ts`

Update status type:
```typescript
export type SessionStatus = 'running' | 'stopping' | 'finished' | 'stopped';
```

**File:** `dashboard/src/components/features/sessions/SessionCard.tsx`

Update status badge colors:
- `running` → blue
- `stopping` → amber (animated/pulsing)
- `finished` → green
- `stopped` → red/gray

Update stop button visibility:
```typescript
// Don't show stop button for sessions already being stopped
{session.status === 'running' && onStop && (
  // ... stop button
)}
```

**File:** `dashboard/src/hooks/useSessions.ts`

Handle `session_updated` SSE messages to update status to 'stopping'.

---

### Task 4: Backend - Broadcast Session Status Change

Currently, when `POST /sessions/{session_id}/stop` is called, the session status isn't updated in the database. We need to:

**File:** `servers/agent-coordinator/main.py`

In `stop_session()` endpoint, after queueing the stop command:
1. Update session status to 'stopping' (new status)
2. Broadcast `session_updated` SSE message

```python
@app.post("/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    # ... existing code ...

    # Update session status to stopping
    update_session_status(session_id, "stopping")

    # Broadcast to SSE clients
    updated_session = get_session_by_id(session_id)
    message = {"type": "session_updated", "session": updated_session}
    await broadcast_to_sse_clients(message)

    return {
        "ok": True,
        "session_id": session_id,
        "run_id": run.run_id,
        "status": "stopping"
    }
```

**File:** `servers/agent-coordinator/database.py`

Ensure `update_session_status()` accepts 'stopping' as valid status.

---

### Task 5: Handle Session Stop Event from Runner

When the runner terminates a process and reports `POST /runner/runs/{run_id}/stopped`, we need to:

**File:** `servers/agent-coordinator/main.py`

In `report_run_stopped()` endpoint:
1. Update session status to 'stopped'
2. Broadcast `session_updated` SSE message
3. Consider creating a `run_stopped` event

```python
@app.post("/runner/runs/{run_id}/stopped")
async def report_run_stopped(run_id: str, request: RunStoppedRequest):
    # ... existing code ...

    # Get session name from run and update session status
    session = get_session_by_name(run.session_name)
    if session:
        update_session_status(session["session_id"], "stopped")

        # Broadcast update
        updated_session = get_session_by_id(session["session_id"])
        message = {"type": "session_updated", "session": updated_session}
        await broadcast_to_sse_clients(message)

    return {"ok": True}
```

---

## File Reference Summary

### Backend Files
| File | Purpose |
|------|---------|
| `servers/agent-coordinator/main.py` | Stop endpoint, run stopped reporting |
| `servers/agent-coordinator/database.py` | Session status updates |
| `servers/agent-coordinator/services/run_queue.py` | Run status management |
| `servers/agent-coordinator/services/stop_command_queue.py` | Stop command queue (done) |

### Dashboard Files
| File | Purpose |
|------|---------|
| `dashboard/src/services/sessionService.ts` | API calls - update response handling |
| `dashboard/src/types/session.ts` | Add 'stopping' status type |
| `dashboard/src/components/features/sessions/SessionCard.tsx` | Status badge, stop button |
| `dashboard/src/components/features/sessions/SessionList.tsx` | Filter for stopping status |
| `dashboard/src/hooks/useSessions.ts` | SSE handling for status updates |
| `dashboard/src/pages/AgentSessions.tsx` | Stop handler, success messages |

### Documentation
| File | Purpose |
|------|---------|
| `docs/features/session-stop-command.md` | Feature specification |
| `docs/components/agent-coordinator/API.md` | API documentation (updated) |
| `docs/components/agent-coordinator/DATA_MODELS.md` | Data models (updated) |
| `docs/ARCHITECTURE.md` | Architecture overview (updated) |

---

## Implementation Order

1. **Task 4: Backend - Broadcast Session Status** (Critical)
   - Without this, dashboard won't see status changes

2. **Task 5: Handle Session Stop Event** (Critical)
   - Completes the stop flow

3. **Task 3: Handle Stop Status in UI** (Required)
   - Show 'stopping' state in dashboard

4. **Task 1: Update Session Service** (Required)
   - Fix response handling, remove mock code

5. **Task 2: Add Run Info** (Optional Enhancement)
   - Nice to have for visibility

---

## Testing Checklist

- [ ] Stop button appears only on running sessions
- [ ] Clicking stop shows confirmation modal
- [ ] Confirming stop calls backend successfully
- [ ] Session status changes to 'stopping' immediately
- [ ] Status badge shows amber/pulsing for 'stopping'
- [ ] After process terminates, status changes to 'stopped'
- [ ] SSE broadcasts update dashboard in real-time
- [ ] Error cases show appropriate messages (session not found, not running, etc.)
- [ ] Multiple stop requests are deduplicated (backend handles this)
