# Event Type Naming Consistency

**Status:** Open
**Priority:** Medium
**Created:** 2025-01-02

## Context

The Agent Orchestrator uses an event-driven architecture where components communicate through typed events. A core architectural decision (ADR-001) established the separation between:

- **Sessions** - Persistent records of agent execution history
- **Runs** - Transient, ephemeral execution units within a session

This separation is fundamental to how the system tracks and manages agent execution.

## Problem

The event types `SESSION_START` and `SESSION_STOP` are misnamed. These events actually represent **run lifecycle events**, not session lifecycle events:

- `SESSION_START` is emitted when a run begins execution
- `SESSION_STOP` is emitted when a run completes (success or failure)

This naming:
1. Contradicts ADR-001's Run/Session separation terminology
2. Confuses developers about what these events represent
3. Makes the codebase harder to understand for new contributors

The code already acknowledges this issue with a TODO comment in `servers/agent-coordinator/models.py`:

```python
class SessionEventType(str, Enum):
    """
    TODO: Rename SESSION_START -> RUN_START and SESSION_STOP -> RUN_STOP
    These events are part of our Run API and should reflect that naming.
    """
```

## Proposed Solution

Rename the event types to accurately reflect their purpose:

| Current | Proposed |
|---------|----------|
| `SESSION_START` | `RUN_START` |
| `SESSION_STOP` | `RUN_STOP` |
| `SessionEventType` | `RunEventType` |

This is a breaking change that requires coordinated updates across all components.

## Affected Files

### Backend (Agent Coordinator)
- `servers/agent-coordinator/models.py` - Enum definition
- `servers/agent-coordinator/main.py` - Event handling
- `servers/agent-coordinator/services/callback_processor.py` - Event processing

### Agent Runner
- `servers/agent-runner/lib/session_client.py` - Event emission
- `servers/agent-runner/lib/supervisor.py` - Event handling
- `servers/agent-runner/executors/claude-code/lib/claude_client.py` - Event emission
- `servers/agent-runner/executors/test-executor/ao-test-exec` - Test executor

### Dashboard
- `dashboard/src/types/event.ts` - TypeScript types
- `dashboard/src/utils/constants.ts` - Constants
- `dashboard/src/contexts/SessionsContext.tsx` - Event handling
- `dashboard/src/contexts/ChatContext.tsx` - Event handling
- `dashboard/src/components/features/sessions/EventTimeline.tsx` - Display
- `dashboard/src/components/features/sessions/EventCard.tsx` - Display
- `dashboard/src/services/unifiedViewService.ts` - Service layer
- `dashboard/src/services/unifiedViewTypes.ts` - Types
- `dashboard/src/pages/unified-view/mock-data.ts` - Mock data
- `dashboard/src/pages/unified-view/utils.ts` - Utilities

### Plugins
- `plugins/orchestrator/skills/orchestrator/commands/lib/session_client.py` - Event emission

### Interfaces
- `interfaces/chat-ui/src/types/index.ts` - Types
- `interfaces/chat-ui/src/contexts/ChatContext.tsx` - Event handling

### Documentation
- `docs/components/agent-coordinator/API.md` - API documentation
- `docs/components/agent-coordinator/DATA_MODELS.md` - Data model docs
- `docs/components/agent-coordinator/DATABASE_SCHEMA.md` - Schema docs
- `docs/components/agent-coordinator/USAGE.md` - Usage examples
- `docs/adr/ADR-003-callback-based-async.md` - ADR reference
- `docs/features/agent-callback-architecture.md` - Feature docs
- `docs/features/session-stop-integration-todo.md` - Integration docs
- `docs/features/unified-session-run-view.md` - Feature docs
- `docs/features/approaches/*.md` - Implementation approaches

### Tests
- `tests/integration/01-basic-session-start.md` - Test case
- `tests/integration/02-session-resume.md` - Test case
- `tests/integration/03-session-with-agent.md` - Test case
- `tests/integration/04-child-agent-sync.md` - Test case
- `tests/integration/06-concurrent-callbacks.md` - Test case

**Total: ~40 files**

## Implementation Strategy

Given the scope, consider a phased approach:

### Phase 1: Add Aliases (Non-breaking)
1. Add `RUN_START` and `RUN_STOP` as aliases in the enum
2. Update documentation to prefer new names
3. Log deprecation warnings when old names are used

### Phase 2: Migrate Components
1. Update Agent Runner to emit new event names
2. Update Dashboard to handle both (backward compatible)
3. Update Plugins and Interfaces

### Phase 3: Remove Old Names (Breaking)
1. Remove deprecated aliases
2. Update all remaining references
3. Final documentation cleanup

## Acceptance Criteria

- [ ] `RUN_START` and `RUN_STOP` are the canonical event type names
- [ ] All code references use the new names
- [ ] All documentation uses the new names
- [ ] No TODO comments remain about this rename
- [ ] ADR-001 terminology is consistently applied
