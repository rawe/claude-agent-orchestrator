# Work Package 3: Dashboard Integration

**Reference**: [agent-callback-architecture.md](./agent-callback-architecture.md)
- Read sections: "Implementation Plan > Phase 3: Dashboard Integration"

## Goal

Update Dashboard to use the new Job API (`POST /jobs`) instead of the Agent Control API. Remove dependency on Agent Control API.

## Runnable State After Completion

- Dashboard Chat tab creates jobs via Job API
- Sessions start/resume through Agent Launcher
- Agent Control API can be disabled (no longer needed by Dashboard)
- WebSocket continues to receive session updates

## Files to Modify

| File | Changes |
|------|---------|
| `dashboard/src/services/api.ts` | Remove agentControlApi, add job endpoints |
| `dashboard/src/services/chatService.ts` | Use Job API instead of Agent Control API |
| `dashboard/src/pages/Chat.tsx` | Listen for session_start events (auto-resume) |
| `dashboard/.env.example` | Remove VITE_AGENT_CONTROL_API_URL |

## Files to Delete (After Verification)

| File | Reason |
|------|--------|
| Agent Control API usage in MCP server | No longer needed |

## Implementation Tasks

### 1. Update API Service (`services/api.ts`)

Remove:
```typescript
export const agentControlApi = axios.create({
  baseURL: import.meta.env.VITE_AGENT_CONTROL_API_URL || 'http://localhost:9501',
});
```

The job endpoints use the same base URL as `agentOrchestratorApi`:
- `POST /jobs` - create job
- `GET /jobs/{job_id}` - get job status (optional, for debugging)

### 2. Update Chat Service (`services/chatService.ts`)

Replace Agent Control API calls with Job API:

**Before (Agent Control API):**
```typescript
export const startSession = async (params) => {
  return agentControlApi.post('/start', params);
};
```

**After (Job API):**
```typescript
export const startSession = async (params: {
  sessionName: string;
  agentName?: string;
  prompt: string;
  projectDir: string;
}) => {
  return agentOrchestratorApi.post('/jobs', {
    type: 'start_session',
    session_name: params.sessionName,
    agent_name: params.agentName,
    prompt: params.prompt,
    project_dir: params.projectDir,
  });
};

export const resumeSession = async (params: {
  sessionName: string;
  prompt: string;
}) => {
  return agentOrchestratorApi.post('/jobs', {
    type: 'resume_session',
    session_name: params.sessionName,
    prompt: params.prompt,
  });
};
```

### 3. Update Chat Page (`pages/Chat.tsx`)

**Important change per spec:**

> IMPORTANT: Also listen for session start events for the current session name in the websocket, as now the resume can automatically start the session again.

The Chat page must handle the case where:
1. User sends a resume message
2. Job is created, session resumes
3. Child agent later completes → triggers callback
4. Callback creates another resume job
5. Session starts again automatically

Listen for `session_start` / `session_updated` WebSocket events:
- If current session name matches and status becomes "running", update UI
- This handles automatic resumes from callbacks

### 4. Remove Environment Variable

In `dashboard/.env.example` and any `.env` files:
- Remove `VITE_AGENT_CONTROL_API_URL`

### 5. Update Types (if needed)

Add job-related types in `dashboard/src/types/`:
```typescript
export interface CreateJobRequest {
  type: 'start_session' | 'resume_session';
  session_name: string;
  agent_name?: string;
  prompt: string;
  project_dir?: string;
}

export interface CreateJobResponse {
  job_id: string;
  status: 'pending';
}
```

## Testing Checklist

- [ ] Dashboard loads without errors (no Agent Control API dependency)
- [ ] Start new session via Chat tab → job created → session starts
- [ ] Resume session via Chat tab → job created → session resumes
- [ ] WebSocket updates show session status changes
- [ ] Automatic resume (from callback) updates Chat UI correctly
- [ ] Error handling: what happens if Launcher is not running?

## Notes

- The Dashboard relies on WebSocket for session updates; no need to poll job status
- Job failures are a known limitation (POC scope) - Dashboard won't know if job fails
- Test with Agent Launcher running (Package 2 must be complete)
