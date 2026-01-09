# Phase 2: Structured Output Model

**Status:** Implementation Ready
**Depends on:** Phase 1 (Unified Input Model)
**Design Reference:** [deterministic-agents-implementation.md](./deterministic-agents-implementation.md) - Section 8 (Structured Result Events)

---

## Objective

Introduce a dedicated `result` event type for storing session results. AI agents send result events instead of relying on message extraction. This creates a uniform result model that deterministic agents will also use.

**End state:** Results are stored as `result` events. The coordinator extracts results from these events for callbacks. Legacy message extraction remains as fallback.

---

## Key Changes

### 1. Event Type Enum

**File:** `servers/agent-coordinator/models.py`
- `SessionEventType` enum (lines 47-60): Add `RESULT = "result"`

### 2. Database Schema

**File:** `servers/agent-coordinator/database.py`
- Events table: Add columns for structured result data
  - `result_type TEXT` - Discriminator: `"autonomous"` or `"procedural"`
  - `result_data TEXT` - JSON structured output (nullable)
- `insert_event()`: Handle new result event fields
- `get_session_result()` (lines 409-427):
  - First query for `event_type='result'`
  - Fall back to legacy `event_type='message'` with `role='assistant'` extraction
  - Return structured dict: `{result_type, result_text, result_data}`

### 3. Claude-Code Executor

**File:** `servers/agent-runner/executors/claude-code/lib/claude_client.py`
- `run_claude_session()` (lines 195-389): After receiving `ResultMessage`, send a `result` event:
  ```python
  session_client.add_event(session_id, {
      "event_type": "result",
      "session_id": session_id,
      "timestamp": datetime.now(UTC).isoformat(),
      "result_type": "autonomous",
      "result_text": message.result
  })
  ```
- Keep existing `message` event for conversation history (optional, for continuity)

### 4. Callback Processor

**File:** `servers/agent-coordinator/services/callback_processor.py`
- `_create_resume_run()` (lines 196-259): Use `get_session_result()` which now returns structured dict
- Update callback template variables to include `result_type` and `result_data` when available
- Callback payload includes full result object for structured access

### 5. Session Result API Endpoint

**File:** `servers/agent-coordinator/main.py`
- `get_session_result_endpoint()` (lines 310-326): Return structured result dict instead of plain text

---

## Result Event Schema

```json
{
  "event_type": "result",
  "session_id": "ses_abc123",
  "timestamp": "2026-01-08T12:00:00Z",
  "result_type": "autonomous",
  "result_text": "Here is the research summary...",
  "result_data": null
}
```

**Fields:**
- `event_type`: Always `"result"`
- `result_type`: `"autonomous"` for AI agents, `"procedural"` for procedural (Phase 4)
- `result_text`: Text output (required)
- `result_data`: Structured JSON output (optional, Phase 4 will use this)

---

## Backward Compatibility

The `get_session_result()` function maintains backward compatibility:

1. First check for `result` event → return structured result
2. Fall back to `message` event with `role='assistant'` → wrap in structured format

This ensures:
- Existing sessions with only message events continue to work
- New sessions get proper result events
- Callbacks receive consistent format regardless of event type used

---

## Files to Modify

| File | Change |
|------|--------|
| `servers/agent-coordinator/models.py` | Add `RESULT` to `SessionEventType` enum |
| `servers/agent-coordinator/database.py` | Add columns, update `get_session_result()` |
| `servers/agent-runner/executors/claude-code/lib/claude_client.py` | Send `result` event after `ResultMessage` |
| `servers/agent-coordinator/services/callback_processor.py` | Use structured result in callbacks |
| `servers/agent-coordinator/main.py` | Update result endpoint response format |

---

## Database Migration

Add columns to events table:

```sql
ALTER TABLE events ADD COLUMN result_type TEXT;
ALTER TABLE events ADD COLUMN result_data TEXT;
```

These columns are nullable - only populated for `result` event types.

---

## Acceptance Criteria

1. **Result event stored:**
   - After AI agent completes, events table contains `event_type='result'`
   - Event has `result_type='autonomous'` and `result_text` populated

2. **Result extraction works:**
   ```bash
   curl /sessions/{session_id}/result
   # Returns: {"result_type": "autonomous", "result_text": "...", "result_data": null}
   ```

3. **Legacy fallback works:**
   - For old sessions without result events, extraction still works via message fallback

4. **Callbacks receive structured result:**
   - Parent agent's callback includes `result_type` and `result_text`
   - Callback template can access structured data

5. **Existing tests pass:** All current callback tests continue working

---

## Testing Strategy

1. Unit test `get_session_result()` with:
   - Session with `result` event → returns structured result
   - Session with only `message` events → returns via fallback
   - Session with no messages → returns None

2. Integration test claude-code executor sends result event

3. Integration test callback processor receives structured result

4. End-to-end test: AI agent → callback → parent receives structured result

5. Regression test: Old sessions without result events still work

---

## References

- [ADR-003](../adr/ADR-003-callback-based-async.md) - Callback-based async
- [ADR-014](../adr/ADR-014-callback-message-format.md) - Callback message format
- [deterministic-agents-implementation.md](./deterministic-agents-implementation.md) - Section 8
- [callback_processor.py](../../servers/agent-coordinator/services/callback_processor.py) - Callback handling
