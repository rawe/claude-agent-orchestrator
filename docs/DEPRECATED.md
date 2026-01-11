# Deprecated Documentation

This file tracks deprecated, superseded, or archived documentation.

## Superseded ADRs

ADRs that have been replaced by newer decisions:

| ADR | Status | Superseded By | Notes |
|-----|--------|---------------|-------|
| [ADR-006](./adr/ADR-006-runner-registration-health-monitoring.md) | Superseded | [ADR-012](./adr/ADR-012-runner-identity-and-registration.md) | Runner identity redesign |
| [ADR-001](./adr/ADR-001-run-session-separation.md) | Partially Superseded | - | Core concepts still valid, some details evolved |

## Archived Documentation

Completed designs and implementation specs moved to archive:

| Document | Archived | Location | Reason |
|----------|----------|----------|--------|
| Rename Session Events to Run Events | 2026-01-06 | [design/archive/](./design/archive/) | Implemented |
| MCP Runner Integration MVP | 2026-01-11 | [architecture/archive/](./architecture/archive/) | Detailed spec superseded by main doc |

## How to Deprecate Documentation

1. **ADRs**: Update the Status field to "Superseded by ADR-XXX" and add entry here
2. **Design Docs**: Move to `design/archive/` when implemented
3. **Architecture Specs**: Move detailed specs to `architecture/archive/` when superseded
4. **Feature Docs**: Update status to "Deprecated" at top of file and add entry here
