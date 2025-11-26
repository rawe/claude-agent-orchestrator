# Feature 003: Session Storage Migration

## Overview

Migrate Agent Orchestrator from file-based session storage to database-backed storage via the Agent Session Manager service.

## Documents

| File | Purpose |
|------|---------|
| `analysis.md` | Detailed analysis with API design, event flow, naming decisions |
| `phase-1-backend-api.md` | Implementation: Backend API endpoints |
| `phase-2-client-library.md` | Implementation: Python client + config |
| `phase-3-command-migration.md` | Implementation: Migrate ao-* commands |
| `phase-4-event-flow.md` | Implementation: Event flow + cleanup |

## Implementation Order

```
Phase 1: Backend API
    ↓
Phase 2: Client Library
    ↓
Phase 3: Command Migration (ao-status, ao-get-result, ao-list-sessions, ao-clean)
    ↓
Phase 4: Event Flow (ao-new, ao-resume, remove observability.py)
```

## Key Decisions

1. **Service name:** Agent Session Manager (not "observability")
2. **Config:** `AGENT_ORCHESTRATOR_SESSION_MANAGER_URL` (required, no enable flag)
3. **API paths:** Unified under `/sessions/*`
4. **Event changes:** `session_start` removed, replaced by `POST /sessions`
5. **Files:** Backup only, API is primary

## How to Use

Give a coding agent ONE phase file at a time. Each phase file contains:
- Overall context
- Prerequisites
- Reference to analysis.md sections
- Specific tasks
- Success criteria
- Verification steps
