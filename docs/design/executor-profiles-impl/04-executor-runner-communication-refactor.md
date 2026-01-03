# Session 4: Executor-Runner Communication via Runner Gateway

**Status:** Implemented
**Prerequisite:** Understanding of executor profiles system
**Design Document:** [`../executor-profiles.md`](../executor-profiles.md)

---

## Architecture Overview

Executors communicate with the Agent Coordinator through the **Runner Gateway**, a local HTTP server that:
- Handles authentication (Auth0 M2M tokens)
- Enriches requests with runner-owned data
- Routes requests to the appropriate Coordinator endpoints

This ensures proper separation of concerns: **each component only sends data it owns**.

---

## Information Ownership

| Property | Owned By | Sent By |
|----------|----------|---------|
| `hostname` | Runner | Runner (via gateway) |
| `executor_profile` | Runner | Runner (via gateway) |
| `executor_session_id` | Executor | Executor |
| `project_dir` | Executor (per-invocation) | Executor |

**Note:** `project_dir` is per-invocation because a single runner can spawn multiple executor instances with different working directories.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Agent Runner                                │
│  Owns: hostname, executor_profile                                   │
│                                                                     │
│   ┌──────────────────────────────────────────────────────────────┐  │
│   │  Runner Gateway                                               │  │
│   │  http://127.0.0.1:{port}                                      │  │
│   │                                                               │  │
│   │  POST /bind      → Enriches with hostname, executor_profile   │  │
│   │  POST /events    → Forwards to coordinator                    │  │
│   │  PATCH /metadata → Forwards to coordinator                    │  │
│   │  /* (other)      → Forwards to coordinator                    │  │
│   └──────────────────────────────────────────────────────────────┘  │
│         ▲                                                           │
│         │ HTTP                                                      │
│   ┌─────┴──────────────────────────────────────────────────────┐   │
│   │  Executor Instance                                          │   │
│   │  - Uses session_client.py                                   │   │
│   │  - Sends only: executor_session_id, project_dir             │   │
│   └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
         │
         │ HTTP (with auth)
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Agent Coordinator                              │
│  Receives complete payloads (API unchanged)                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Gateway Endpoints

### POST /bind

Binds an executor to a session after the framework provides its session ID.

**Executor sends:**
```json
{
  "session_id": "ses_abc123",
  "executor_session_id": "uuid-from-claude-sdk",
  "project_dir": "/path/to/project"
}
```

**Gateway enriches and forwards to `POST /sessions/{session_id}/bind`:**
```json
{
  "executor_session_id": "uuid-from-claude-sdk",
  "hostname": "machine-hostname",
  "executor_profile": "coding",
  "project_dir": "/path/to/project"
}
```

### POST /events

Adds an event to a session. Gateway extracts `session_id` from body to route correctly.

**Executor sends:**
```json
{
  "session_id": "ses_abc123",
  "event_type": "message",
  "role": "user",
  "content": [{"type": "text", "text": "Hello"}]
}
```

**Gateway forwards to `POST /sessions/{session_id}/events`.**

### PATCH /metadata

Updates session metadata.

**Executor sends:**
```json
{
  "session_id": "ses_abc123",
  "last_resumed_at": "2024-01-15T10:30:00Z"
}
```

**Gateway forwards to `PATCH /sessions/{session_id}/metadata`.**

---

## Key Components

| Component | Location | Role |
|-----------|----------|------|
| Runner Gateway | `servers/agent-runner/lib/runner_gateway.py` | Local HTTP server that enriches and routes requests |
| Session Client | `servers/agent-runner/lib/session_client.py` | HTTP client for executor-to-gateway communication |
| Agent Runner | `servers/agent-runner/agent-runner` | Creates gateway with runner-owned data |
| Claude Executor | `servers/agent-runner/executors/claude-code/lib/claude_client.py` | Uses session_client to bind and send events |
| Test Executor | `servers/agent-runner/executors/test-executor/ao-test-exec` | Simple executor for testing |

---

## Session Client API

The session client provides a simplified interface for executors:

```python
from session_client import SessionClient

client = SessionClient(api_url)  # api_url points to Runner Gateway

# Bind executor to session (gateway adds hostname, executor_profile)
client.bind(
    session_id="ses_abc123",
    executor_session_id="uuid-from-sdk",
    project_dir="/path/to/project",  # Optional
)

# Add event (gateway routes to correct coordinator endpoint)
client.add_event(session_id, {
    "event_type": "message",
    "role": "user",
    "content": [{"type": "text", "text": "Hello"}]
})

# Update metadata
client.update_session(
    session_id="ses_abc123",
    last_resumed_at="2024-01-15T10:30:00Z"
)
```

---

## Runner Gateway Configuration

The gateway is initialized with runner-owned data:

```python
from runner_gateway import RunnerGateway

gateway = RunnerGateway(
    coordinator_url="http://localhost:8765",
    auth0_client=auth0_client,  # For M2M authentication
    hostname="machine-hostname",
    executor_profile="coding",
)

gateway.start()  # Binds to dynamic port
os.environ["AGENT_ORCHESTRATOR_API_URL"] = gateway.url  # Executors use this
```

---

## Benefits

1. **Clean separation of concerns**: Executors only send data they own
2. **Single point of authentication**: Gateway handles all auth
3. **Simplified executor code**: No need for hostname lookup or profile knowledge
4. **Future-proof**: Easy to add event batching, caching, or other runner-level features
5. **Coordinator API unchanged**: No changes required to Agent Coordinator

---

## Implementation Checklist

- [x] Created `runner_gateway.py` with route handlers
- [x] Updated `agent-runner` to pass runner config to gateway
- [x] Simplified `session_client.py` bind method
- [x] Updated `claude_client.py` to use simplified bind
- [x] Updated `ao-test-exec` to use simplified bind
- [x] Removed old `coordinator_proxy.py`
