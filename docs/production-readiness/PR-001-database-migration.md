# PR-001: Database Migration (SQLite → PostgreSQL)

**Priority**: P0 (Critical)
**Status**: Pending
**Effort**: Medium

## Problem

SQLite has a single-writer lock. With multiple users creating sessions and events concurrently, write contention becomes a bottleneck.

## Current State

- SQLite database at `.agent-orchestrator/observability.db`
- Tables: sessions, runs, events (3 tables)
- Uses raw `sqlite3` module (not SQLAlchemy)
- Synchronous writes on every event

## Why Address

1. **Write contention**: SQLite serializes all writes. 10 concurrent agent runs logging events will queue up.
2. **No horizontal scaling**: SQLite is file-based. Can't run multiple coordinator instances.
3. **Backup complexity**: File-based backups require coordinator downtime or risk corruption.

## Why NOT Address (Counter-argument)

- SQLite handles thousands of writes/second for simple queries
- If event volume is low (< 100 events/second), SQLite may suffice
- Migration adds operational complexity (PostgreSQL hosting)

## Recommendation

**Address before production.** Event logging during agent runs creates sustained write load. PostgreSQL enables future horizontal scaling.

## Implementation Notes

- Add SQLAlchemy with async driver (`asyncpg`) for PostgreSQL support
- Migrate existing raw `sqlite3` code to SQLAlchemy ORM
- Add connection pooling configuration
- Migrate data with manual script or `alembic`

Note: Since SQLAlchemy is not currently used, this requires rewriting database functions, not just changing a connection string.

## Acceptance Criteria

- [ ] PostgreSQL connection working
- [ ] All existing queries functional
- [ ] Connection pooling configured
- [ ] Data migration script tested
