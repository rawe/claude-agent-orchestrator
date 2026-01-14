# PR-002: Run Queue Simplification

**Priority**: P1 (High)
**Status**: Pending
**Effort**: Medium

## Problem

The run queue uses an in-memory cache with write-through to SQLite. This dual-source architecture adds complexity without clear benefit, and the cache has a bloat issue.

## Current State

**Architecture**: Write-through cache pattern
- All mutations write to database FIRST, then update in-memory cache
- Reads come from cache for fast polling
- Database is already the source of truth

**Code location**: `servers/agent-coordinator/services/run_queue.py` (620+ lines)

**Key components**:
- `self._runs: dict[str, Run]` - In-memory dictionary (line 323)
- `threading.Lock()` - Single lock for all operations (line 324)
- Write-through on every operation: `add_run()`, `claim_run()`, `update_run_status()`

**Recovery modes** (already implemented):
- `stale` (default): Runs > 5 min old get recovered on restart
- `all`: Aggressive recovery of all non-terminal runs
- Recovery works correctly - no data loss on coordinator restart

## Why Address

### 1. Cache Bloat Issue

Terminal runs (completed/failed/stopped) remain in cache **indefinitely**. Only removed when session is deleted.

```python
# run_queue.py - No eviction policy exists
# get_all_runs() returns ALL runs including terminal ones
# Long-running coordinators accumulate thousands of stale runs in memory
```

### 2. Unnecessary Complexity

The cache was a premature optimization. With write-through, the database is already authoritative:

| Operation | Current Flow |
|-----------|-------------|
| Create run | DB insert → cache add |
| Claim run | DB update (atomic) → cache update |
| Update status | DB update → cache update |
| Get run | Cache lookup → DB fallback if miss |

The `get_run_with_fallback()` function (line 606-622) provides database fallback for historical run queries.

### 3. Code Simplification

Removing the cache would:
- Eliminate ~400 lines of synchronization code
- Remove dual-source-of-truth bugs
- Simplify testing (no cache state to manage)
- Fix the bloat issue automatically (DB queries don't accumulate)

## Why NOT Address (Counter-argument)

- **Claim performance**: Runners poll frequently. Cache allows O(n) memory scan vs DB query.
- **Working system**: Current implementation is functional and tested.
- **Risk**: Refactoring core queue logic could introduce bugs.

**Assessment**: With proper SQLite indexing on `(status, created_at)`, claim queries perform well for realistic volumes (< 1000 pending runs). The simplification benefit outweighs the minor latency increase.

## Recommendation

**Remove the in-memory cache. Use database directly.**

The write-through pattern already treats the database as authoritative. The cache is a read optimization that adds complexity and has a bloat bug.

## Implementation Plan

### Option A: Database-Only Queue (Recommended)

1. **Simplify RunQueue class** (index `idx_runs_status_created` already exists at `database.py:91`):
   - Remove `self._runs` dictionary
   - Remove `self._lock` (SQLite handles concurrency)
   - Remove `_load_runs()` on init
   - Remove cache sync logic
   - Direct DB queries for all operations

2. **Update claim logic**:
   ```python
   def claim_run(self, runner: Runner) -> Optional[Run]:
       # Direct DB query with demand matching
       return db_claim_first_matching_run(
           runner_id=runner.runner_id,
           capabilities=runner.capabilities
       )
   ```

3. **Estimated reduction**: ~620 lines → ~150 lines

### Option B: Add Cache Eviction (Minimal Change)

If full refactor is too risky:
- Add TTL-based eviction for terminal runs (e.g., 1 hour after completion)
- Add background cleanup task
- Keep dual-source architecture

**Not recommended**: Adds more complexity to fix a symptom, not the root cause.

### Option C: External Queue (Future)

Consider Redis/RabbitMQ only if:
- Coordinator horizontal scaling needed (PR-004)
- 500+ concurrent runners
- Complex routing beyond tag matching

**Not needed initially.**

## Code References

| Component | Location |
|-----------|----------|
| RunQueue class | `run_queue.py:303-623` |
| Cache dictionary | `run_queue.py:323` |
| Write-through pattern | `run_queue.py:382-427` (add_run example) |
| Claim with DB atomic | `run_queue.py:429-462` |
| Fallback for historical queries | `run_queue.py:606-622` |
| Recovery modes | `run_queue.py:332-351` |
| DB claim function | `database.py:673-692` |

## Acceptance Criteria

- [ ] In-memory cache removed from RunQueue
- [ ] All operations query database directly
- [ ] Recovery modes still functional
- [ ] No memory growth from completed runs
- [ ] Claim latency acceptable (< 100ms with 1000 pending runs)
