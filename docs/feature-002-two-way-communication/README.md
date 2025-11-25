# Feature 002: Two-Way Communication Between Frontend and Agent Sessions

## Overview

Establish bidirectional communication between the unified frontend and running Python AE command processes (ao-new/ao-resume) that host the Claude Agent SDK. This enables critical user control features:

1. **Stop Mechanism**: Ability to halt running agent execution from the frontend
2. **Permission Control**: User approval/denial of tool executions in real-time

## Status

🔍 **Analysis Complete** - Multiple architectural approaches evaluated

**Note**: The file-based approach was initially analyzed but rejected in favor of HTTP-based solutions for production use.

## Key Challenges

### Technical Constraints

- Claude SDK hooks have a 2-second timeout (hard-coded, cannot extend)
- Hooks are observational only - cannot enforce permission decisions
- AE command processes run as detached subprocesses (no direct PID tracking)
- Current architecture is one-way: Backend → Frontend via WebSocket

### User Requirements

- Frontend must be able to stop "runaway" agents
- Users should control which tools are allowed to execute
- Control must reside in the frontend
- Must work within existing architectural constraints

## Architectural Approaches Analyzed

### Stop Mechanism Options

1. **Process Signal (SIGTERM/SIGINT)** - HIGH complexity, MEDIUM feasibility
2. **File Marker Signal** - LOW complexity, HIGH feasibility ✅ **RECOMMENDED**
3. **Hook-Based Interruption** - MEDIUM complexity, MEDIUM feasibility
4. **WebSocket Command Channel** - VERY HIGH complexity, LOW feasibility

### Permission Control Options

1. **Rule-Based Auto-Approval** - Blocked by SDK limitation
2. **Pause-and-Prompt Pattern** - Architecturally incompatible
3. **Pre-Approved Tool Budget** - Too rigid, same SDK limitation
4. **Hybrid Rule-Based + Manual Review Queue** - HIGH complexity, MEDIUM feasibility ✅ **RECOMMENDED**
5. **Extended Hook Timeout** - Not possible (SDK limitation)

## Recommended Solutions

### 1. Stop Mechanism: File Marker Approach

**Implementation Time**: 1-2 days
**Complexity**: LOW
**Feasibility**: HIGH

**How it works**:
- Frontend sends POST `/sessions/{session_id}/stop`
- Backend writes `{session_name}.stop` file
- Agent message loop checks for `.stop` file after each message
- Process exits gracefully when detected

**Trade-offs**:
- 1-2 second detection delay (acceptable)
- Cannot interrupt mid-tool execution (tool completes first)
- Requires polling check (minimal overhead)

### 2. Permission Control: HTTP-Based Request/Response

**Implementation Time**: 2-3 weeks
**Complexity**: MEDIUM
**Feasibility**: HIGH

**Recommended Approach**: Blocking HTTP with Response
- Hook makes blocking HTTP POST to observability backend
- Backend holds request open (async Future pattern)
- Frontend posts decision via separate endpoint
- Backend resolves Future, returns decision to hook
- Hook timeout extended to 30-60 seconds

**Alternative Approaches** (for future consideration):
- Long-Polling Pattern (better resource usage)
- Correlation ID Pattern (most scalable for production)

## Implementation Timeline

### Phase 1: Stop Mechanism (1-2 days)
- Backend endpoint implementation
- Stop detection in agent message loop
- Frontend integration
- Testing

### Phase 2: Permission Control MVP (2-3 weeks)
- Backend infrastructure for approval requests
- Hook implementation with blocking requests
- Frontend approval UI
- Testing

### Phase 3: Permission Control Full (3-4 weeks additional)
- Rule engine for auto-approval
- Rule editor UI in frontend
- Session sync and real-time updates
- Advanced features

**Total Timeline**: 6-8 weeks for complete implementation

## Documents

### Analysis Documents

1. **[ANALYSIS-001-file-based-approach.md](./ANALYSIS-001-file-based-approach.md)**
   Original architecture analysis proposing file-based communication
   **Status**: ❌ Rejected (file-based communication not suitable for stop mechanism)

2. **[ANALYSIS-002-http-based-solutions.md](./ANALYSIS-002-http-based-solutions.md)**
   Comprehensive evaluation of 7 HTTP-based architectural approaches
   **Status**: ✅ Approved (Approach 2: Blocking HTTP recommended for local use case)

### Implementation Plans

**To be created**: Detailed implementation plan based on approved approach

## Key Findings

### Constraints Identified

1. Claude SDK hooks have 2-second timeout (cannot extend)
2. Hooks are observational only (cannot enforce decisions)
3. No SDK pause/resume mechanism exists
4. Current architecture is one-way (backend → frontend)

### Recommended Architecture

```
┌─────────────┐
│  Frontend   │
│  (React)    │
└──────┬──────┘
       │ HTTP POST /stop
       │ HTTP POST /approve
       ▼
┌─────────────────────┐
│ Observability       │
│ Backend (FastAPI)   │
│ - Pending requests  │
│ - Stop signals      │
└──────┬──────────────┘
       │ HTTP (blocking)
       │ File marker
       ▼
┌─────────────────────┐
│ AE Command Process  │
│ - Check .stop file  │
│ - Hook blocks for   │
│   approval          │
└─────────────────────┘
```

## Next Steps

1. ✅ Review and approve HTTP-based approach
2. Create detailed implementation plan (IMPL-002)
3. Implement Phase 1: Stop Mechanism (1-2 days)
4. Validate stop mechanism with users
5. Implement Phase 2: Permission Control MVP (2-3 weeks)
6. Collect usage data and feedback
7. Enhance with full rule engine if needed (3-4 weeks)

## Related Features

- Integrates with observability backend for event tracking
- Works with existing agent session management
- Complements agent manager API for comprehensive agent control
