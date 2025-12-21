# SSE Sessions Architecture

Server-Sent Events implementation for real-time session streaming.

**ADR Reference:** [ADR-013: WebSocket to SSE Migration](../adr/ADR-013-websocket-to-sse-migration.md)

## Overview

Replace the existing WebSocket endpoint (`/ws`) with an SSE endpoint (`/sse/sessions`) that provides:

- Standard HTTP authentication
- Server-side filtering by session/user
- Built-in reconnection with resume support
- Same event types and payloads as current WebSocket

## Endpoint Design

### URL Structure

```
GET /sse/sessions
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string | Filter to single session |
| `created_by` | string | Filter to sessions created by user |
| `include_init` | boolean | Include initial state on connect (default: true) |

### Examples

```bash
# Admin: all sessions
GET /sse/sessions

# Admin: specific session
GET /sse/sessions?session_id=abc123

# User: own sessions only (enforced by auth)
GET /sse/sessions

# Skip initial state (reconnection with Last-Event-ID)
GET /sse/sessions?include_init=false
```

## Authentication

SSE uses standard HTTP, so authentication works normally:

### Method 1: Authorization Header (Non-Browser Clients)

```python
# Agent Runner, CLI tools
import httpx

async with httpx.AsyncClient() as client:
    async with client.stream(
        "GET",
        "https://coordinator/sse/sessions",
        headers={"Authorization": "Bearer xxx"}
    ) as response:
        async for line in response.aiter_lines():
            # Process SSE events
```

### Method 2: Cookies (Dashboard)

```javascript
// Browser with credentials
const eventSource = new EventSource("/sse/sessions", {
  withCredentials: true
});
```

### Method 3: Fetch API with Headers (Dashboard Alternative)

```javascript
// When cookie auth isn't suitable
const response = await fetch("/sse/sessions", {
  headers: { "Authorization": `Bearer ${token}` }
});

const reader = response.body.getReader();
const decoder = new TextDecoder();
// Process SSE stream...
```

## Event Format

### SSE Structure

Each event includes three fields:

```
id: <event_id>
event: <event_type>
data: <json_payload>

```

Note: Double newline (`\n\n`) separates events.

### Event ID Format

```
<timestamp_ms>-<event_type_short>-<sequence>
```

Examples:
```
id: 1703123456789-ini-001
id: 1703123456790-scr-001
id: 1703123456791-sup-002
id: 1703123456792-evt-001
```

**Type abbreviations:**
| Abbreviation | Event Type |
|--------------|------------|
| `ini` | init |
| `scr` | session_created |
| `sup` | session_updated |
| `sdl` | session_deleted |
| `evt` | event |
| `rfl` | run_failed |

**Why this format?**
- Timestamp enables time-based resume
- Type abbreviation aids debugging
- Sequence handles same-millisecond events

### Event Types

Same as current WebSocket:

#### `init` - Initial State

Sent on connection (unless `include_init=false`):

```
id: 1703123456789-ini-001
event: init
data: {"sessions": [{"session_id": "abc", "status": "running", ...}, ...]}

```

#### `session_created` - New Session

```
id: 1703123456790-scr-001
event: session_created
data: {"session": {"session_id": "abc", "status": "pending", ...}}

```

#### `session_updated` - Session Changed

```
id: 1703123456791-sup-001
event: session_updated
data: {"session": {"session_id": "abc", "status": "running", ...}}

```

#### `session_deleted` - Session Removed

```
id: 1703123456792-sdl-001
event: session_deleted
data: {"session_id": "abc"}

```

#### `event` - Session Event (Tool Call, Message, etc.)

```
id: 1703123456793-evt-001
event: event
data: {"session_id": "abc", "event_type": "tool_call", "tool_name": "Read", ...}

```

#### `run_failed` - Run Timeout/Failure

```
id: 1703123456794-rfl-001
event: run_failed
data: {"run_id": "run-123", "session_id": "abc", "error": "No matching runner"}

```

## Resume Support

### How It Works

1. Client connects, receives events with IDs
2. Connection drops
3. Browser automatically reconnects with `Last-Event-ID` header
4. Server resumes from that point

### Server Implementation

```python
@app.get("/sse/sessions")
async def sse_sessions(
    request: Request,
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
    session_id: Optional[str] = None,
    include_init: bool = True,
):
    # Parse last_event_id to determine resume point
    resume_from = parse_event_id(last_event_id) if last_event_id else None

    async def event_generator():
        # Send init if requested and not resuming
        if include_init and not resume_from:
            sessions = get_filtered_sessions(request.user)
            yield format_sse("init", {"sessions": sessions}, "ini")

        # Stream events (from resume point if applicable)
        async for event in get_event_stream(resume_from, session_id, request.user):
            yield format_sse(event.type, event.data, event.type_abbrev)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
```

### Event ID Parsing

```python
def parse_event_id(event_id: str) -> Optional[tuple[int, str, int]]:
    """Parse event ID into (timestamp_ms, type, sequence)."""
    if not event_id:
        return None
    try:
        parts = event_id.split("-")
        return (int(parts[0]), parts[1], int(parts[2]))
    except (IndexError, ValueError):
        return None
```

### Considerations

- **Event buffering:** Server needs to buffer recent events for resume
- **Buffer size:** Configure based on expected disconnect duration (e.g., last 5 minutes)
- **Missed events:** If `Last-Event-ID` is too old, send full `init` instead

## Filtering Logic

### Admin Role

No filtering - receives all events.

```python
def get_filtered_sessions(user) -> list[Session]:
    if user.role == "admin":
        return get_all_sessions()
    ...
```

### User Role

Server enforces access control:

```python
def get_filtered_sessions(user) -> list[Session]:
    if user.role == "user":
        return get_sessions_by_creator(user.user_id)
    ...

def should_send_event(event, user) -> bool:
    if user.role == "admin":
        return True
    if user.role == "user":
        return event.session_id in user.accessible_sessions
    return False
```

### Query Parameter Filtering

Additional filtering on top of role-based access:

```python
@app.get("/sse/sessions")
async def sse_sessions(
    session_id: Optional[str] = None,
    # ...
):
    # Role-based filtering first
    accessible = get_accessible_sessions(request.user)

    # Then apply query param filter
    if session_id:
        if session_id not in accessible:
            raise HTTPException(403, "Access denied")
        accessible = {session_id}
```

## Connection Management

### Server-Side

```python
# Track active SSE connections
sse_connections: dict[str, set[SSEConnection]] = {}

class SSEConnection:
    user_id: str
    role: str
    filters: dict  # session_id, created_by filters
    queue: asyncio.Queue
```

### Broadcasting Events

Replace WebSocket broadcast with SSE broadcast:

```python
async def broadcast_event(event_type: str, data: dict):
    """Broadcast to all SSE connections (with filtering)."""
    message = format_sse(event_type, data)

    for conn in sse_connections.values():
        if should_send_event(data, conn.user, conn.filters):
            await conn.queue.put(message)
```

### Heartbeat (Keep-Alive)

SSE connections can timeout. Send periodic comments:

```python
async def event_generator():
    while True:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=30)
            yield event
        except asyncio.TimeoutError:
            # Send SSE comment as heartbeat
            yield ": heartbeat\n\n"
```

## Client Implementation

### Dashboard (React)

```typescript
// hooks/useSSE.ts
export function useSSE(filters?: { sessionId?: string }) {
  const [sessions, setSessions] = useState<Session[]>([]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (filters?.sessionId) params.set("session_id", filters.sessionId);

    const eventSource = new EventSource(
      `/sse/sessions?${params}`,
      { withCredentials: true }
    );

    eventSource.addEventListener("init", (e) => {
      const { sessions } = JSON.parse(e.data);
      setSessions(sessions);
    });

    eventSource.addEventListener("session_created", (e) => {
      const { session } = JSON.parse(e.data);
      setSessions(prev => [...prev, session]);
    });

    eventSource.addEventListener("session_updated", (e) => {
      const { session } = JSON.parse(e.data);
      setSessions(prev => prev.map(s =>
        s.session_id === session.session_id ? session : s
      ));
    });

    eventSource.addEventListener("session_deleted", (e) => {
      const { session_id } = JSON.parse(e.data);
      setSessions(prev => prev.filter(s => s.session_id !== session_id));
    });

    eventSource.addEventListener("event", (e) => {
      const event = JSON.parse(e.data);
      // Handle session events (tool calls, messages, etc.)
    });

    eventSource.onerror = () => {
      // EventSource auto-reconnects, just log
      console.log("SSE connection error, reconnecting...");
    };

    return () => eventSource.close();
  }, [filters?.sessionId]);

  return { sessions };
}
```

### Agent Runner (Python)

```python
import httpx

async def subscribe_to_sessions(token: str, session_id: Optional[str] = None):
    """Subscribe to session events via SSE."""
    url = "https://coordinator/sse/sessions"
    if session_id:
        url += f"?session_id={session_id}"

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "GET",
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=None,
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    yield data
                elif line.startswith("event: "):
                    event_type = line[7:]
                    # Next data line belongs to this event type
```

## Migration Path

### Phase 1: Add SSE Endpoint

1. Implement `/sse/sessions` endpoint
2. Add to Coordinator alongside existing `/ws`
3. Test with curl/httpie

### Phase 2: Update Dashboard

1. Create `useSSE` hook
2. Replace `WebSocketContext` with `SSEContext`
3. Update components to use new context
4. Test reconnection, filtering

### Phase 3: Deprecate WebSocket

1. Add deprecation warning to `/ws`
2. Monitor for remaining WebSocket usage
3. Remove `/ws` endpoint after migration period

## Testing

### Manual Testing

```bash
# Test SSE endpoint
curl -N -H "Authorization: Bearer xxx" \
  "http://localhost:8765/sse/sessions"

# Test with session filter
curl -N -H "Authorization: Bearer xxx" \
  "http://localhost:8765/sse/sessions?session_id=abc123"

# Test resume with Last-Event-ID
curl -N -H "Authorization: Bearer xxx" \
  -H "Last-Event-ID: 1703123456789-evt-001" \
  "http://localhost:8765/sse/sessions"
```

### Integration Tests

```python
async def test_sse_receives_session_created():
    """SSE stream receives session_created event."""
    async with sse_client("/sse/sessions") as events:
        # Create session via REST
        await create_session("test-session")

        # Should receive event
        event = await events.get(timeout=5)
        assert event["type"] == "session_created"
        assert event["session"]["session_id"] == "test-session"

async def test_sse_filtering_by_session():
    """SSE stream only receives events for filtered session."""
    async with sse_client("/sse/sessions?session_id=abc") as events:
        # Create unrelated session
        await create_session("other-session")

        # Should not receive event (wrong session)
        with pytest.raises(asyncio.TimeoutError):
            await events.get(timeout=1)
```
