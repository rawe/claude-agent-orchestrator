# HTTP-Based Two-Way Communication Solutions

**Date**: November 25, 2025
**Focus**: HTTP-based architecture for communicating decisions back to AE command processes
**Constraint Relaxation**: Hook timeout can be extended (no longer limited to 2 seconds)
**Requirement**: No file-based solutions - HTTP connections only

---

## Executive Summary

This document evaluates architectural approaches for establishing HTTP-based two-way communication between the frontend and the AE command processes (ao-new/ao-resume) that host the Claude Agent SDK. The goal is to enable:

1. **Stop mechanism**: Halt running agent execution
2. **Permission control**: Approve/deny tool executions in real-time

With the constraint that hook timeouts can be extended, several HTTP-based patterns become viable. This analysis evaluates 7 distinct approaches across dimensions of complexity, scalability, reliability, and implementation effort.

### Quick Recommendation Summary

| Approach | Complexity | Scalability | Reliability | Timeline | Recommended |
|----------|-----------|-------------|-------------|----------|-------------|
| 1. Temporal Server per Session | HIGH | LOW | MEDIUM | 3-4 weeks | 🟡 |
| 2. Blocking HTTP with Response | MEDIUM | MEDIUM | HIGH | 2-3 weeks | ✅ BEST |
| 3. Long-Polling Pattern | MEDIUM | MEDIUM | MEDIUM | 2-3 weeks | ✅ |
| 4. Request/Response via Correlation ID | MEDIUM | HIGH | HIGH | 3-4 weeks | ✅ |
| 5. WebSocket from Hook | HIGH | MEDIUM | MEDIUM | 3-4 weeks | 🟡 |
| 6. Server-Sent Events (SSE) | HIGH | LOW | LOW | 3-4 weeks | ❌ |
| 7. Hybrid: Temp Server + Registry | VERY HIGH | HIGH | HIGH | 5-6 weeks | 🟡 |

**Top 3 Recommendations**:
1. **Approach 2**: Blocking HTTP with Response (simplest, works for local use case)
2. **Approach 3**: Long-Polling Pattern (more robust, better for production)
3. **Approach 4**: Correlation ID Pattern (most scalable, production-ready)

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Architecture Context](#2-architecture-context)
3. [Approach 1: Temporal Server per Session](#3-approach-1-temporal-server-per-session)
4. [Approach 2: Blocking HTTP with Response](#4-approach-2-blocking-http-with-response)
5. [Approach 3: Long-Polling Pattern](#5-approach-3-long-polling-pattern)
6. [Approach 4: Request/Response via Correlation ID](#6-approach-4-requestresponse-via-correlation-id)
7. [Approach 5: WebSocket from Hook](#7-approach-5-websocket-from-hook)
8. [Approach 6: Server-Sent Events (SSE)](#8-approach-6-server-sent-events-sse)
9. [Approach 7: Hybrid - Temp Server + Registry](#9-approach-7-hybrid-temp-server--registry)
10. [Comparative Analysis](#10-comparative-analysis)
11. [Implementation Recommendations](#11-implementation-recommendations)
12. [Technical Specifications](#12-technical-specifications)

---

## 1. Problem Statement

### 1.1 Current Architecture Limitation

**Current Flow** (One-Way):
```
AE Command (ao-new) → Claude SDK → Hook → HTTP POST → Observability Backend → WebSocket → Frontend
                                      ↓
                                 (2s timeout)
                                      ↓
                                 Exit(0) always
```

**Problem**:
- No way for frontend to send decisions back to running AE command process
- Hook completes and exits immediately
- AE command process has no HTTP server to receive commands
- File-based solutions rejected for production use

### 1.2 Requirements

**Functional Requirements**:
1. Frontend sends "stop" command → AE command process stops execution
2. Frontend approves/denies tool → Hook receives decision before tool executes
3. Multiple concurrent sessions supported
4. Real-time responsiveness (decisions within seconds, not minutes)

**Non-Functional Requirements**:
1. **HTTP-based only** (no file-based solutions)
2. **Scalable**: Support multiple concurrent sessions
3. **Reliable**: Decisions must reach target process
4. **Maintainable**: Clear separation of concerns
5. **Local-first**: Optimized for single-machine development use case

**Constraint Relaxation**:
- Hook timeout can be extended (e.g., 30-60 seconds for waiting on user input)
- Acceptable for hook to block while waiting for decision

### 1.3 Key Architectural Questions

1. **Where does the HTTP server live?**
   - In AE command process? (Approach 1, 7)
   - In observability backend? (Approach 2, 3, 4)
   - No server, use existing connections? (Approach 5, 6)

2. **How does frontend discover the target?**
   - Service registry? (Approach 7)
   - Session ID routing? (Approach 2, 3, 4)
   - Direct connection info? (Approach 1)

3. **How does hook wait for decision?**
   - Blocking HTTP call? (Approach 2)
   - Polling? (Approach 4)
   - Long-polling? (Approach 3)
   - Persistent connection? (Approach 5, 6)

4. **What happens with multiple frontends?**
   - First response wins?
   - All must agree?
   - User acknowledgment: "On local machine, very doubtful"

---

## 2. Architecture Context

### 2.1 Current Component Topology

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (React) - Port 3000/5173                          │
│  - WebSocket client to observability backend                │
│  - HTTP client for REST API                                 │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Observability Backend (FastAPI) - Port 8765                │
│  - POST /events (receive from hooks)                        │
│  - WebSocket /ws (push to frontends)                        │
│  - SQLite database                                          │
└─────────────────────────────────────────────────────────────┘
                           ▲
                           │ HTTP POST (from hooks)
                           │
┌─────────────────────────────────────────────────────────────┐
│  AE Command Process (ao-new/ao-resume)                      │
│  - Runs as subprocess (detached)                            │
│  - No HTTP server currently                                 │
│  - Executes Claude SDK                                      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Claude SDK                                          │   │
│  │  - Message loop                                      │   │
│  │  - Tool execution                                    │   │
│  │  - Hook invocation                                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  PreToolUse Hook (Python script)                     │   │
│  │  - Currently: POST to observability, exit(0)         │   │
│  │  - Needed: Wait for decision, return approval        │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Key Insights

**AE Command Process Characteristics**:
- Process ID: Available but not currently tracked
- Lifecycle: Runs until session completes
- Network: No listening sockets
- State: Session ID known after SDK initialization
- Isolation: Each session = separate process

**Hook Execution Context**:
- Timing: Can be extended (new constraint)
- Execution: Synchronous within SDK flow
- Network: Can make outbound HTTP calls
- State: Has session_id, tool_name, tool_input
- Return value: Can return approval/denial (SDK supports this)

**Observability Backend Characteristics**:
- Always running (persistent server)
- Single instance on localhost:8765
- Has session registry (SQLite)
- WebSocket connections to frontends
- Can route by session_id

---

## 3. Approach 1: Temporal Server per Session

### 3.1 Architecture

**Concept**: Each AE command process starts its own HTTP server on a random available port.

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend                                                    │
│  User clicks "Stop Session X"                               │
└─────────────────────────────────────────────────────────────┘
            │
            ▼ POST /sessions/{session_id}/stop
┌─────────────────────────────────────────────────────────────┐
│  Observability Backend                                       │
│  1. Lookup session_id → get command_server_url              │
│  2. Proxy request to http://localhost:{port}/stop           │
└─────────────────────────────────────────────────────────────┘
            │
            ▼ HTTP POST http://localhost:52341/stop
┌─────────────────────────────────────────────────────────────┐
│  AE Command Process (Session X)                             │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Temporal HTTP Server (FastAPI/Flask)                │   │
│  │  - Port: 52341 (random, found via socket binding)   │   │
│  │  - POST /stop → Set stop flag                       │   │
│  │  - POST /approve-tool → Store approval decision     │   │
│  │  - GET /status → Return current state                │   │
│  └──────────────────────────────────────────────────────┘   │
│              │                                               │
│              ▼ (shared state)                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Claude SDK Message Loop                             │   │
│  │  - Checks stop flag after each message               │   │
│  │  - Reads approval decisions from queue               │   │
│  └──────────────────────────────────────────────────────┘   │
│              │                                               │
│              ▼                                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  PreToolUse Hook                                     │   │
│  │  - Query local server for approval                   │   │
│  │  - Wait up to 30s for decision                       │   │
│  │  - Return approval/denial to SDK                     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Implementation Details

**Phase 1: Start Server on AE Command Launch**

```python
# File: plugins/agent-orchestrator/.../lib/claude_client.py

import asyncio
from fastapi import FastAPI
from threading import Thread, Event
import socket

class SessionCommandServer:
    """HTTP server for receiving commands for this session"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.port = self._find_free_port()
        self.app = FastAPI()
        self.stop_requested = Event()
        self.approval_queue = {}  # tool_use_id -> decision

        # Register endpoints
        self.app.post("/stop")(self.handle_stop)
        self.app.post("/approve-tool/{tool_use_id}")(self.handle_approve_tool)
        self.app.get("/status")(self.handle_status)

    def _find_free_port(self) -> int:
        """Find an available port"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port

    async def handle_stop(self):
        """Handle stop request"""
        self.stop_requested.set()
        return {"ok": True, "message": "Stop requested"}

    async def handle_approve_tool(self, tool_use_id: str, decision: dict):
        """Handle tool approval/denial"""
        self.approval_queue[tool_use_id] = decision
        return {"ok": True}

    async def handle_status(self):
        """Return server status"""
        return {
            "session_id": self.session_id,
            "port": self.port,
            "running": True
        }

    def start(self):
        """Start server in background thread"""
        def run():
            import uvicorn
            uvicorn.run(self.app, host="127.0.0.1", port=self.port)

        thread = Thread(target=run, daemon=True)
        thread.start()

    def wait_for_approval(self, tool_use_id: str, timeout: float = 30.0) -> str:
        """Wait for approval decision"""
        import time
        start = time.time()
        while time.time() - start < timeout:
            if tool_use_id in self.approval_queue:
                return self.approval_queue.pop(tool_use_id)
            time.sleep(0.1)
        return "deny"  # Default to deny on timeout


async def run_claude_session(...):
    # Start command server
    command_server = SessionCommandServer(session_id)
    command_server.start()

    # Register server with observability backend
    await register_command_server(
        observability_url,
        session_id,
        f"http://127.0.0.1:{command_server.port}"
    )

    try:
        # Main message loop
        async for message in client.receive_response():
            # Check for stop
            if command_server.stop_requested.is_set():
                break

            # Process message...

    finally:
        # Unregister server
        await unregister_command_server(observability_url, session_id)
```

**Phase 2: Register Server Info**

```python
# File: plugins/agent-orchestrator/.../lib/observability.py

async def register_command_server(url: str, session_id: str, server_url: str):
    """Register command server URL with observability backend"""
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{url}/sessions/{session_id}/command-server",
            json={"server_url": server_url}
        )
```

**Phase 3: Observability Backend Routing**

```python
# File: agent-orchestrator-observability/backend/main.py

# New table
CREATE TABLE session_command_servers (
    session_id TEXT PRIMARY KEY,
    server_url TEXT NOT NULL,
    registered_at TEXT NOT NULL
);

@app.post("/sessions/{session_id}/command-server")
async def register_command_server(session_id: str, data: dict):
    """Register command server for session"""
    db.execute(
        "INSERT OR REPLACE INTO session_command_servers VALUES (?, ?, ?)",
        (session_id, data["server_url"], datetime.now(UTC).isoformat())
    )
    return {"ok": True}

@app.post("/sessions/{session_id}/stop")
async def stop_session_proxy(session_id: str):
    """Proxy stop request to session's command server"""
    # Get server URL
    row = db.execute(
        "SELECT server_url FROM session_command_servers WHERE session_id = ?",
        (session_id,)
    ).fetchone()

    if not row:
        raise HTTPException(404, "Session command server not found")

    # Proxy request
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{row['server_url']}/stop")
        return response.json()
```

**Phase 4: Hook Queries Local Server**

```python
# File: agent-orchestrator-observability/hooks/pre_tool_hook.py

def pre_tool_hook():
    session_id = input_data["session_id"]
    tool_use_id = input_data["tool_use_id"]
    tool_name = input_data["tool_name"]

    # Query local command server for approval
    # (Server URL can be passed via env var or convention)
    command_server_url = os.getenv("SESSION_COMMAND_SERVER_URL")

    if command_server_url:
        try:
            # Wait for approval (blocking)
            response = requests.get(
                f"{command_server_url}/wait-approval/{tool_use_id}",
                timeout=30.0
            )
            decision = response.json()["decision"]
        except requests.Timeout:
            decision = "deny"
    else:
        decision = "allow"  # Fallback

    # Return decision to SDK
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision
        }
    }
```

### 3.3 Evaluation

#### Pros
- ✅ **Direct communication**: Frontend → Backend → AE process (no intermediaries)
- ✅ **Process isolation**: Each session has dedicated server
- ✅ **State locality**: Approval decisions local to process
- ✅ **Flexibility**: Can add any endpoints needed
- ✅ **Real-time**: Direct HTTP calls, no polling

#### Cons
- ❌ **Port management complexity**: Finding free ports, conflicts
- ❌ **Registration overhead**: Must register/unregister with central backend
- ❌ **Scalability concerns**: Each session = new server (resource overhead)
- ❌ **Discovery complexity**: Frontend must lookup server URL
- ❌ **Connection reliability**: If server crashes, no way to reach process
- ❌ **Firewall issues**: Multiple listening ports may trigger security alerts
- ❌ **Cleanup**: Stale server registrations if process crashes

#### Scalability Analysis

**Resource Overhead per Session**:
- Memory: ~50-100MB per FastAPI/Flask server
- Ports: 1 port per session
- Threads: 1+ per server

**Limits**:
- Ports: ~65,535 total (excluding reserved) → realistically ~100 concurrent sessions
- Memory: 100 sessions × 100MB = 10GB

**Failure Modes**:
- Port exhaustion: Can't start new sessions
- Registration desync: Backend has stale server URLs
- Orphaned servers: Process crashes, server still running

#### Implementation Complexity

| Component | Effort | Complexity |
|-----------|--------|-----------|
| Session command server class | 2-3 days | MEDIUM |
| Port management & discovery | 1-2 days | MEDIUM |
| Registration/unregister logic | 1 day | LOW |
| Observability backend routing | 2 days | MEDIUM |
| Hook integration | 1 day | LOW |
| Error handling & cleanup | 2-3 days | HIGH |
| **Total** | **9-12 days** | **MEDIUM-HIGH** |

**Timeline**: 2-3 weeks

### 3.4 Recommendation

**Rating**: 🟡 VIABLE BUT NOT IDEAL

**Use When**:
- Need absolute process isolation
- Sessions are long-running (server overhead justified)
- Local development only (not production)

**Avoid When**:
- High session churn (many short sessions)
- Resource constraints
- Need production scalability

---

## 4. Approach 2: Blocking HTTP with Response

### 4.1 Architecture

**Concept**: Hook makes HTTP POST to observability backend and BLOCKS waiting for response. Backend holds request open until frontend sends decision.

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend                                                    │
│  User sees "Approve tool execution?"                         │
│  Clicks "Approve"                                            │
└─────────────────────────────────────────────────────────────┘
            │
            ▼ POST /tool-decisions/{request_id}/respond
┌─────────────────────────────────────────────────────────────┐
│  Observability Backend (FastAPI with async)                 │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Pending Requests Store                              │   │
│  │  {                                                   │   │
│  │    "req-123": {                                      │   │
│  │      "tool_name": "Bash",                            │   │
│  │      "response_future": AsyncFuture(),               │   │
│  │      "created_at": "...",                            │   │
│  │      "timeout": 30                                   │   │
│  │    }                                                 │   │
│  │  }                                                   │   │
│  └──────────────────────────────────────────────────────┘   │
│              │                                               │
│              ▼ (resolve future)                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  POST /request-approval (from hook)                  │   │
│  │  - Create request entry                              │   │
│  │  - Broadcast to frontend via WebSocket               │   │
│  │  - WAIT for response (await future)                  │   │
│  │  - Return decision to hook                           │   │
│  └──────────────────────────────────────────────────────┘   │
│              │                                               │
│              ▼ (when frontend responds)                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  POST /tool-decisions/{request_id}/respond           │   │
│  │  - Set future result (unblocks waiting request)      │   │
│  │  - Return success to frontend                        │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
            ▲
            │ (HTTP POST, blocks for up to 30s)
┌─────────────────────────────────────────────────────────────┐
│  PreToolUse Hook                                            │
│  1. POST to /request-approval                               │
│  2. Wait for response (blocking)                            │
│  3. Receive decision in response body                       │
│  4. Return decision to SDK                                  │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Implementation Details

**Phase 1: Backend - Pending Request Storage**

```python
# File: agent-orchestrator-observability/backend/main.py

import asyncio
from typing import Dict
from datetime import datetime, UTC

# In-memory storage for pending approval requests
pending_requests: Dict[str, dict] = {}

class PendingRequest:
    def __init__(self, request_id: str, session_id: str, tool_name: str, tool_input: dict, timeout: float = 30.0):
        self.request_id = request_id
        self.session_id = session_id
        self.tool_name = tool_name
        self.tool_input = tool_input
        self.timeout = timeout
        self.created_at = datetime.now(UTC)
        self.future = asyncio.Future()

@app.post("/request-approval")
async def request_approval(request: dict):
    """
    Hook calls this endpoint and BLOCKS waiting for approval.
    Returns approval decision when frontend responds.
    """
    request_id = str(uuid.uuid4())
    session_id = request["session_id"]
    tool_name = request["tool_name"]
    tool_input = request["tool_input"]

    # Create pending request
    pending = PendingRequest(request_id, session_id, tool_name, tool_input, timeout=30.0)
    pending_requests[request_id] = pending

    # Broadcast to frontend via WebSocket
    message = json.dumps({
        "type": "approval_request",
        "request_id": request_id,
        "session_id": session_id,
        "tool_name": tool_name,
        "tool_input": tool_input,
        "timeout": 30.0
    })

    for ws in connections.copy():
        try:
            await ws.send_text(message)
        except:
            connections.discard(ws)

    # WAIT for response (blocks here)
    try:
        decision = await asyncio.wait_for(pending.future, timeout=30.0)
        return {"decision": decision, "request_id": request_id}
    except asyncio.TimeoutError:
        # Timeout - default to deny
        return {"decision": "deny", "request_id": request_id, "reason": "timeout"}
    finally:
        # Cleanup
        pending_requests.pop(request_id, None)


@app.post("/tool-decisions/{request_id}/respond")
async def respond_to_approval(request_id: str, response: dict):
    """
    Frontend calls this to provide approval decision.
    Unblocks the waiting /request-approval call.
    """
    if request_id not in pending_requests:
        raise HTTPException(404, "Request not found or already completed")

    pending = pending_requests[request_id]

    # Resolve the future (unblocks waiting request)
    decision = response.get("decision", "deny")
    pending.future.set_result(decision)

    return {"ok": True, "message": "Decision recorded"}
```

**Phase 2: Hook - Blocking Request**

```python
# File: agent-orchestrator-observability/hooks/pre_tool_hook.py

import httpx
import json
import sys

def pre_tool_hook():
    input_data = json.loads(sys.stdin.read())

    session_id = input_data.get("session_id")
    tool_name = input_data.get("tool_name")
    tool_input = input_data.get("tool_input")

    observability_url = os.getenv("AGENT_ORCHESTRATOR_OBSERVABILITY_URL", "http://127.0.0.1:8765")

    try:
        # Make BLOCKING request (wait up to 30 seconds)
        response = httpx.post(
            f"{observability_url}/request-approval",
            json={
                "session_id": session_id,
                "tool_name": tool_name,
                "tool_input": tool_input
            },
            timeout=30.0  # Extended timeout
        )

        decision = response.json().get("decision", "deny")

        # Return decision to SDK
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision
            }
        }
        print(json.dumps(result))
        sys.exit(0)

    except httpx.TimeoutException:
        # Timeout - default to deny
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "User approval timeout"
            }
        }
        print(json.dumps(result))
        sys.exit(0)

    except Exception as e:
        # Error - default to deny for safety
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Error: {str(e)}"
            }
        }
        print(json.dumps(result))
        sys.exit(0)
```

**Phase 3: Frontend - Approval UI**

```typescript
// File: agent-orchestrator-frontend/src/hooks/useApprovalRequests.ts

export const useApprovalRequests = () => {
  const [pendingRequests, setPendingRequests] = useState<ApprovalRequest[]>([]);
  const { subscribe } = useWebSocket();

  useEffect(() => {
    const unsubscribe = subscribe((message: WebSocketMessage) => {
      if (message.type === 'approval_request') {
        // Add to pending requests
        setPendingRequests(prev => [...prev, {
          request_id: message.request_id,
          session_id: message.session_id,
          tool_name: message.tool_name,
          tool_input: message.tool_input,
          timeout: message.timeout,
          created_at: new Date()
        }]);
      }
    });

    return unsubscribe;
  }, [subscribe]);

  const approve = async (requestId: string) => {
    await observabilityApi.post(`/tool-decisions/${requestId}/respond`, {
      decision: 'allow'
    });

    // Remove from pending
    setPendingRequests(prev => prev.filter(r => r.request_id !== requestId));
  };

  const deny = async (requestId: string) => {
    await observabilityApi.post(`/tool-decisions/${requestId}/respond`, {
      decision: 'deny'
    });

    // Remove from pending
    setPendingRequests(prev => prev.filter(r => r.request_id !== requestId));
  };

  return { pendingRequests, approve, deny };
};
```

```typescript
// File: agent-orchestrator-frontend/src/components/ApprovalModal.tsx

export const ApprovalModal = () => {
  const { pendingRequests, approve, deny } = useApprovalRequests();

  if (pendingRequests.length === 0) return null;

  const request = pendingRequests[0];  // Show oldest request

  return (
    <Modal open={true}>
      <h2>Tool Execution Approval Required</h2>
      <p>Session: {request.session_id}</p>
      <p>Tool: {request.tool_name}</p>
      <pre>{JSON.stringify(request.tool_input, null, 2)}</pre>

      <div className="actions">
        <button onClick={() => approve(request.request_id)}>
          Approve
        </button>
        <button onClick={() => deny(request.request_id)}>
          Deny
        </button>
      </div>

      <p>Timeout in {calculateTimeRemaining(request)} seconds</p>
    </Modal>
  );
};
```

**Phase 4: Stop Mechanism (Bonus)**

```python
# File: agent-orchestrator-observability/backend/main.py

# Store stop requests similarly
stop_requests: Dict[str, asyncio.Event] = {}

@app.post("/sessions/{session_id}/request-stop")
async def request_stop(session_id: str):
    """
    Frontend requests stop.
    This sets an event that the message loop checks.
    """
    if session_id not in stop_requests:
        stop_requests[session_id] = asyncio.Event()

    stop_requests[session_id].set()

    return {"ok": True, "message": "Stop requested"}


# In message loop hook or periodic check
@app.get("/check-stop/{session_id}")
async def check_stop(session_id: str):
    """
    Hook or message loop calls this to check if stop requested.
    """
    if session_id in stop_requests and stop_requests[session_id].is_set():
        return {"stop_requested": True}
    else:
        return {"stop_requested": False}
```

### 4.3 Evaluation

#### Pros
- ✅ **Simplest architecture**: No temp servers, no port management
- ✅ **Centralized**: All logic in observability backend
- ✅ **Single connection**: Frontend always talks to same backend
- ✅ **No discovery**: Frontend knows backend URL (static)
- ✅ **Blocking explicit**: Clear when hook is waiting
- ✅ **Works for local use case**: User acknowledged single frontend likely
- ✅ **Minimal changes**: Leverages existing backend

#### Cons
- ❌ **Multiple frontends problematic**: First response wins (but unlikely on local machine)
- ❌ **Backend becomes bottleneck**: Holds many open connections
- ❌ **Connection limits**: Backend has max concurrent connection limit
- ❌ **Timeout management**: Must handle timeouts at multiple levels
- ❌ **Memory usage**: Pending requests stored in memory

#### Scalability Analysis

**Connection Handling**:
- FastAPI/Uvicorn default: 100 concurrent connections
- With tuning: Up to 1000-2000 connections
- Each pending approval = 1 held connection

**Resource Usage**:
- Memory: ~1KB per pending request (minimal)
- Connections: 1 per waiting hook

**Limits**:
- Concurrent approvals: ~100-1000 (depends on config)
- Sufficient for local development

**Failure Modes**:
- Backend restart: All pending requests timeout
- Network hiccup: Hook timeout triggers
- Slow frontend: Timeout before user responds

#### Implementation Complexity

| Component | Effort | Complexity |
|-----------|--------|-----------|
| Backend pending request storage | 1 day | LOW |
| Backend async future handling | 2 days | MEDIUM |
| Approval request endpoint | 1 day | LOW |
| Response endpoint | 1 day | LOW |
| Hook blocking request | 1 day | LOW |
| Frontend approval UI | 3-4 days | MEDIUM |
| WebSocket integration | 1 day | LOW |
| **Total** | **10-12 days** | **LOW-MEDIUM** |

**Timeline**: 2-3 weeks

### 4.4 Recommendation

**Rating**: ✅ **RECOMMENDED FOR LOCAL USE CASE**

**Use When**:
- Single user, local development (as stated by user)
- Simplicity valued over ultimate scalability
- Want to leverage existing backend

**Avoid When**:
- Multiple concurrent frontend users expected
- Need production-grade scalability
- Backend restarts frequently (would lose pending requests)

**Best For**: User's stated use case (local machine, unlikely multiple frontends)

---

## 5. Approach 3: Long-Polling Pattern

### 4.1 Architecture

**Concept**: Hook makes initial request, gets request_id, then polls for decision. Frontend posts decision separately. Backend matches them up.

```
┌─────────────────────────────────────────────────────────────┐
│  PreToolUse Hook                                            │
│  1. POST /create-approval-request                           │
│     → Response: { request_id: "req-123" }                   │
│                                                              │
│  2. Loop: GET /approval-requests/req-123/decision           │
│     - Long-poll with timeout=5s                             │
│     - If no decision yet, returns 202 Accepted              │
│     - If decision ready, returns 200 + decision             │
│     - Repeat until decision or overall timeout (30s)        │
│                                                              │
│  3. Return decision to SDK                                  │
└─────────────────────────────────────────────────────────────┘
            ▲
            │ (polling)
            ▼
┌─────────────────────────────────────────────────────────────┐
│  Observability Backend                                       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Approval Requests Table (SQLite or in-memory)       │   │
│  │  {                                                   │   │
│  │    "request_id": "req-123",                          │   │
│  │    "session_id": "...",                              │   │
│  │    "status": "pending",  // pending, approved, denied│   │
│  │    "decision": null,                                 │   │
│  │    "created_at": "...",                              │   │
│  │  }                                                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
            ▲
            │ (posts decision)
┌─────────────────────────────────────────────────────────────┐
│  Frontend                                                    │
│  User clicks "Approve"                                       │
│  → POST /approval-requests/req-123/decide                   │
│     Body: { decision: "allow" }                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Implementation Details

**Phase 1: Backend - Request Creation**

```python
# File: agent-orchestrator-observability/backend/main.py

from pydantic import BaseModel
from typing import Literal

class ApprovalRequest(BaseModel):
    request_id: str
    session_id: str
    tool_name: str
    tool_input: dict
    status: Literal["pending", "approved", "denied"]
    decision: str | None
    created_at: str
    decided_at: str | None

# In-memory storage (could use SQLite instead)
approval_requests: Dict[str, ApprovalRequest] = {}

@app.post("/create-approval-request")
async def create_approval_request(request: dict):
    """
    Hook creates an approval request.
    Returns request_id for polling.
    """
    request_id = str(uuid.uuid4())

    approval_req = ApprovalRequest(
        request_id=request_id,
        session_id=request["session_id"],
        tool_name=request["tool_name"],
        tool_input=request["tool_input"],
        status="pending",
        decision=None,
        created_at=datetime.now(UTC).isoformat(),
        decided_at=None
    )

    approval_requests[request_id] = approval_req

    # Broadcast to frontend
    message = json.dumps({
        "type": "approval_request",
        "data": approval_req.dict()
    })

    for ws in connections.copy():
        try:
            await ws.send_text(message)
        except:
            connections.discard(ws)

    return {"request_id": request_id}


@app.get("/approval-requests/{request_id}/decision")
async def poll_for_decision(request_id: str, timeout: float = 5.0):
    """
    Long-polling endpoint for hooks.
    Waits up to `timeout` seconds for a decision.
    Returns 202 if still pending, 200 if decided.
    """
    if request_id not in approval_requests:
        raise HTTPException(404, "Request not found")

    start_time = asyncio.get_event_loop().time()

    # Poll with short sleep
    while asyncio.get_event_loop().time() - start_time < timeout:
        req = approval_requests[request_id]

        if req.status != "pending":
            # Decision made
            return {
                "status": req.status,
                "decision": req.decision,
                "decided_at": req.decided_at
            }

        # Wait a bit before checking again
        await asyncio.sleep(0.5)

    # Timeout - still pending
    return JSONResponse(
        status_code=202,
        content={"status": "pending", "message": "No decision yet"}
    )


@app.post("/approval-requests/{request_id}/decide")
async def decide_approval(request_id: str, decision_data: dict):
    """
    Frontend posts decision here.
    """
    if request_id not in approval_requests:
        raise HTTPException(404, "Request not found")

    req = approval_requests[request_id]

    if req.status != "pending":
        raise HTTPException(400, "Request already decided")

    # Update decision
    decision = decision_data.get("decision", "deny")
    req.status = "approved" if decision == "allow" else "denied"
    req.decision = decision
    req.decided_at = datetime.now(UTC).isoformat()

    approval_requests[request_id] = req

    return {"ok": True, "message": "Decision recorded"}
```

**Phase 2: Hook - Polling Loop**

```python
# File: agent-orchestrator-observability/hooks/pre_tool_hook.py

import httpx
import time
import json
import sys

def pre_tool_hook():
    input_data = json.loads(sys.stdin.read())

    session_id = input_data.get("session_id")
    tool_name = input_data.get("tool_name")
    tool_input = input_data.get("tool_input")

    observability_url = os.getenv("AGENT_ORCHESTRATOR_OBSERVABILITY_URL", "http://127.0.0.1:8765")

    try:
        # Step 1: Create approval request
        response = httpx.post(
            f"{observability_url}/create-approval-request",
            json={
                "session_id": session_id,
                "tool_name": tool_name,
                "tool_input": tool_input
            },
            timeout=5.0
        )

        request_id = response.json()["request_id"]

        # Step 2: Poll for decision (max 30 seconds total)
        start_time = time.time()
        max_wait = 30.0

        while time.time() - start_time < max_wait:
            response = httpx.get(
                f"{observability_url}/approval-requests/{request_id}/decision",
                params={"timeout": 5.0},  # Long-poll timeout
                timeout=6.0  # HTTP timeout slightly higher
            )

            if response.status_code == 200:
                # Decision made
                decision = response.json()["decision"]
                break
            elif response.status_code == 202:
                # Still pending, continue polling
                continue
            else:
                # Error
                decision = "deny"
                break
        else:
            # Overall timeout
            decision = "deny"

        # Return decision to SDK
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision
            }
        }
        print(json.dumps(result))
        sys.exit(0)

    except Exception as e:
        # Error - deny
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Error: {str(e)}"
            }
        }
        print(json.dumps(result))
        sys.exit(0)
```

**Phase 3: Frontend - Same as Approach 2**

Uses same approval UI, but posts to different endpoint:
```typescript
const approve = async (requestId: string) => {
  await observabilityApi.post(`/approval-requests/${requestId}/decide`, {
    decision: 'allow'
  });
};
```

### 5.3 Evaluation

#### Pros
- ✅ **No held connections**: Polling releases connection between polls
- ✅ **Backend friendly**: Less resource intensive than blocking
- ✅ **Resilient**: Backend restart doesn't lose requests if using SQLite
- ✅ **Simpler than Approach 1**: No temp servers
- ✅ **Timeout granular**: Can adjust poll interval and max wait separately
- ✅ **Request tracking**: Approval requests stored explicitly

#### Cons
- ❌ **Polling overhead**: Network traffic from repeated polling
- ❌ **Delayed response**: Up to poll_interval delay (0.5-5s)
- ❌ **More complex hook**: Hook has loop logic
- ❌ **Two HTTP calls**: Create + poll (vs one blocking call)

#### Scalability Analysis

**Network Overhead**:
- Polling interval: 0.5-5 seconds
- Max polling duration: 30 seconds
- Requests per hook: ~6-60 polls

**Resource Usage**:
- Memory: Approval requests stored (1KB each)
- Connections: Released between polls (better than blocking)

**Failure Modes**:
- Backend restart: Can persist to SQLite
- Network issues: Hook retries polls
- Timeout: Hook gives up after max wait

#### Implementation Complexity

| Component | Effort | Complexity |
|-----------|--------|-----------|
| Backend request creation | 1 day | LOW |
| Backend polling endpoint | 2 days | MEDIUM |
| Backend decision endpoint | 1 day | LOW |
| Hook polling logic | 2 days | MEDIUM |
| Frontend integration | 3 days | MEDIUM |
| **Total** | **9 days** | **MEDIUM** |

**Timeline**: 2-3 weeks

### 5.4 Recommendation

**Rating**: ✅ **RECOMMENDED FOR PRODUCTION**

**Use When**:
- Need production-grade reliability
- Backend resource constraints
- Want explicit request tracking

**Avoid When**:
- Need absolutely minimal latency (polling adds delay)
- Simplicity is paramount (Approach 2 simpler)

**Best For**: Production deployments, multiple concurrent users

---

## 6. Approach 4: Request/Response via Correlation ID

### 6.1 Architecture

**Concept**: Hook sends request with correlation ID, backend queues it, hook polls a dedicated "response queue" for its correlation ID. Frontend posts response with correlation ID.

```
┌─────────────────────────────────────────────────────────────┐
│  PreToolUse Hook                                            │
│  1. Generate correlation_id = uuid()                        │
│  2. POST /approval-queue with correlation_id                │
│  3. Poll GET /response-queue/{correlation_id}               │
│     - Returns response when available                       │
│  4. Return decision to SDK                                  │
└─────────────────────────────────────────────────────────────┘
            ▲
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│  Observability Backend                                       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Approval Queue (requests waiting for decision)      │   │
│  │  - Keyed by correlation_id                           │   │
│  │  - Contains tool info                                │   │
│  └──────────────────────────────────────────────────────┘   │
│              │                                               │
│              ▼ (matched by correlation_id)                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Response Queue (decisions from frontend)            │   │
│  │  - Keyed by correlation_id                           │   │
│  │  - Contains decision                                 │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
            ▲
            │
┌─────────────────────────────────────────────────────────────┐
│  Frontend                                                    │
│  1. Receives approval request via WebSocket                 │
│  2. User decides                                            │
│  3. POST /response-queue with correlation_id and decision   │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Implementation Details

**Similar to Approach 3, but**:
- Hook generates correlation_id client-side
- Two separate queues: approval queue (requests) and response queue (decisions)
- Explicit queue semantics for better scalability

**Key Difference from Approach 3**:
- Correlation ID generated by hook (not server)
- Clearer separation of request/response
- Better for distributed systems (could use Redis, etc.)

### 6.3 Evaluation

#### Pros
- ✅ **Most scalable**: Can replace in-memory with Redis/message queue
- ✅ **Distributed-ready**: Correlation ID pattern is industry standard
- ✅ **Clear semantics**: Request queue vs response queue
- ✅ **Production-grade**: Used in microservices architectures

#### Cons
- ❌ **More complex**: Two queues to manage
- ❌ **Overhead**: Correlation ID management
- ❌ **Over-engineered for local**: User's use case is local machine

#### Implementation Complexity

**Timeline**: 3-4 weeks (more complex than Approach 2/3)

### 6.4 Recommendation

**Rating**: ✅ **RECOMMENDED FOR PRODUCTION AT SCALE**

**Use When**:
- Need ultimate scalability
- Distributed deployment
- Multiple backend instances

**Avoid When**:
- Local use case only
- Simplicity preferred

**Best For**: Future scaling, multi-instance deployments

---

## 7. Approach 5: WebSocket from Hook

### 7.1 Architecture

**Concept**: Hook opens WebSocket connection to backend, waits for decision message.

```
┌─────────────────────────────────────────────────────────────┐
│  PreToolUse Hook (Python)                                   │
│  1. POST /request-approval → get request_id                 │
│  2. Open WebSocket: ws://backend/hook-ws/{request_id}       │
│  3. Wait for message with decision                          │
│  4. Close WebSocket                                         │
│  5. Return decision to SDK                                  │
└─────────────────────────────────────────────────────────────┘
            ▲
            │ WebSocket
            ▼
┌─────────────────────────────────────────────────────────────┐
│  Observability Backend                                       │
│  - WebSocket endpoint for hooks                             │
│  - When frontend posts decision, send via WebSocket         │
└─────────────────────────────────────────────────────────────┘
            ▲
            │ HTTP POST decision
┌─────────────────────────────────────────────────────────────┐
│  Frontend                                                    │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Evaluation

#### Pros
- ✅ **Real-time**: Instant decision delivery
- ✅ **Bidirectional**: WebSocket is inherently two-way

#### Cons
- ❌ **WebSocket in hook**: Python WebSocket client in short-lived script
- ❌ **Connection overhead**: Opening WebSocket takes time
- ❌ **Complexity**: More complex than HTTP polling
- ❌ **Error handling**: WebSocket disconnections

#### Implementation Complexity

**Timeline**: 3-4 weeks

### 7.3 Recommendation

**Rating**: 🟡 **VIABLE BUT COMPLEX**

**Avoid**: Complexity doesn't justify benefits over Approach 2/3

---

## 8. Approach 6: Server-Sent Events (SSE)

### 8.1 Architecture

**Concept**: Hook opens SSE connection, waits for decision event.

### 8.2 Evaluation

#### Pros
- ✅ **One-way push**: Simpler than WebSocket

#### Cons
- ❌ **SSE in Python**: Less common, fewer libraries
- ❌ **Still complex**: Similar issues to WebSocket approach

#### Implementation Complexity

**Timeline**: 3-4 weeks

### 8.3 Recommendation

**Rating**: ❌ **NOT RECOMMENDED**

**Avoid**: Same complexity as WebSocket with fewer benefits

---

## 9. Approach 7: Hybrid - Temp Server + Registry

### 9.1 Architecture

**Concept**: Combine Approach 1 (temp server) with centralized registry for better port management.

```
┌─────────────────────────────────────────────────────────────┐
│  Service Registry (in Observability Backend)                │
│  - Manages port allocation                                  │
│  - Tracks session → server URL mapping                      │
│  - Health checks on command servers                         │
└─────────────────────────────────────────────────────────────┘
            ▲
            │ Register/heartbeat
┌─────────────────────────────────────────────────────────────┐
│  AE Command Process                                         │
│  - Request port from registry                               │
│  - Start temp server on allocated port                      │
│  - Send heartbeats                                          │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 Evaluation

#### Pros
- ✅ **Centralized port management**: No conflicts
- ✅ **Health monitoring**: Registry knows if server died
- ✅ **Cleaner than Approach 1**: Coordinated port allocation

#### Cons
- ❌ **Very complex**: Registry + temp servers + health checks
- ❌ **Over-engineered**: Way too complex for local use case

#### Implementation Complexity

**Timeline**: 5-6 weeks

### 9.3 Recommendation

**Rating**: 🟡 **VIABLE FOR LARGE-SCALE PRODUCTION ONLY**

**Avoid for this use case**: Massive overkill for local development

---

## 10. Comparative Analysis

### 10.1 Decision Matrix

| Criteria | Approach 1 (Temp Server) | Approach 2 (Blocking) | Approach 3 (Long-Poll) | Approach 4 (Correlation) | Approach 5 (WebSocket) | Approach 7 (Hybrid) |
|----------|-------------------------|---------------------|---------------------|----------------------|---------------------|-------------------|
| **Simplicity** | LOW | HIGH | MEDIUM | MEDIUM | LOW | VERY LOW |
| **Scalability** | LOW | MEDIUM | MEDIUM | HIGH | MEDIUM | HIGH |
| **Reliability** | MEDIUM | HIGH | HIGH | HIGH | MEDIUM | HIGH |
| **Local Use Case Fit** | MEDIUM | EXCELLENT | GOOD | POOR | MEDIUM | POOR |
| **Production Ready** | NO | YES* | YES | YES | YES | YES |
| **Implementation Time** | 3-4 weeks | 2-3 weeks | 2-3 weeks | 3-4 weeks | 3-4 weeks | 5-6 weeks |
| **Resource Usage** | HIGH | MEDIUM | LOW | LOW | MEDIUM | HIGH |
| **Port Management** | COMPLEX | NONE | NONE | NONE | NONE | MANAGED |
| **Multiple Frontends** | YES | NO* | YES | YES | YES | YES |

*Approach 2 works but first response wins (acceptable for local use case per user)

### 10.2 Use Case Recommendation

**For User's Stated Use Case** (local machine, unlikely multiple frontends):

**RECOMMENDED: Approach 2 (Blocking HTTP with Response)**

**Reasons**:
1. ✅ Simplest implementation (2-3 weeks)
2. ✅ Leverages existing observability backend
3. ✅ No port management complexity
4. ✅ No service discovery needed
5. ✅ Perfect for single user, local development
6. ✅ "First response wins" acceptable when only one frontend

**Alternative for Future Scaling**:

**Approach 3 (Long-Polling Pattern)**

**Reasons**:
1. ✅ Similar timeline (2-3 weeks)
2. ✅ Better resource usage (no held connections)
3. ✅ More resilient to backend restarts
4. ✅ Easier to add multiple frontend support later
5. ✅ Production-grade pattern

### 10.3 Two-Phase Recommendation

**Phase 1: Implement Approach 2** (2-3 weeks)
- Quick win for local use case
- Validate UX and workflows
- Collect user feedback

**Phase 2: Migrate to Approach 3 if needed** (1-2 weeks)
- If multiple frontends become important
- If resource usage becomes concern
- If production deployment needed

**Migration Path**: Easy migration (similar APIs, change hook from blocking to polling)

---

## 11. Implementation Recommendations

### 11.1 Recommended Implementation: Approach 2

**Full Implementation Plan**:

#### Week 1: Backend Foundation

**Days 1-2: Pending Request Storage**
```python
# File: agent-orchestrator-observability/backend/main.py

# Add to existing backend
pending_requests: Dict[str, PendingRequest] = {}

class PendingRequest:
    def __init__(self, ...):
        self.future = asyncio.Future()
        # ... other fields

@app.post("/request-approval")
async def request_approval(request: dict):
    # Create request, broadcast to frontend, wait for response
    # (See full implementation in Approach 2 section)
    pass

@app.post("/tool-decisions/{request_id}/respond")
async def respond_to_approval(request_id: str, response: dict):
    # Resolve future, unblock waiting request
    pass
```

**Days 3-4: Stop Mechanism**
```python
# Similar pattern for stop requests
stop_requests: Dict[str, asyncio.Event] = {}

@app.post("/sessions/{session_id}/request-stop")
async def request_stop(session_id: str):
    # Set stop event
    pass

@app.get("/check-stop/{session_id}")
async def check_stop(session_id: str):
    # Return stop status
    pass
```

**Day 5: Testing**
- Unit tests for request/response matching
- Timeout tests
- Error handling tests

#### Week 2: Hook Integration

**Days 1-2: PreToolUse Hook**
```python
# File: hooks/pre_tool_hook.py

def pre_tool_hook():
    # Blocking request to /request-approval
    # Return decision to SDK
    pass
```

**Day 3: Message Loop Stop Check**
```python
# File: lib/claude_client.py

async def run_claude_session(...):
    # In message loop, periodically check stop
    async for message in client.receive_response():
        # ... process message ...

        # Check for stop
        if await check_stop_requested(session_id):
            break
```

**Days 4-5: Testing**
- Integration tests with real SDK
- Timeout scenarios
- Error handling

#### Week 3: Frontend UI

**Days 1-2: Approval Modal**
```typescript
// File: components/ApprovalModal.tsx
export const ApprovalModal = () => {
  // Show pending approval requests
  // Approve/Deny buttons
  // Countdown timer
};
```

**Day 3: WebSocket Integration**
```typescript
// File: hooks/useApprovalRequests.ts
export const useApprovalRequests = () => {
  // Subscribe to approval_request messages
  // API calls to approve/deny
};
```

**Days 4-5: Stop Button UI**
```typescript
// File: components/SessionDetails.tsx
// Add Stop button
// Show stopping state
// Listen for session_stop event
```

#### Post-Implementation: Testing & Documentation

**Week 4 (Optional): Polish & Production**
- End-to-end testing
- Performance testing (concurrent approvals)
- Error scenario testing
- Documentation
- User guide

### 11.2 Configuration

**Hook Timeout Configuration**:

```json
// File: .claude/settings.json or hooks.example.json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "python hooks/pre_tool_hook.py",
        "timeout": 35000  // 35 seconds (30s wait + 5s buffer)
      }]
    }]
  }
}
```

**Environment Variables**:
```bash
# Extended timeout for approval requests
AGENT_ORCHESTRATOR_APPROVAL_TIMEOUT=30

# Observability URL
AGENT_ORCHESTRATOR_OBSERVABILITY_URL=http://127.0.0.1:8765
```

### 11.3 Database Schema

**No new tables needed for Approach 2** (in-memory storage).

**Optional: Persist approval requests for auditing**:

```sql
CREATE TABLE approval_requests (
    request_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    tool_input TEXT,  -- JSON
    status TEXT NOT NULL,  -- pending, approved, denied, timeout
    decision TEXT,
    created_at TEXT NOT NULL,
    decided_at TEXT,
    timeout_at TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX idx_approval_requests_session ON approval_requests(session_id);
CREATE INDEX idx_approval_requests_status ON approval_requests(status);
```

---

## 12. Technical Specifications

### 12.1 API Contracts

#### For Approach 2 (Recommended)

**Request Approval** (Hook → Backend):
```
POST /request-approval

Request Body:
{
  "session_id": "uuid",
  "tool_name": "Bash",
  "tool_input": {
    "command": "npm run build"
  }
}

Response (on approval):
{
  "decision": "allow",
  "request_id": "uuid"
}

Response (on denial):
{
  "decision": "deny",
  "request_id": "uuid",
  "reason": "User denied"
}

Response (on timeout):
{
  "decision": "deny",
  "request_id": "uuid",
  "reason": "timeout"
}

Timeout: 30 seconds
```

**Respond to Approval** (Frontend → Backend):
```
POST /tool-decisions/{request_id}/respond

Request Body:
{
  "decision": "allow"  // or "deny"
}

Response:
{
  "ok": true,
  "message": "Decision recorded"
}

Errors:
404 - Request not found or already completed
400 - Invalid decision value
```

**Request Stop** (Frontend → Backend):
```
POST /sessions/{session_id}/request-stop

Request Body: (empty)

Response:
{
  "ok": true,
  "message": "Stop requested"
}

Errors:
404 - Session not found
```

**Check Stop** (Message Loop → Backend):
```
GET /check-stop/{session_id}

Response:
{
  "stop_requested": true  // or false
}
```

#### WebSocket Messages

**Approval Request** (Backend → Frontend):
```json
{
  "type": "approval_request",
  "request_id": "uuid",
  "session_id": "uuid",
  "tool_name": "Bash",
  "tool_input": {
    "command": "npm run build"
  },
  "timeout": 30.0,
  "created_at": "2025-11-25T..."
}
```

**Stop Requested** (Backend → Frontend):
```json
{
  "type": "session_stopping",
  "session_id": "uuid"
}
```

### 12.2 Hook Return Value Format

**For SDK Permission Decision**:

```python
# Success - Allow
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow"
  }
}

# Success - Deny
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "User denied this operation"
  }
}

# Success - Ask (let SDK handle)
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask"
  }
}
```

### 12.3 Error Handling Strategy

**Hook Timeout Handling**:
```python
try:
    response = httpx.post(..., timeout=30.0)
    decision = response.json()["decision"]
except httpx.TimeoutException:
    # Default to deny on timeout
    decision = "deny"
    reason = "User approval timeout (30s)"
except Exception as e:
    # Default to deny on any error
    decision = "deny"
    reason = f"Error requesting approval: {str(e)}"

# Always return valid response to SDK
return {
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": reason
    }
}
```

**Backend Error Handling**:
```python
@app.post("/request-approval")
async def request_approval(request: dict):
    try:
        # ... create request, wait for response ...
        pass
    except asyncio.TimeoutError:
        # Timeout waiting for frontend
        return {"decision": "deny", "reason": "timeout"}
    except Exception as e:
        # Unexpected error
        logging.error(f"Error in request_approval: {e}")
        return {"decision": "deny", "reason": "internal_error"}
```

---

## Conclusion

After comprehensive evaluation of 7 architectural approaches for HTTP-based two-way communication, the analysis concludes:

### Primary Recommendation: Approach 2 (Blocking HTTP with Response)

**Why**:
1. ✅ Best fit for stated use case (local machine, single user)
2. ✅ Simplest implementation (2-3 weeks)
3. ✅ Leverages existing infrastructure
4. ✅ No port management complexity
5. ✅ "First response wins" acceptable for local use

**Implementation**:
- Hook makes blocking HTTP POST to observability backend
- Backend holds request open (async Future pattern)
- Frontend posts decision via separate endpoint
- Backend resolves Future, returns decision to hook
- Hook returns decision to SDK

**Timeline**: 2-3 weeks

### Alternative Recommendation: Approach 3 (Long-Polling)

**Why**:
- Better resource usage (no held connections)
- More resilient to backend restarts
- Production-grade pattern
- Similar timeline (2-3 weeks)

**When to Choose**:
- If resource efficiency is priority
- If backend restarts are common
- If future scaling to production is likely

### Not Recommended for This Use Case:
- ❌ Approach 1 (Temp Server): Too complex, port management issues
- ❌ Approach 4 (Correlation ID): Over-engineered for local use
- ❌ Approach 5 (WebSocket): Unnecessary complexity
- ❌ Approach 6 (SSE): Same issues as WebSocket
- ❌ Approach 7 (Hybrid): Massive overkill

### Migration Path:
If scaling becomes necessary:
1. Start with Approach 2 (2-3 weeks)
2. Validate UX and collect feedback
3. Migrate to Approach 3 if needed (1-2 weeks)
4. Easy migration path (similar APIs)

### Key Enabler:
**Extended hook timeout** - With ability to extend hook timeout beyond 2 seconds, HTTP-based request/response patterns become viable for interactive approvals.

---

**End of Document**
