# Agent Runtime Documentation

Server for tracking agent sessions and events with real-time WebSocket updates.

## Documentation

- [API.md](./API.md) - REST and WebSocket API reference
- [JOBS_API.md](./JOBS_API.md) - Jobs API deep dive (lifecycle, launcher integration)
- [JOB_EXECUTION_FLOW.md](./JOB_EXECUTION_FLOW.md) - Job execution sequence diagram and polling details
- [DATA_MODELS.md](./DATA_MODELS.md) - Event and session data structures
- [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) - SQLite schema
- [USAGE.md](./USAGE.md) - Quick start guide

## Quick Reference

**Server:** `http://127.0.0.1:8765`
**WebSocket:** `ws://127.0.0.1:8765/ws`
**Database:** `.agent-orchestrator/observability.db`