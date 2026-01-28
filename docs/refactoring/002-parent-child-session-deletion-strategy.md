# Parent-Child Session Deletion Strategy

**Status:** Open
**Priority:** High
**Created:** 2026-01-02

## Context

The Agent Orchestrator uses a parent-child session hierarchy where:
- Parent sessions spawn child sessions for sub-agent orchestration
- Child sessions use `parent_session_id` foreign key to reference their parent
- Execution modes (SYNC, ASYNC_POLL, ASYNC_CALLBACK) define how parent-child lifecycle is managed

ADR-003, ADR-005, and ADR-010 establish that parents explicitly control child lifecycles through these execution modes. The architectural intent is that child sessions exist to serve their parent's orchestration goals.

## Problem

The current database schema uses `ON DELETE SET NULL` for the `parent_session_id` foreign key constraint:

```sql
parent_session_id TEXT REFERENCES sessions(session_id) ON DELETE SET NULL
```

This creates several problems when a parent session is deleted:

1. **Silent Orphaning**: Child sessions survive with `parent_session_id = NULL`, becoming orphans
2. **Lost Hierarchy**: Parent-child relationships are permanently broken - dashboard shows disconnected sessions
3. **Callback Failures**: Pending callbacks to deleted parent sessions fail (logged but not resolved)
4. **Data Accumulation**: Database fills with orphaned child session records over time
5. **No Child Detection**: No function exists to find children of a session, preventing cleanup
6. **UI Confusion**: Dashboard displays orphaned sessions with null parent_id fields and no context

The documentation (`docs/features/agent-callback-architecture.md`, line 1034) acknowledges this gap:
> "When a parent session is deleted while children are running or callbacks are pending, the callbacks will fail gracefully (Callback Processor logs an error). No automatic cleanup of pending notifications."

## Proposed Solution

### Option A: CASCADE DELETE (Recommended)

Change the foreign key constraint to cascade delete child sessions when parent is deleted:

```sql
parent_session_id TEXT REFERENCES sessions(session_id) ON DELETE CASCADE
```

**Rationale:**
- Matches architectural intent: children exist to serve parent's orchestration goals
- When parent is deleted, its orchestration context is gone - children have no independent purpose
- ASYNC_CALLBACK mode explicitly requires parent for resume callbacks
- SYNC mode blocks parent waiting for child - child is part of parent's work
- Cleaner than SET NULL - no orphaned records

**Safeguards to implement:**
- Add endpoint parameter to check for running children before deletion
- Return count of cascaded children in delete response
- Log warning when cascading deletes child sessions

### Option B: SET NULL with Cleanup (Alternative)

Keep current `ON DELETE SET NULL` but add explicit cleanup:

1. Add `get_child_sessions(parent_session_id)` function
2. Before parent delete: cancel/terminate running children
3. After parent delete: explicitly delete orphaned children
4. Add periodic cleanup job for orphaned sessions

**Pros:** More control over cleanup process
**Cons:** More complex, same end result, risk of orphans if cleanup fails

### Option C: Prevent Deletion if Children Exist

Block parent deletion entirely if child sessions exist:

```python
def delete_session(session_id):
    children = get_child_sessions(session_id)
    if children:
        raise HTTPException(400, "Cannot delete session with active children")
```

**Pros:** Safest - no unintended deletions
**Cons:** User must manually delete children first, tedious for deep hierarchies

## Implementation Strategy

### Phase 1: Add Helper Functions
1. Create `get_child_sessions(parent_session_id)` in `database.py`
2. Add `count_child_sessions(parent_session_id)` for quick checks

### Phase 2: Update Schema
Since SQLite doesn't support `ALTER CONSTRAINT`, options:
- **Option 2a:** Recreate sessions table with new constraint (migration script)
- **Option 2b:** Use trigger to implement cascade behavior:
  ```sql
  CREATE TRIGGER cascade_delete_child_sessions
  BEFORE DELETE ON sessions
  FOR EACH ROW
  BEGIN
      DELETE FROM sessions WHERE parent_session_id = OLD.session_id;
  END;
  ```

### Phase 3: Update Delete Endpoint
1. Add optional `cascade` query parameter (default: true)
2. Check for children before deletion
3. Return statistics including cascaded children count
4. Broadcast SSE event for cascaded deletions

### Phase 4: Update Documentation
1. Update ADR-003, ADR-005, ADR-010 to clarify cascade behavior
2. Document parent-child lifecycle in API docs
3. Add warning about cascade delete in deletion endpoint docs

### Phase 5: Add Tests
- Test parent deletion with no children
- Test parent deletion cascades to children
- Test multi-level cascade (grandchildren)
- Test deletion blocked if children running (if safeguard enabled)

## Affected Files

### Backend (Agent Coordinator)
- `servers/agent-coordinator/database.py`
  - Line 27: FK constraint `ON DELETE SET NULL` → `ON DELETE CASCADE`
  - Lines 252-299: `delete_session()` function - add cascade reporting
  - New: `get_child_sessions()` and `count_child_sessions()` functions

- `servers/agent-coordinator/main.py`
  - Lines 597-625: Delete endpoint - report cascaded children count

### Dashboard
- `apps/dashboard/src/types/session.ts` - Consider adding orphan detection types
- `apps/dashboard/src/components/features/sessions/SessionCard.tsx` - Optional: visual indicator for orphaned sessions
- `apps/dashboard/src/contexts/SessionsContext.tsx` - Handle cascaded deletion SSE events

### Documentation
- `docs/adr/ADR-003-callback-based-async.md` - Clarify cascade behavior
- `docs/adr/ADR-005-parent-session-context-propagation.md` - Clarify lifecycle
- `docs/adr/ADR-010-session-identity-and-executor-abstraction.md` - Document cascade
- `docs/features/agent-callback-architecture.md` - Update line 1034 gap description
- `docs/components/agent-coordinator/API.md` - Document cascade in delete endpoint
- `docs/components/agent-coordinator/DATABASE_SCHEMA.md` - Update FK constraint docs

### Tests
- `tests/integration/05-child-agent-callback.md` - Add parent deletion test
- `tests/integration/06-concurrent-callbacks.md` - Test cascaded deletion
- New: `tests/integration/XX-parent-session-deletion.md` - Dedicated deletion tests

## Acceptance Criteria

- [ ] Foreign key constraint uses `ON DELETE CASCADE` (or equivalent trigger)
- [ ] Helper function `get_child_sessions()` exists and works
- [ ] Delete endpoint reports count of cascaded child deletions
- [ ] SSE broadcasts cascaded deletion events to dashboard
- [ ] Documentation updated to reflect cascade behavior
- [ ] Integration tests cover parent deletion scenarios
- [ ] No orphaned sessions remain after parent deletion
- [ ] Dashboard handles cascaded deletion gracefully

## Decision Required

Before implementation, confirm the approach:

1. **CASCADE DELETE** (delete children when parent deleted) - Recommended
2. **SET NULL + Cleanup** (keep current + add cleanup logic)
3. **Block Deletion** (prevent deletion if children exist)

The recommendation is **Option A (CASCADE DELETE)** as it aligns with the architectural intent and provides the cleanest solution.
