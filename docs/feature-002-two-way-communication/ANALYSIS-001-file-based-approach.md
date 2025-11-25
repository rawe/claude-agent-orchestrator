# Two-Way Communication Architecture Analysis

**Date**: November 25, 2025
**Author**: Technical Analysis Report
**Project**: Agent Orchestrator - Two-Way Communication Implementation
**Version**: 1.0

---

## Executive Summary

This document provides a comprehensive architectural analysis of the Agent Orchestrator system, from Python AE commands through the observability backend to the unified frontend, with specific focus on implementing two-way communication for:

1. **Stop Mechanism**: Ability to halt running agents from the frontend
2. **Fine-Grained Permission Control**: User control over tool execution approvals

### Key Findings

- **Current Architecture**: One-way communication (backend → frontend via WebSocket)
- **Stop Mechanism**: **FEASIBLE** - File-based signal approach (2-4 days implementation)
- **Permission Control**: **PARTIALLY FEASIBLE** - Rule-based system with async review (5-7 weeks implementation)
- **Primary Constraint**: Claude SDK hooks have 2-second timeout, cannot enforce permission decisions
- **Recommended Approaches**: File-marker stop signal + Hybrid rule-based permission system

---

## Table of Contents

1. [Current Architecture Overview](#1-current-architecture-overview)
2. [Data Flow Analysis](#2-data-flow-analysis)
3. [WebSocket Event System](#3-websocket-event-system)
4. [Stop Mechanism Analysis](#4-stop-mechanism-analysis)
5. [Fine-Grained Permission Control Analysis](#5-fine-grained-permission-control-analysis)
6. [Implementation Recommendations](#6-implementation-recommendations)
7. [Technical Specifications](#7-technical-specifications)
8. [Risk Analysis](#8-risk-analysis)
9. [Appendices](#9-appendices)

---

## 1. Current Architecture Overview

### 1.1 System Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND LAYER                                │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Unified Frontend (React + TypeScript)                       │   │
│  │  - Port: 3000/5173                                           │   │
│  │  - WebSocket Client (ws://localhost:8765/ws)                 │   │
│  │  - State Management: Context API + Custom Hooks             │   │
│  │  - Real-time Event Display                                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                  ▲
                                  │ WebSocket (one-way push)
                                  │ HTTP REST (requests)
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    OBSERVABILITY BACKEND LAYER                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  FastAPI Server (Port 8765)                                  │   │
│  │  - POST /events (receive from hooks)                         │   │
│  │  - WebSocket /ws (broadcast to frontends)                    │   │
│  │  - SQLite Database (sessions, events)                        │   │
│  │  - In-memory WebSocket connection pool                       │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                  ▲
                                  │ HTTP POST (events from hooks)
                                  │
┌─────────────────────────────────────────────────────────────────────┐
│                    AGENT ORCHESTRATION LAYER                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  MCP Server (agent-orchestrator-mcp.py)                      │   │
│  │  - Tools: start_agent_session, resume_agent_session, ...    │   │
│  │  - Executes AE commands via subprocess                       │   │
│  │  - Async/blocking modes                                      │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Python AE Commands (UV Scripts)                             │   │
│  │  - ao-new: Create new session                                │   │
│  │  - ao-resume: Resume session                                 │   │
│  │  - ao-status: Check session status                           │   │
│  │  - Shared libraries: config, session, agent, claude_client   │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ Claude SDK Integration
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     CLAUDE CODE AGENT SESSION                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  ClaudeSDKClient (claude-agent-sdk)                          │   │
│  │  - Programmatic hooks: UserPromptSubmit, PostToolUse         │   │
│  │  - Message streaming to JSONL                                │   │
│  │  - Session ID management                                     │   │
│  │  - Tool execution                                            │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Observability Hooks (Python Scripts)                        │   │
│  │  - user_prompt_submit_hook.py                                │   │
│  │  - post_tool_hook.py                                         │   │
│  │  - Timeout: 2 seconds (hard constraint)                      │   │
│  │  - Silent failure pattern                                    │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Key Technologies

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Frontend | React | 18.3.1 | UI framework |
| Frontend | TypeScript | 5.6.2 | Type safety |
| Frontend | Vite | 6.0.5 | Build tool |
| Frontend | Tailwind CSS | 3.4.17 | Styling |
| Backend | FastAPI | ≥0.104.0 | API server |
| Backend | Uvicorn | ≥0.24.0 | ASGI server |
| Backend | SQLite | 3.x | Database |
| Backend | WebSocket | Native | Real-time events |
| Orchestration | Python | 3.11+ | AE commands |
| Orchestration | UV | Latest | Python script runner |
| Orchestration | Claude SDK | Latest | Agent integration |

### 1.3 Current Data Flow (One-Way)

```
Agent Session → Hooks → Observability Backend → WebSocket → Frontend
                   ↓
            (2s timeout)
                   ↓
          HTTP POST /events
                   ↓
         SQLite DB (persist)
                   ↓
    Broadcast to all connected clients
                   ↓
         Frontend receives & displays
```

**Key Characteristics**:
- **One-way communication**: Backend pushes events to frontend
- **No feedback loop**: Frontend cannot send commands back to running agents
- **Silent failure**: Hooks never block agent execution
- **Real-time updates**: WebSocket provides instant event delivery
- **Persistence**: All events stored in SQLite for historical queries

---

## 2. Data Flow Analysis

### 2.1 Session Creation Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. MCP Tool Call: start_agent_session(session_name, agent, prompt)  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. MCP Server: execute_script_async() or execute_script()           │
│    - Builds command: ao-new session-name --agent agent -p "prompt"  │
│    - Spawns subprocess with start_new_session=True (detached)       │
│    - Returns immediately if async mode                              │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. ao-new Command                                                    │
│    - load_config(): Get project_dir, sessions_dir, agents_dir       │
│    - validate_session_name(): Check format and length               │
│    - save_session_metadata(): STAGE 1 - Create .meta.json           │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. run_claude_session() - Async SDK Integration                     │
│    Step 1: Initialize ClaudeSDKClient with options                  │
│    Step 2: Register programmatic hooks                              │
│    Step 3: Write user message to .jsonl                             │
│    Step 4: Stream messages from SDK                                 │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. Message Loop (lines 157-229, claude_client.py)                   │
│    For each message in client.receive_response():                   │
│      - Write message to .jsonl file                                 │
│      - Extract session_id from SystemMessage                        │
│      - update_session_id(): STAGE 2 - Add session_id to .meta.json │
│      - Send metadata to observability backend                       │
│      - Extract result from ResultMessage                            │
│      - Send events to observability                                 │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 6. Hook Execution (Parallel to message loop)                        │
│    UserPromptSubmit Hook:                                           │
│      - Sends session_start event (fallback for SDK limitation)      │
│      - Sends user message with role="user"                          │
│    PostToolUse Hook:                                                │
│      - Sends tool execution data (name, input, output, error)       │
│    Timeout: 2 seconds per hook                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 7. Observability Backend: POST /events                              │
│    - Validate event data (Pydantic model)                           │
│    - Special handling:                                              │
│      * session_start: Create session in DB                          │
│      * session_stop: Update session status to "finished"            │
│    - Insert event into SQLite                                       │
│    - Broadcast to all WebSocket clients                             │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 8. Frontend: WebSocket Message Handler                              │
│    - Parse JSON message                                             │
│    - Broadcast to all subscribers (observer pattern)                │
│    - useSessions() hook: Update session list                        │
│    - useSessionEvents() hook: Append to event list                  │
│    - UI re-renders with new data                                    │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Session Resumption Flow

```
ao-resume session-name -p "continuation"
    ↓
load_session_metadata() → Extract session_id from .meta.json
    ↓
load_agent_config() → Load agent if session has one
    ↓
run_session_sync(..., resume_session_id=session_id)
    ↓
ClaudeSDKClient.resume = session_id
    ↓
Stream messages, append to .jsonl
    ↓
Send events (NO session_start since resuming)
    ↓
update_session_metadata() → Update last_resumed_at
```

### 2.3 Event Types and Flow

| Event Type | Source | Destination | Purpose |
|-----------|--------|-------------|---------|
| `session_start` | UserPromptSubmit hook | Observability Backend | Mark session beginning |
| `user` | UserPromptSubmit hook | Observability Backend | Capture user prompts |
| `message` | Message loop | Observability Backend | Assistant responses |
| `post_tool` | PostToolUse hook | Observability Backend | Tool execution logs |
| `session_stop` | Message loop end | Observability Backend | Mark session completion |
| `init` | WebSocket connection | Frontend | Initial state sync |
| `event` | Event endpoint | Frontend | Real-time event broadcast |
| `session_updated` | Metadata update | Frontend | Session metadata changes |
| `session_deleted` | Delete endpoint | Frontend | Session removal notification |

### 2.4 File System Structure

**Session Files** (`.agent-orchestrator/sessions/`):
```
{session_name}.meta.json   - Metadata (session_id, agent, timestamps)
{session_name}.jsonl       - Event stream (all messages chronologically)
{session_name}.log         - Execution log (optional, if logging enabled)
```

**Agent Files** (`agents/{agent_name}/`):
```
agent.json                 - Agent configuration (name, description)
agent.system-prompt.md     - System prompt text
agent.mcp.json            - MCP server configuration
```

**Database Files**:
```
.agent-orchestrator/observability.db  - Sessions and events
```

---

## 3. WebSocket Event System

### 3.1 WebSocket Server Implementation

**File**: `agent-orchestrator-observability/backend/main.py`

**Endpoint**: `WebSocket /ws` (lines 162-180)

**Connection Management**:
```python
connections: set[WebSocket] = set()  # In-memory connection pool

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.add(websocket)

    # Send initial state
    sessions = get_sessions()
    await websocket.send_text(json.dumps({
        "type": "init",
        "sessions": sessions
    }))

    try:
        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connections.discard(websocket)
```

**Broadcasting Pattern**:
```python
# Used in POST /events, PATCH /sessions, DELETE /sessions
for ws in connections.copy():
    try:
        await ws.send_text(message)
    except:
        connections.discard(ws)  # Remove failed connections
```

### 3.2 Frontend WebSocket Client

**File**: `agent-orchestrator-frontend/src/contexts/WebSocketContext.tsx`

**Key Features**:
- Lazy initialization on provider mount
- Automatic reconnection with exponential backoff
- Delays: `[1s, 2s, 4s, 8s, 16s, 30s]`
- Observer pattern for message distribution

**Subscription Pattern**:
```typescript
const subscribersRef = useRef<Set<(message: WebSocketMessage) => void>>(new Set());

// Subscribe to messages
const subscribe = useCallback((callback: (message: WebSocketMessage) => void) => {
  subscribersRef.current.add(callback);
  return () => subscribersRef.current.delete(callback);  // Unsubscribe
}, []);

// Broadcast to all subscribers
ws.onmessage = (event) => {
  const message: WebSocketMessage = JSON.parse(event.data);
  subscribersRef.current.forEach((callback) => callback(message));
};
```

### 3.3 Message Types

```typescript
interface WebSocketMessage {
  type: 'init' | 'event' | 'session_updated' | 'session_deleted';
  sessions?: Session[];        // For 'init'
  data?: SessionEvent;         // For 'event'
  session?: Session;           // For 'session_updated'
  session_id?: string;         // For 'session_deleted'
}
```

### 3.4 Frontend Integration

**Hook: useSessions()** (`/src/hooks/useSessions.ts`):
```typescript
// Subscribe to WebSocket messages
useEffect(() => {
  const unsubscribe = subscribe((message: WebSocketMessage) => {
    switch (message.type) {
      case 'init':
        setSessions(message.sessions || []);
        break;
      case 'session_updated':
        // Update specific session in state
        break;
      case 'session_deleted':
        // Remove session from state
        break;
      case 'event':
        // Handle session_start, session_stop events
        break;
    }
  });

  return unsubscribe;
}, [subscribe]);
```

**Hook: useSessionEvents()** (`/src/hooks/useSessions.ts`):
```typescript
// Subscribe to events for specific session
useEffect(() => {
  const unsubscribe = subscribe((message: WebSocketMessage) => {
    if (message.type === 'event' && message.data?.session_id === sessionId) {
      // Deduplicate using getEventKey()
      setEvents(prev => {
        const key = getEventKey(message.data);
        if (prev.some(e => getEventKey(e) === key)) return prev;
        return [...prev, message.data];
      });
    }
  });

  return unsubscribe;
}, [subscribe, sessionId]);
```

### 3.5 Limitations of Current WebSocket System

**One-Way Communication**:
- Backend receives no messages from frontend via WebSocket
- Frontend-to-backend communication uses HTTP REST API only
- WebSocket receive loop exists but discards all client messages

**No Bidirectional Capability**:
- Current design: Backend → Frontend (events)
- Not designed for: Frontend → Backend (commands)
- Would require architectural changes to support command channel

---

## 4. Stop Mechanism Analysis

### 4.1 Problem Statement

**User Requirement**: Ability to stop a running agent from the frontend when it goes "havoc" (misbehaves, infinite loop, stuck).

**Current State**:
- No stop mechanism exists
- Frontend has placeholder: `stopSession()` in `sessionService.ts` (lines 44-56) - currently mocked
- Backend has no `/sessions/{session_id}/stop` endpoint
- Running agents are detached processes (no PID tracking)

### 4.2 Evaluated Approaches

#### Approach 1: Process Signal (SIGTERM/SIGINT)

**How It Works**:
1. Frontend sends POST `/sessions/{session_id}/stop`
2. Backend finds PID of running Claude process
3. Send SIGTERM or SIGINT to terminate

**Pros**:
- Immediate termination
- Works for truly stuck processes
- Standard Unix pattern

**Cons**:
- **PID not stored** in current system
- Processes spawned with `start_new_session=True` (detached)
- Would need major refactoring:
  - Store PID in session metadata
  - Query process table on stop request
  - Handle stale PIDs
  - Platform-specific signal handling
- Hard to distinguish graceful stop from kill
- May leave resources in inconsistent state

**Complexity**: HIGH
**Implementation Effort**: 5-7 days
**Feasibility**: MEDIUM
**Recommended**: ❌

---

#### Approach 2: File Marker Signal (RECOMMENDED)

**How It Works**:
1. Frontend sends POST `/sessions/{session_id}/stop`
2. Backend writes `{session_name}.stop` file to sessions directory
3. AE commands or hooks periodically check for `.stop` file
4. Process exits gracefully when detected

**Pros**:
- **Minimal implementation** (1-2 days)
- Leverages existing file-based session system
- No process tracking needed
- Cross-platform compatible
- Graceful shutdown possible
- Frontend skeleton already exists

**Cons**:
- **Polling overhead** (check every tool call)
- **Timing**: May take seconds to detect
- Cannot interrupt mid-tool execution
- Waits for current tool to complete

**Complexity**: LOW
**Implementation Effort**: 1-2 days
**Feasibility**: HIGH
**Recommended**: ✅ BEST CHOICE

**Implementation Plan**:

**Phase 1: Backend Endpoint** (30 minutes)
```python
# File: agent-orchestrator-observability/backend/main.py

@app.post("/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    """Stop a running session"""
    # Get session from DB to find session_name
    sessions = get_sessions()
    session = next((s for s in sessions if s['session_id'] == session_id), None)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session_name = session['session_name']
    sessions_dir = Path(".agent-orchestrator/sessions")

    # Write stop marker file
    stop_file = sessions_dir / f"{session_name}.stop"
    stop_file.write_text(json.dumps({
        "stopped_at": datetime.now(UTC).isoformat(),
        "stop_requested_by": "user"
    }))

    # Update status to "stopping"
    update_session_status(session_id, "stopping")

    # Broadcast to WebSocket clients
    message = json.dumps({
        "type": "session_stopping",
        "session_id": session_id
    })
    for ws in connections.copy():
        try:
            await ws.send_text(message)
        except:
            connections.discard(ws)

    return {"ok": True, "message": "Stop requested"}
```

**Phase 2: Stop Detection in Agent** (2-3 hours)
```python
# File: plugins/agent-orchestrator/.../lib/claude_client.py

async def _check_stop_requested(session_name: str, sessions_dir: Path) -> bool:
    """Check if stop has been requested via marker file"""
    stop_file = sessions_dir / f"{session_name}.stop"
    return stop_file.exists()

# In run_claude_session(), add to message loop:
async for message in client.receive_response():
    # ... existing code to process message ...

    # Check for stop request after each message
    if session_name and sessions_dir:
        if await _check_stop_requested(session_name, sessions_dir):
            # Clean up stop file
            stop_file = sessions_dir / f"{session_name}.stop"
            stop_file.unlink(missing_ok=True)

            # Send final session_stop event
            if observability_enabled and session_id:
                send_session_stop(
                    get_observability_url(),
                    session_id,
                    exit_code=130,  # SIGINT exit code
                    reason="stopped_by_user"
                )

            # Exit message loop gracefully
            break
```

**Phase 3: Frontend Integration** (1 hour)
```typescript
// File: agent-orchestrator-frontend/src/services/sessionService.ts

export const stopSession = async (sessionId: string): Promise<{ success: boolean; message: string }> => {
  try {
    const response = await observabilityApi.post(`/sessions/${sessionId}/stop`);
    return response.data;
  } catch (error) {
    console.error('Failed to stop session:', error);
    throw error;
  }
};
```

**Phase 4: UI Updates** (1 hour)
- Add "Stop" button to session details page
- Show "Stopping..." state during request
- Listen for `session_stop` event from backend
- Update UI when session actually stops

**Total Timeline**: 1-2 days

**Edge Cases**:
- Stop file created but process already finished → Safe, just cleanup
- Stop file created while tool executing → Tool completes, then checks
- Multiple stop requests → Idempotent (file already exists)
- Stale stop files from crashes → Cleanup on session start

---

#### Approach 3: Hook-Based Interruption

**How It Works**:
1. Frontend sends request to observability backend
2. Backend stores "stop_requested" flag in session record
3. PostToolUse hook (2-second timeout) checks flag
4. Hook returns special signal to interrupt
5. Process catches signal and exits

**Pros**:
- Leverages existing hook infrastructure
- Can interrupt between tool calls

**Cons**:
- **2-second hook timeout** is critical constraint
- Only interrupts BETWEEN tools
- **Hook cannot enforce decision** - SDK limitation
- No documented way for hook to signal "stop execution"

**Complexity**: MEDIUM
**Implementation Effort**: 3-4 days
**Feasibility**: MEDIUM
**Recommended**: 🟡 (Secondary option)

---

#### Approach 4: WebSocket Command Channel

**How It Works**:
1. Add bidirectional WebSocket support
2. Frontend sends stop command via WebSocket
3. Backend propagates to running process
4. Process receives and exits

**Pros**:
- Real-time bidirectional communication
- No polling needed

**Cons**:
- **Over-engineered** for stop functionality
- WebSocket already exists (one-way only)
- Difficult to bridge WebSocket to detached process
- High complexity for minimal benefit

**Complexity**: VERY HIGH
**Implementation Effort**: 7-10 days
**Feasibility**: LOW
**Recommended**: ❌

---

### 4.3 Recommendation: File Marker Approach

**Why This Approach**:
1. **Lowest implementation effort** (1-2 days)
2. **Uses existing infrastructure** (file-based sessions)
3. **Highest reliability** (simple mechanism, fewer edge cases)
4. **Cross-platform compatible**
5. **Graceful shutdown** (allows cleanup)
6. **Frontend skeleton exists** (placeholder already created)

**Acceptable Trade-offs**:
- 1-2 second delay before detection (acceptable for stop use case)
- Cannot interrupt mid-tool (tool completes first, then stops)
- Requires polling check (minimal overhead at each message)

**Alternative Enhancement**:
Combine with PostToolUse hook check as secondary mechanism:
- Primary: File marker check in message loop
- Secondary: PostToolUse hook also checks file marker
- Result: Stop detected between tool calls (faster response)

---

## 5. Fine-Grained Permission Control Analysis

### 5.1 Problem Statement

**User Requirement**: Frontend-controlled permission system where:
- Users can approve/deny tool executions
- Users can create rules for which tools are allowed
- Control must reside in the frontend
- Must work within hook timeout constraints (2 seconds)

**Current State**:
- Static permission config in `.claude/settings.json`
- `permission_mode="bypassPermissions"` (all tools allowed)
- PreToolUse hook exists but is **disabled** (line 110, claude_client.py)
- Hooks have 2-second timeout
- No frontend permission UI

### 5.2 The Core Challenge

**Timing Constraint**:
- PreToolUse hook has 2-second timeout (hard-coded, cannot extend)
- Direct user interaction (click approve/deny) takes >2 seconds
- Need solution that provides frontend control while respecting timeout

**SDK Limitation**:
- **Critical Finding**: Hooks cannot enforce permission decisions
- Hooks are observational only (event capture)
- No documented SDK mechanism for hooks to block/allow tools
- Hook return value does not control tool execution

**Evidence**:
```python
# Current hook implementation (observability.py, line 270)
def post_tool_hook(...):
    # ... process tool data ...
    send_post_tool(url, session_id, ...)  # Send event to backend
    sys.exit(0)  # Always exit successfully (observational only)
```

### 5.3 Evaluated Approaches

#### Approach A: Rule-Based Auto-Approval

**How It Works**:
- Frontend maintains permission rules database
- Rules synced to backend or session storage
- PreToolUse hook queries rules and makes instant decision
- Frontend UI for creating/editing rules

**Example Rules**:
```json
{
  "id": "rule-1",
  "pattern": {
    "tool_name": "Bash",
    "parameters": { "command": "npm run *" }
  },
  "decision": "allow",
  "reason": "Allow npm scripts"
}
```

**Pros**:
- Rule evaluation fits within 2-second timeout
- Fast decisions (no user interaction needed)
- Frontend controls rule creation

**Cons**:
- **Cannot enforce decisions** (hook limitation)
- Hook can only log approval/denial, not block tool
- Rules are observational, not preventive

**Complexity**: MEDIUM
**Feasibility**: 3/10 (blocked by SDK limitation)
**Recommended**: ❌

---

#### Approach B: Pause-and-Prompt Pattern

**How It Works**:
1. PreToolUse hook writes pending request to file/DB
2. Frontend polls for pending requests
3. User approves/denies in UI
4. Hook waits for decision
5. Session resumes based on decision

**Pros**:
- Direct user control
- Approval UI in frontend

**Cons**:
- **Cannot pause hook** (SDK doesn't support)
- **2-second timeout** insufficient for user interaction
- **No SDK pause/resume API** documented
- Agent doesn't wait for hook completion

**Complexity**: VERY HIGH
**Feasibility**: 1/10 (architecturally incompatible)
**Recommended**: ❌

---

#### Approach C: Pre-Approved Tool Budget

**How It Works**:
- Frontend pre-approves tools at session start
- Approval stored in session config
- Hook checks pre-approval list instantly
- Frontend can modify list mid-session

**Pros**:
- Pre-approval lookup fits within timeout
- Frontend controls approval list

**Cons**:
- **Same blocker as Approach A** (cannot enforce)
- Too rigid (doesn't help with unexpected tools)
- Pre-approval too broad for granular control

**Complexity**: MEDIUM
**Feasibility**: 3/10 (same SDK limitation)
**Recommended**: ❌

---

#### Approach D: Hybrid Rule-Based + Manual Review Queue (RECOMMENDED)

**How It Works**:

**Phase 1 - Default (Rule-Based)**:
- Frontend maintains rule database
- Hook matches request against rules (<100ms)
- If rule matches → log as approved (observational)
- If no rule matches → log to review queue

**Phase 2 - On Mismatch (Manual Review)**:
- Tool execution happens (hook cannot prevent)
- Event logged to observability backend
- Frontend shows pending review in dashboard
- User reviews and creates rule for future

**Phase 3 - Next Time (Rule Applied)**:
- User creates rule for this tool pattern
- Rule stored in frontend + synced to backend
- Next execution → approved instantly by rule

**Architecture**:
```
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (React)                            │
│  ┌──────────────┐        ┌──────────────────┐                   │
│  │ Rule Editor  │◄───────┤ Permission Rules │                   │
│  │    (UI)      │        │  (localStorage)  │                   │
│  └──────────────┘        └──────────────────┘                   │
│         ▲                         │                              │
│         │                         ▼                              │
│         │                 ┌──────────────────┐                  │
│         │                 │   Rule Database  │                  │
│         │                 │  (IndexedDB/SQL) │                  │
│         │                 └──────────────────┘                  │
│         │                         │                              │
│  ┌─────────────────────┐         ▼                              │
│  │  Review Queue       │  ┌────────────────────┐                │
│  │  (Pending Approvals)│  │  Session Details   │                │
│  └─────────────────────┘  └────────────────────┘                │
└─────────────────────────────────────────────────────────────────┘
                     ▲                              │
                     │ WebSocket                    │ HTTP API
                     │                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              OBSERVABILITY BACKEND (FastAPI)                     │
│  ┌──────────────────┐         ┌──────────────────────┐          │
│  │  Review Queue    │         │  Rule Sync Endpoint │          │
│  │  (Pending logs)  │         │  (GET/POST rules)   │          │
│  └──────────────────┘         └──────────────────────┘          │
│                                                                   │
│  SQLite: sessions, events, rules, decisions                      │
└─────────────────────────────────────────────────────────────────┘
                     ▲
                     │ Hook Output
┌─────────────────────────────────────────────────────────────────┐
│               CLAUDE CODE AGENT SESSION                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  PreToolUse Hook                                          │  │
│  │  1. Load rules from config file                           │  │
│  │  2. Match tool against rules (<100ms)                     │  │
│  │  3. If match: log "approved"                              │  │
│  │     If no match: log "pending_review"                     │  │
│  │  4. Send event to observability                           │  │
│  │  5. Return success (tool executes regardless)             │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Rule Schema**:
```json
{
  "id": "uuid",
  "session_id": "session-id",
  "created_at": "2025-11-25T...",
  "enabled": true,
  "pattern": {
    "tool_name": "Bash|Read|Write|*",
    "parameters": {
      "command": "npm run *|grep *",
      "file_path": "*.md|*.py|*"
    }
  },
  "decision": "allow",  // "allow" | "deny" | "ask"
  "reason": "User-created rule for npm scripts"
}
```

**Pending Review Event**:
```json
{
  "event_type": "tool_pending_review",
  "session_id": "session-id",
  "tool_use_id": "uuid",
  "timestamp": "2025-11-25T...",
  "tool_name": "Bash",
  "tool_input": { "command": "npm run build" },
  "status": "pending",
  "user_decision": null,
  "decision_timestamp": null
}
```

**UX Flow - Known Tool (Rule Exists)**:
```
Claude Code → Tool Call: Bash("npm run build")
    ↓
PreToolUse Hook
    ↓
Load rules from .agent-orchestrator/sessions/{session}.rules.json
    ↓
Match "npm run build" against rules
    ↓
Rule Found: "Allow npm scripts" ✓
    ↓
Log: { event_type: "pre_tool", status: "approved", rule_id: "uuid" }
    ↓
Tool Executes Normally (hook cannot prevent)
    ↓
Frontend sees approval (no action needed)
```

**UX Flow - Unknown Tool (No Rule)**:
```
Claude Code → Tool Call: Bash("some-unknown-command")
    ↓
PreToolUse Hook
    ↓
Load rules
    ↓
No matching rule
    ↓
Log: { event_type: "tool_pending_review", status: "pending" }
    ↓
Tool Executes (hook cannot prevent)
    ↓
Frontend receives pending_review event via WebSocket
    ↓
Dashboard shows: "New Tool Pending Review: Bash (some-unknown-command)"
    ↓
User reviews:
   Option A: Click "Approve" → Creates rule for this pattern
   Option B: Click "Create Rule" → Opens rule editor
   Option C: Dismiss → Stays in pending queue
    ↓
Next time same tool is called → Rule matches → Approved instantly
```

**Pros**:
- **Respects 2-second timeout** (rule evaluation <100ms)
- **Frontend controls rules** (creation/management UI)
- **Observational logging** (hook can log without enforcing)
- **Async review** (approval outside hook timeout)
- **Learning system** (rules improve over time)
- **Fallback handling** (unknown tools handled via review)

**Cons**:
- **Cannot prevent first execution** (SDK limitation)
- Tool runs first time before approval
- Requires user to review and create rules
- More complex than simple approve/deny

**Complexity**: HIGH
**Implementation Effort**: 5-7 weeks
**Feasibility**: 8/10
**Recommended**: ✅ BEST FEASIBLE OPTION

**Why This Works**:
1. Accepts SDK limitation (hooks are observational)
2. Provides frontend control via rule creation
3. Rules enable instant decisions (within timeout)
4. Async review for unknown tools
5. Learning system improves with use
6. Pragmatic approach respecting constraints

---

#### Approach E: Extended Hook Timeout

**Investigation**:
- Checked SDK documentation and code
- Timeout is hard-coded at 2000ms
- No API parameter to extend timeout
- No async hook support documented

**Complexity**: N/A
**Feasibility**: 0/10 (not possible)
**Recommended**: ❌

---

### 5.4 Recommendation: Hybrid Rule-Based + Review Queue

**Implementation Phases**:

**Phase 1: Backend Infrastructure** (1-2 weeks)
- Add SQLite tables: `permission_rules`, `tool_decisions`, `rule_versions`
- Add FastAPI endpoints:
  - `POST /sessions/{session_id}/rules` - Create rule
  - `GET /sessions/{session_id}/rules` - List rules
  - `PUT /rules/{rule_id}` - Update rule
  - `DELETE /rules/{rule_id}` - Delete rule
  - `GET /sessions/{session_id}/pending-reviews` - Get pending
  - `POST /tool-decisions/{tool_use_id}/approve` - Approve tool
  - `POST /tool-decisions/{tool_use_id}/deny` - Deny tool
- Update event schema with decision tracking

**Phase 2: Hook Implementation** (1 week)
- Enable PreToolUse hook in claude_client.py (currently disabled at line 110)
- Implement rule matcher logic
- Load rules from session config file
- Log decisions to observability backend
- Optimize for <100ms execution time

**Phase 3: Frontend UI** (2-3 weeks)
- New page: "Permission Rules"
  - List all rules
  - Edit/delete rules
  - Create new rules with pattern builder
  - Rule templates for common scenarios
- New widget: "Pending Reviews"
  - Dashboard card showing pending decisions
  - Quick approve/deny buttons
  - Create rule from decision option
- Session details enhancement
  - Show which rules applied
  - Statistics: approved, denied, pending

**Phase 4: Session Sync** (1 week)
- On session start: Fetch rules, write to `.rules.json`
- During session: Sync rule changes to backend
- Real-time rule updates

**Total Timeline**: 5-7 weeks

**Key Trade-offs**:
- **Cannot prevent first execution** (SDK limitation)
- **Post-execution approval** (tool runs, then user reviews)
- **Rule creation required** (not instant approve/deny)

**Why These Trade-offs Are Acceptable**:
1. Rules created within seconds
2. Second occurrence prevented
3. Learning system improves over time
4. Respects SDK architectural constraints
5. Provides frontend control (primary requirement)

---

### 5.5 Alternative: MVP (Lighter Version)

If full implementation too heavy:

**Minimum Viable Product** (2-3 weeks):
1. Backend: Single table `tool_decisions` for pending reviews
2. Hook: Log all tool calls (no rule evaluation)
3. Frontend: Simple list of "Pending Tool Approvals"
4. No rule engine, just manual per-tool approval

**Advantages**:
- Faster implementation (2-3 weeks vs 5-7 weeks)
- Simpler backend logic
- Still provides frontend visibility

**Disadvantages**:
- Every tool needs manual review (not ideal)
- No learning/automation
- Higher user friction

**Upgrade Path**:
- Validate MVP with users
- Add rule engine later if needed

---

## 6. Implementation Recommendations

### 6.1 Priority and Sequencing

**Recommended Implementation Order**:

1. **Stop Mechanism** (1-2 days)
   - Simpler to implement
   - High user value (immediate need)
   - Low risk
   - No SDK limitations

2. **Permission Control MVP** (2-3 weeks)
   - Test user interest
   - Validate observational approach
   - Collect real usage data

3. **Permission Control Full** (additional 3-4 weeks)
   - Add rule engine
   - Add rule editor UI
   - Add learning features

**Total Timeline**:
- **Phase 1** (Stop): 1-2 days
- **Phase 2** (Permission MVP): 2-3 weeks
- **Phase 3** (Permission Full): 3-4 weeks
- **Total**: ~6-8 weeks for complete implementation

### 6.2 Stop Mechanism Implementation

**File**: `docs/STOP_MECHANISM_IMPLEMENTATION.md` (create separately)

**Quick Reference**:

1. **Backend Endpoint** (30 min)
   - Create `POST /sessions/{session_id}/stop`
   - Write `.stop` file to sessions directory
   - Update session status to "stopping"
   - Broadcast via WebSocket

2. **Stop Detection** (2-3 hours)
   - Add `_check_stop_requested()` function
   - Call in message loop after each message
   - Clean up `.stop` file when detected
   - Send `session_stop` event

3. **Frontend Integration** (1 hour)
   - Update `sessionService.stopSession()`
   - Add "Stop" button to session UI
   - Show "Stopping..." state
   - Listen for `session_stop` event

4. **Testing** (3-4 hours)
   - Happy path: Stop running session
   - Edge cases: Already stopped, multiple requests
   - Timing: Verify 1-2 second detection
   - Cleanup: Verify `.stop` file removed

**Total**: 1-2 days

### 6.3 Permission Control Implementation

**File**: `docs/PERMISSION_CONTROL_IMPLEMENTATION.md` (create separately)

**Quick Reference**:

**MVP Version** (2-3 weeks):

1. **Backend** (1 week)
   - Table: `tool_decisions`
   - Endpoints: GET pending, POST approve/deny
   - Event: `tool_pending_review`

2. **Hook** (2 days)
   - Enable PreToolUse hook
   - Log all tools as "pending_review"
   - Send to observability backend

3. **Frontend** (1 week)
   - Page: "Pending Tool Approvals"
   - Widget: Review queue in dashboard
   - Actions: Approve/Deny buttons

**Full Version** (additional 3-4 weeks):

4. **Rule Engine** (1-2 weeks)
   - Table: `permission_rules`
   - Rule matcher algorithm
   - Rule evaluation in hook

5. **Rule Editor UI** (2 weeks)
   - Page: "Permission Rules"
   - Component: Rule pattern builder
   - Templates: Common rule patterns

6. **Integration** (3-4 days)
   - Session config sync
   - Real-time rule updates
   - Statistics and metrics

### 6.4 Database Schema Extensions

**For Stop Mechanism**:
```sql
-- Extend sessions table
ALTER TABLE sessions ADD COLUMN stopped_at TEXT;
ALTER TABLE sessions ADD COLUMN stop_reason TEXT;
```

**For Permission Control**:
```sql
-- New tables
CREATE TABLE permission_rules (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    tool_name_pattern TEXT NOT NULL,
    parameter_patterns TEXT,  -- JSON
    decision TEXT NOT NULL,  -- allow, deny, ask
    reason TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE TABLE tool_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_use_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    tool_input TEXT,  -- JSON
    timestamp TEXT NOT NULL,
    status TEXT NOT NULL,  -- pending, approved, denied
    rule_id TEXT,
    user_decision TEXT,
    decision_timestamp TEXT,
    decision_notes TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
    FOREIGN KEY (rule_id) REFERENCES permission_rules(id)
);

CREATE INDEX idx_tool_decisions_session ON tool_decisions(session_id);
CREATE INDEX idx_tool_decisions_status ON tool_decisions(status);
CREATE INDEX idx_rules_session ON permission_rules(session_id);
```

### 6.5 API Specifications

**Stop Mechanism**:
```
POST /sessions/{session_id}/stop

Request: (empty body)
Response: { "ok": true, "message": "Stop requested" }
Error: 404 if session not found
```

**Permission Control**:
```
POST /sessions/{session_id}/rules
Body: { "pattern": {...}, "decision": "allow", "reason": "..." }
Response: { "id": "uuid", ... }

GET /sessions/{session_id}/rules
Response: { "rules": [...] }

GET /sessions/{session_id}/pending-reviews
Response: { "pending": [...] }

POST /tool-decisions/{tool_use_id}/approve
Body: { "create_rule": true, "rule": {...} }
Response: { "ok": true }
```

---

## 7. Technical Specifications

### 7.1 Hook Timeout Handling

**Current Implementation**:
```python
# hooks.example.json
"timeout": 2000  # milliseconds
```

**Best Practices**:
1. Keep hook execution under 100ms (buffer for network)
2. Use async HTTP calls with timeout < 1s
3. Cache data in memory (don't fetch from network)
4. Fail gracefully (always `sys.exit(0)`)

**Example**:
```python
try:
    # Fast operation
    decision = evaluate_rules(tool_name, tool_input, cached_rules)  # <50ms

    # Async logging (non-blocking)
    send_event_async(url, decision, timeout=1.0)

except Exception as e:
    log_error(e)  # Log but don't fail

finally:
    sys.exit(0)  # Always succeed
```

### 7.2 Rule Matching Algorithm

**Pseudocode**:
```python
def evaluate_rules(tool_name: str, tool_input: dict, rules: list) -> tuple[str, str]:
    """
    Returns: (decision, matched_rule_id)
    decision: "allow" | "deny" | "pending_review"
    """
    for rule in sorted(rules, key=lambda r: r.priority):
        # Match tool name (supports wildcards and regex)
        if matches_pattern(tool_name, rule.pattern.tool_name):
            # Match parameters (supports wildcards and regex)
            if matches_parameters(tool_input, rule.pattern.parameters):
                return (rule.decision, rule.id)

    # No rule matched
    return ("pending_review", None)

def matches_pattern(value: str, pattern: str) -> bool:
    """
    Supports:
    - Exact match: "Bash"
    - Wildcard: "*", "Bash*"
    - Regex: "Bash|Read|Write"
    """
    if pattern == "*" or pattern == "":
        return True
    if "|" in pattern:
        return bool(re.match(pattern, value))
    return fnmatch.fnmatch(value, pattern)

def matches_parameters(input: dict, patterns: dict) -> bool:
    """
    Match all specified parameter patterns
    """
    for key, pattern in patterns.items():
        if key not in input:
            return False
        if not matches_pattern(str(input[key]), pattern):
            return False
    return True
```

### 7.3 Session Config File Format

**File**: `.agent-orchestrator/sessions/{session_name}.rules.json`

```json
{
  "version": "1.0",
  "session_id": "uuid",
  "updated_at": "2025-11-25T...",
  "rules": [
    {
      "id": "uuid-1",
      "priority": 1,
      "enabled": true,
      "pattern": {
        "tool_name": "Bash",
        "parameters": {
          "command": "npm run *"
        }
      },
      "decision": "allow",
      "reason": "Allow npm scripts"
    },
    {
      "id": "uuid-2",
      "priority": 2,
      "enabled": true,
      "pattern": {
        "tool_name": "Write",
        "parameters": {
          "file_path": "*.md"
        }
      },
      "decision": "allow",
      "reason": "Allow writing to markdown files"
    }
  ]
}
```

### 7.4 Frontend State Management

**Rule State** (localStorage + IndexedDB):
```typescript
interface PermissionRule {
  id: string;
  session_id: string;
  created_at: string;
  updated_at: string;
  enabled: boolean;
  priority: number;
  pattern: {
    tool_name: string;         // "Bash", "Read", "*"
    parameters: Record<string, string>;  // { "command": "npm run *" }
  };
  decision: 'allow' | 'deny' | 'ask';
  reason: string;
}

interface PendingReview {
  id: string;
  tool_use_id: string;
  session_id: string;
  tool_name: string;
  tool_input: Record<string, any>;
  timestamp: string;
  status: 'pending' | 'approved' | 'denied';
}
```

**Custom Hooks**:
```typescript
// usePermissionRules.ts
export const usePermissionRules = (sessionId: string) => {
  const [rules, setRules] = useState<PermissionRule[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch rules from backend
  // Subscribe to rule updates via WebSocket
  // CRUD operations: createRule, updateRule, deleteRule

  return { rules, loading, createRule, updateRule, deleteRule };
};

// usePendingReviews.ts
export const usePendingReviews = (sessionId: string) => {
  const [reviews, setReviews] = useState<PendingReview[]>([]);

  // Fetch pending reviews
  // Subscribe to new pending reviews via WebSocket
  // Actions: approve, deny, createRuleFromReview

  return { reviews, approve, deny, createRuleFromReview };
};
```

---

## 8. Risk Analysis

### 8.1 Risks for Stop Mechanism

| Risk | Impact | Probability | Mitigation |
|------|--------|------------|-----------|
| **Stop file not detected** | MEDIUM | LOW | Add logging, verify polling frequency |
| **Stop file persists after crash** | LOW | MEDIUM | Cleanup on session start, validation |
| **Multiple stop requests** | LOW | MEDIUM | Idempotent file write, status check |
| **Timing delay frustrates users** | MEDIUM | MEDIUM | Document 1-2s delay, show "Stopping..." state |
| **Mid-tool execution** | MEDIUM | HIGH | Document behavior, acceptable trade-off |

**Overall Risk**: LOW - Simple mechanism, well-understood patterns

### 8.2 Risks for Permission Control

| Risk | Impact | Probability | Mitigation |
|------|--------|------------|-----------|
| **2s timeout exceeded** | HIGH | MEDIUM | Optimize rule matching (<50ms), cache rules |
| **Rule patterns too complex** | MEDIUM | HIGH | Provide templates, pattern builder UI |
| **Rules sync problems** | MEDIUM | MEDIUM | Graceful degradation, version control |
| **Permission bypass** | HIGH | LOW | Validate rules, audit trail, confirmation |
| **Hook errors break agent** | HIGH | LOW | Wrap in try-catch, always exit(0) |
| **Frontend/backend desync** | MEDIUM | MEDIUM | Timestamps, conflict resolution |
| **Users don't create rules** | MEDIUM | HIGH | Auto-suggest rules, templates, onboarding |

**Overall Risk**: MEDIUM-HIGH - Complex system, requires careful UX design

### 8.3 Mitigation Strategies

**For Hook Reliability**:
```python
def pretool_hook_safe_wrapper():
    try:
        # Load rules from cache (not network)
        rules = load_cached_rules()

        # Fast evaluation
        decision = evaluate_rules(tool_name, tool_input, rules)

        # Async logging (non-blocking)
        asyncio.create_task(send_event(url, decision))

    except Exception as e:
        # Log error but don't fail
        log_error(e)
        decision = "pending_review"  # Safe default

    finally:
        # ALWAYS exit successfully
        sys.exit(0)
```

**For Rule Validation**:
```python
def validate_rule(rule: dict) -> bool:
    # Check pattern complexity (prevent ReDoS)
    if len(rule['pattern']['tool_name']) > 200:
        return False

    # Validate decision
    if rule['decision'] not in ['allow', 'deny', 'ask']:
        return False

    # Limit parameter patterns
    if len(rule['pattern']['parameters']) > 10:
        return False

    return True
```

**For Performance**:
```python
# Rule caching
_rule_cache = {}
_cache_timestamp = None

def load_rules(session_name: str) -> list:
    global _rule_cache, _cache_timestamp

    # Cache for 5 seconds
    if _cache_timestamp and (time.time() - _cache_timestamp) < 5:
        return _rule_cache.get(session_name, [])

    # Reload from file
    rules = json.loads(Path(f"{session_name}.rules.json").read_text())
    _rule_cache[session_name] = rules
    _cache_timestamp = time.time()

    return rules
```

---

## 9. Appendices

### Appendix A: Complete File Listing

**Backend Files**:
```
agent-orchestrator-observability/
├── backend/
│   ├── main.py                    # FastAPI app, WebSocket, endpoints
│   ├── database.py                # SQLite operations
│   └── models.py                  # Pydantic models
├── hooks/
│   ├── user_prompt_submit_hook.py
│   ├── post_tool_hook.py
│   └── hooks.example.json
└── pyproject.toml
```

**Frontend Files**:
```
agent-orchestrator-frontend/
├── src/
│   ├── contexts/
│   │   └── WebSocketContext.tsx
│   ├── hooks/
│   │   └── useSessions.ts
│   ├── services/
│   │   └── sessionService.ts
│   ├── components/
│   │   └── features/
│   │       └── sessions/
│   │           ├── SessionList.tsx
│   │           ├── SessionCard.tsx
│   │           ├── EventTimeline.tsx
│   │           └── EventCard.tsx
│   └── types/
│       ├── session.ts
│       └── event.ts
└── package.json
```

**Orchestration Files**:
```
plugins/agent-orchestrator/
├── mcp-server/
│   ├── agent-orchestrator-mcp.py
│   └── libs/
│       ├── server.py
│       └── utils.py
└── skills/agent-orchestrator/commands/
    ├── ao-new
    ├── ao-resume
    ├── ao-status
    └── lib/
        ├── config.py
        ├── session.py
        ├── agent.py
        ├── claude_client.py
        └── observability.py
```

### Appendix B: Key Line References

| Component | File | Key Lines | Purpose |
|-----------|------|-----------|---------|
| WebSocket Server | main.py | 162-180 | WebSocket endpoint |
| Event Broadcast | main.py | 70-81 | Broadcast pattern |
| Session Create | main.py | 45-88 | POST /events handler |
| Stop Detection | claude_client.py | 157-229 | Message loop (to modify) |
| Hook Registration | claude_client.py | 107-121 | Programmatic hooks |
| Frontend WebSocket | WebSocketContext.tsx | 20-64 | Connection management |
| Frontend Subscribe | WebSocketContext.tsx | 76-81 | Subscription pattern |
| Session List Hook | useSessions.ts | 31-77 | WebSocket message handling |
| Process Spawn | utils.py (MCP) | 201-207 | Async execution |
| Rule Matching | (to create) | N/A | Permission control |

### Appendix C: Environment Variables

```bash
# Observability
AGENT_ORCHESTRATOR_OBSERVABILITY_ENABLED=true
AGENT_ORCHESTRATOR_OBSERVABILITY_URL=http://127.0.0.1:8765

# Paths
AGENT_ORCHESTRATOR_PROJECT_DIR=/path/to/project
AGENT_ORCHESTRATOR_SESSIONS_DIR=/path/to/sessions
AGENT_ORCHESTRATOR_AGENTS_DIR=/path/to/agents

# Logging
AGENT_ORCHESTRATOR_ENABLE_LOGGING=false
DEBUG_LOGGING=false

# Frontend
VITE_WEBSOCKET_URL=ws://localhost:8765/ws
VITE_OBSERVABILITY_BACKEND_URL=http://localhost:8765
```

### Appendix D: Testing Checklist

**Stop Mechanism Tests**:
- [ ] Stop running session (happy path)
- [ ] Stop already finished session (should fail gracefully)
- [ ] Multiple stop requests (idempotent)
- [ ] Stop file cleanup (verify removal)
- [ ] Timing (measure detection delay)
- [ ] Mid-tool execution (verify tool completes first)
- [ ] WebSocket broadcast (verify clients notified)
- [ ] Session status update (verify "stopping" → "stopped")

**Permission Control Tests**:
- [ ] Rule matching (exact, wildcard, regex)
- [ ] Rule priority (first match wins)
- [ ] No rule match (pending review)
- [ ] Rule creation from pending review
- [ ] Rule CRUD operations
- [ ] Hook timeout (verify <2s execution)
- [ ] Rule sync (frontend ↔ backend)
- [ ] Performance (100 rules, measure time)

### Appendix E: Glossary

| Term | Definition |
|------|-----------|
| **AE Commands** | Agent Executor commands (ao-new, ao-resume, etc.) |
| **MCP** | Model Context Protocol (server for Claude tools) |
| **SDK** | Software Development Kit (claude-agent-sdk) |
| **Hook** | Event callback registered with Claude SDK |
| **Session** | Single agent execution instance |
| **JSONL** | JSON Lines format (one JSON object per line) |
| **WebSocket** | Protocol for bidirectional real-time communication |
| **Observability** | System for monitoring agent behavior |
| **Detached Process** | Process that runs independently of parent |
| **File Marker** | Signal file used for inter-process communication |
| **Rule Pattern** | Template for matching tool calls |
| **Pending Review** | Tool execution awaiting user approval |

---

## Conclusion

This comprehensive analysis has evaluated the current architecture and identified two viable approaches for implementing two-way communication:

### Stop Mechanism: File Marker Approach
- **Timeline**: 1-2 days
- **Complexity**: LOW
- **Feasibility**: HIGH
- **Recommended**: ✅ Proceed immediately

### Permission Control: Hybrid Rule-Based + Review Queue
- **Timeline**: 5-7 weeks (or 2-3 weeks for MVP)
- **Complexity**: HIGH
- **Feasibility**: MEDIUM (with trade-offs)
- **Recommended**: ✅ Proceed with MVP first

### Key Constraints Identified
1. Claude SDK hooks have 2-second timeout (cannot extend)
2. Hooks are observational only (cannot enforce decisions)
3. No SDK pause/resume mechanism exists
4. Current architecture is one-way (backend → frontend)

### Recommended Next Steps
1. Implement stop mechanism (1-2 days)
2. Validate with users
3. Implement permission control MVP (2-3 weeks)
4. Collect usage data
5. Enhance with full rule engine (3-4 weeks)

Both solutions work within existing architectural constraints while providing meaningful user control from the frontend.

---

**End of Document**
