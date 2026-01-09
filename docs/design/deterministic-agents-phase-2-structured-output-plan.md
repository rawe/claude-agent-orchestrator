# Phase 2: Structured Output Model - Implementation Plan

**Design Doc:** `docs/design/deterministic-agents-phase-2-structured-output.md`
**Breaking Changes:** Yes (no backwards compatibility needed - DB will be dropped, all clients in monorepo)

---

## Overview

Introduce a dedicated `result` event type for storing session results. AI agents send result events instead of relying on message extraction. This creates a uniform result model that deterministic agents (Phase 4) will also use.

---

## Result Schema (Simplified)

```json
{
  "result_text": "Human readable output...",
  "result_data": {"key": "value"}
}
```

- **result_text**: Always present (human-readable output)
- **result_data**: Present for deterministic agents, `null` for AI agents
- **No result_type field**: Presence of `result_data` is the discriminator

---

## 1. Agent Coordinator Changes

### 1.1 Models (`servers/agent-coordinator/models.py`)

**Add RESULT to SessionEventType enum (line 47-60):**
```python
class SessionEventType(str, Enum):
    RUN_START = "run_start"
    RUN_COMPLETED = "run_completed"
    PRE_TOOL = "pre_tool"
    POST_TOOL = "post_tool"
    MESSAGE = "message"
    RESULT = "result"  # NEW
```

**Add result fields to Event model (line 302-322):**
```python
class Event(BaseModel):
    # ... existing fields ...
    # Result fields (for event_type='result')
    result_text: Optional[str] = None
    result_data: Optional[dict] = None
```

**Add SessionResult response model:**
```python
class SessionResult(BaseModel):
    """Structured result from a session."""
    result_text: Optional[str] = None
    result_data: Optional[dict] = None
```

### 1.2 Database (`servers/agent-coordinator/database.py`)

**Update events table schema (line 95-111):**
```sql
CREATE TABLE IF NOT EXISTS events (
    ...existing columns...
    result_text TEXT,    -- NEW: text output
    result_data TEXT     -- NEW: JSON structured output
)
```

**Update insert_event() (line 196-218):**
- Add `result_text`, `result_data` to INSERT statement
- Serialize `result_data` as JSON

**Replace get_session_result() (line 409-427):**
```python
def get_session_result(session_id: str) -> dict | None:
    """Get structured result from result event."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("""
        SELECT result_text, result_data FROM events
        WHERE session_id = ? AND event_type = 'result'
        ORDER BY timestamp DESC LIMIT 1
    """, (session_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "result_text": row["result_text"],
        "result_data": json.loads(row["result_data"]) if row["result_data"] else None
    }
```

### 1.3 API Endpoint (`servers/agent-coordinator/main.py`)

**Update get_session_result_endpoint() (line 309-326):**
```python
@app.get("/sessions/{session_id}/result", tags=["Sessions"])
async def get_session_result_endpoint(session_id: str) -> SessionResult:
    """Get structured result from session."""
    session = get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["status"] != "finished":
        raise HTTPException(status_code=400, detail="Session not finished")

    result = get_session_result(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No result found")

    return SessionResult(**result)
```

### 1.4 Callback Processor (`servers/agent-coordinator/services/callback_processor.py`)

**Update _create_resume_run() (line 196-259):**
- Extract structured result: `result = get_session_result(child_session_id)`
- Pass raw `result_data` JSON in callback when available

**Update callback templates:**
```python
CALLBACK_PROMPT_TEMPLATE = """<agent-callback session="{child_session_id}" status="completed">
## Child Result

{result_text}

{result_data_section}
</agent-callback>

Please continue with the orchestration based on this result."""
```

Where `{result_data_section}` is:
- Empty string if `result_data` is None (AI agent)
- `## Structured Data\n\n```json\n{json.dumps(result_data, indent=2)}\n``` ` if present (deterministic agent)

---

## 2. Agent Runner / Executor Changes

### 2.1 Claude-Code Executor (`servers/agent-runner/executors/claude-code/lib/claude_client.py`)

**Send result event after ResultMessage (after line 366):**
```python
if isinstance(message, ResultMessage):
    if executor_session_id is None:
        executor_session_id = message.session_id
    result = message.result

    # Send result event (NEW)
    if result and session_id:
        try:
            session_client.add_event(session_id, {
                "event_type": "result",
                "session_id": session_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "result_text": result,
                "result_data": None  # AI agents produce text only
            })
        except SessionClientError:
            pass  # Silent failure - don't break execution

    # Keep existing message event for conversation history
    if result and session_id:
        try:
            session_client.add_event(session_id, {
                "event_type": "message",
                ...
            })
        except SessionClientError:
            pass
```

### 2.2 Test Executor (`servers/agent-runner/executors/test-executor/`)

**Update to send result event:**
Similar pattern - after generating response, send a `result` event with `result_data: null`.

---

## 3. Embedded MCP Server Changes

### 3.1 Tools (`servers/agent-runner/lib/agent_orchestrator_mcp/tools.py`)

**Update get_agent_session_result() return format (around line 196-210):**
```python
# Before:
return {
    "session_id": session_id,
    "result": session_result,
}

# After - return raw result_data directly:
return {
    "session_id": session_id,
    "result_text": session_result.get("result_text"),
    "result_data": session_result.get("result_data"),  # Raw JSON or null
}
```

**Update start_agent_session() sync mode return (around line 155-175):**
```python
# Before:
return {
    "session_id": session_id,
    "result": session_result,
}

# After - return raw result_data directly:
return {
    "session_id": session_id,
    "result_text": result.get("result_text"),
    "result_data": result.get("result_data"),  # Raw JSON or null
}
```

### 3.2 Coordinator Client (`servers/agent-runner/lib/agent_orchestrator_mcp/coordinator_client.py`)

**Update get_session_result() (around line 249):**
```python
async def get_session_result(self, session_id: str) -> dict | None:
    """Get structured session result."""
    async with self._get_client() as client:
        response = await client.get(
            f"{self._coordinator_url}/sessions/{session_id}/result",
            headers=self._get_auth_headers(),
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()  # Returns {result_text, result_data}
```

---

## 4. Dashboard Frontend Changes

### 4.1 Types (`dashboard/src/types/`)

**Add to event.ts:**
```typescript
export interface SessionResult {
  result_text: string | null;
  result_data: Record<string, unknown> | null;
}
```

**Extend SessionEvent in event.ts:**
```typescript
export interface SessionEvent {
  // ... existing fields ...
  // Result fields (for event_type='result')
  result_text?: string;
  result_data?: Record<string, unknown>;
}
```

**Add 'result' to EventType:**
```typescript
export type EventType = 'run_start' | 'run_completed' | 'pre_tool' | 'post_tool' | 'message' | 'result';
```

### 4.2 Services (`dashboard/src/services/sessionService.ts`)

**Add getSessionResult():**
```typescript
export async function getSessionResult(sessionId: string): Promise<SessionResult> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/result`);
  if (!response.ok) throw new Error('Failed to fetch result');
  return response.json();
}
```

### 4.3 Components

**Update EventCard.tsx to display result events:**
- Add case for `event_type === 'result'`
- Display result_text
- Show expandable result_data if present (JSON viewer)

---

## 5. Chat-UI Frontend Changes

### 5.1 Types (`interfaces/chat-ui/src/types/index.ts`)

**Extend SessionEvent:**
```typescript
export interface SessionEvent {
  // ... existing fields ...
  result_text?: string;
  result_data?: Record<string, unknown>;
}
```

**Add 'result' to event_type union.**

### 5.2 Context (`interfaces/chat-ui/src/contexts/ChatContext.tsx`)

**Handle result events in reducer:**
- When `event_type === 'result'`, store structured result
- Optionally display result_data in chat (for debugging/visibility)

---

## 6. Integration Tests

### 6.1 New Test Case: `tests/integration/11-result-event-emission.md`

**Verify:**
1. Claude-code executor sends `result` event after completion
2. Event has correct schema: `{event_type: 'result', result_text: '...', result_data: null}`
3. Event is stored in database
4. SSE stream broadcasts result event

### 6.2 New Test Case: `tests/integration/12-structured-result-api.md`

**Verify:**
1. `GET /sessions/{id}/result` returns structured format
2. Response: `{result_text: '...', result_data: null}`
3. 404 if no result event exists

### 6.3 New Test Case: `tests/integration/13-structured-callback.md`

**Verify:**
1. Child completes with result event
2. Parent receives callback with structured result
3. result_data passed as raw JSON when available

### 6.4 Update Existing Tests

- **05-child-agent-callback.md**: Verify callback format updated
- **06-concurrent-callbacks.md**: Verify all callbacks include structured results
- **07-callback-on-child-failure.md**: No change (failure callbacks don't have result events)

---

## Implementation Order

1. **Coordinator models & database** - Foundation
2. **Coordinator API endpoint** - Enable testing
3. **Claude-code executor** - Send result events
4. **Test executor** - Send result events (for integration tests)
5. **Callback processor** - Use structured results
6. **MCP server tools** - Return structured format
7. **Dashboard frontend** - Display structured results
8. **Chat-UI frontend** - Handle result events
9. **Integration tests** - Verify end-to-end

---

## Files to Modify

| Component | File | Changes |
|-----------|------|---------|
| Coordinator | `servers/agent-coordinator/models.py` | Add RESULT enum, result_text/result_data fields to Event, SessionResult model |
| Coordinator | `servers/agent-coordinator/database.py` | Add columns, update insert_event, rewrite get_session_result |
| Coordinator | `servers/agent-coordinator/main.py` | Update result endpoint response |
| Coordinator | `servers/agent-coordinator/services/callback_processor.py` | Use structured result in callbacks, include raw result_data |
| Executor | `servers/agent-runner/executors/claude-code/lib/claude_client.py` | Send result event |
| Executor | `servers/agent-runner/executors/test-executor/test-executor` | Send result event |
| MCP Server | `servers/agent-runner/lib/agent_orchestrator_mcp/tools.py` | Return result_text + result_data directly |
| MCP Server | `servers/agent-runner/lib/agent_orchestrator_mcp/coordinator_client.py` | Parse structured response |
| Dashboard | `dashboard/src/types/event.ts` | Add result_text/result_data fields, SessionResult type |
| Dashboard | `dashboard/src/services/sessionService.ts` | Add getSessionResult |
| Dashboard | `dashboard/src/components/features/sessions/EventCard.tsx` | Display result events |
| Chat-UI | `interfaces/chat-ui/src/types/index.ts` | Add result_text/result_data fields |
| Chat-UI | `interfaces/chat-ui/src/contexts/ChatContext.tsx` | Handle result events |
| Tests | `tests/integration/11-result-event-emission.md` | New test |
| Tests | `tests/integration/12-structured-result-api.md` | New test |
| Tests | `tests/integration/13-structured-callback.md` | New test |

---

## Verification

1. **Unit Test:** `get_session_result()` returns `{result_text, result_data}` dict
2. **Manual Test:** Start session, verify result event in SSE stream
3. **API Test:** `curl /sessions/{id}/result` returns `{result_text: "...", result_data: null}`
4. **Integration Test:** Run `/tests:case 11-result-event-emission`
5. **E2E Test:** Parent-child callback includes result_data as raw JSON
6. **Dashboard:** Result events display correctly in EventTimeline
7. **Chat-UI:** Result events handled without errors

---

## Database Migration

Since backwards compatibility is not needed:
1. Drop existing database: `rm .agent-orchestrator/observability.db`
2. Restart coordinator - tables recreated with new schema
