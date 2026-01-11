# ADR-013: WebSocket to Server-Sent Events Migration

**Status:** Accepted
**Date:** 2025-12-21
**Decision Makers:** Architecture Review
**Related:** [SSE Architecture](../architecture/sse-sessions.md)

## Context

The Agent Coordinator uses WebSocket (`/ws`) to broadcast real-time session updates to the Dashboard. As we plan to expose the Coordinator to the public internet with authentication (see `docs/architecture/auth-coordinator.md`), we evaluated the streaming architecture.

### Current WebSocket Implementation

- **Endpoint:** `ws://localhost:8765/ws`
- **Direction:** Server → Client (broadcast only)
- **Client messages:** None (connection kept alive with receive loop)
- **Filtering:** None - all events to all clients
- **Event types:** `init`, `event`, `session_created`, `session_updated`, `session_deleted`, `run_failed`

### Key Observation

The WebSocket is used **unidirectionally**. The Dashboard receives events but never sends commands through the WebSocket - all mutations use REST endpoints. This is a pure broadcast channel.

### Problems with WebSocket for Authentication

1. **No standard auth mechanism:** Browsers cannot send `Authorization` headers during WebSocket handshake
2. **Token in URL:** Query parameter tokens appear in server logs, browser history
3. **Protocol complexity:** Separate ws:// protocol complicates proxy configuration
4. **No built-in resume:** Must implement reconnection and state recovery manually

## Decision

Replace WebSocket with **Server-Sent Events (SSE)** for real-time session streaming.

### New Endpoint Structure

```
GET /sse/sessions                     # Global stream (admin)
GET /sse/sessions?session_id=xxx      # Single session stream
GET /sse/sessions?created_by=user123  # User's sessions only
```

### Authentication Model

| Role | Access |
|------|--------|
| **Admin** | Global stream, all events |
| **User** | Filtered stream, own sessions only |

### Event Format

SSE with `id`, `event`, and `data` fields:

```
id: 1703123456789-evt-001
event: session_updated
data: {"session_id": "abc", "status": "running", ...}

id: 1703123456790-evt-002
event: event
data: {"session_id": "abc", "event_type": "tool_call", ...}
```

### Deprecation Path

1. **Phase 1:** Add `/sse/sessions` endpoint alongside existing `/ws`
2. **Phase 2:** Migrate Dashboard to SSE
3. **Phase 3:** Deprecate `/ws` endpoint

## Rationale

### Why SSE Over WebSocket?

| Aspect | WebSocket | SSE |
|--------|-----------|-----|
| **Direction needed** | Bidirectional | Server → Client |
| **Our usage** | Server → Client only | Server → Client |
| **HTTP Auth** | Not supported (browser) | Standard headers/cookies |
| **Auto-reconnect** | Manual implementation | Built into EventSource API |
| **Resume support** | Manual implementation | `Last-Event-ID` header |
| **Proxy compatibility** | May be blocked | Standard HTTP |
| **Protocol** | ws:// (separate) | https:// (standard) |
| **Complexity** | Higher | Lower |

**WebSocket's bidirectional capability is unused.** SSE provides the same functionality with simpler authentication and better browser support.

### Why Not Keep WebSocket?

1. **Authentication complexity:** Secure WebSocket auth requires workarounds (cookies, subprotocol hack, first-message auth)
2. **No benefit:** We don't use client-to-server messaging
3. **Maintenance burden:** Two streaming protocols to maintain

### Why Filtered Streams?

The current WebSocket broadcasts all events to all clients. With authentication and roles:

- **Admin** needs all events (monitoring, debugging)
- **User** should only see their own sessions (security, privacy, efficiency)

Server-side filtering:
- Reduces bandwidth for user clients
- Enforces access control at the source
- Enables session-specific event IDs (better resume)

## Consequences

### Positive

- **Simple auth:** Standard HTTP headers work (`Authorization: Bearer xxx`)
- **Cookie support:** Dashboard can use HttpOnly session cookies
- **Auto-reconnect:** Browser's EventSource handles reconnection
- **Resume capability:** `Last-Event-ID` enables seamless recovery
- **Proxy-friendly:** Works through HTTP proxies without special configuration
- **Less code:** Remove WebSocket connection management from Dashboard
- **Better filtering:** Server-side filtering reduces client complexity

### Negative

- **Migration effort:** Dashboard must be updated to use SSE
- **EventSource limitation:** No custom headers in native API (use cookies or fetch fallback)
- **Text only:** SSE is UTF-8 text (not an issue - we send JSON)
- **HTTP/1.1 connection limit:** 6 connections per domain (HTTP/2 solves this)

### Neutral

- Event payload format remains the same (JSON)
- Same event types, same data structures
- `/ws` can remain during transition for backwards compatibility

## References

- [SSE Architecture](../architecture/sse-sessions.md) - Implementation details
- [Auth Architecture](../architecture/auth-coordinator.md) - Authentication design
- [MDN: Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [MDN: EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
