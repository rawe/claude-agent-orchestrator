# Runner Gateway API

The Runner Gateway is a local HTTP server that executors use to communicate with the Agent Coordinator. It enriches requests with runner-owned data before forwarding.

**Base URL:** `http://127.0.0.1:{dynamic_port}` (set via `AGENT_ORCHESTRATOR_API_URL`)

---

## Gateway-Specific Endpoints

These endpoints exist **only on the Runner Gateway**, not on the Agent Coordinator. The gateway transforms and routes them to the appropriate Coordinator endpoints.

### POST /bind

Binds an executor to a session.

**Request:**
```json
{
  "session_id": "string (required)",
  "executor_session_id": "string (required)",
  "project_dir": "string (optional)"
}
```

**Gateway enriches with:**
- `hostname` - Machine hostname (from runner)
- `executor_profile` - Profile name (from runner)

**Forwards to Coordinator:** `POST /sessions/{session_id}/bind`

---

### POST /events

Adds an event to a session.

**Request:**
```json
{
  "session_id": "string (required)",
  "event_type": "string (required)",
  "...": "additional event fields"
}
```

**Forwards to Coordinator:** `POST /sessions/{session_id}/events`

---

### PATCH /metadata

Updates session metadata.

**Request:**
```json
{
  "session_id": "string (required)",
  "last_resumed_at": "string (optional)",
  "executor_session_id": "string (optional)"
}
```

**Forwards to Coordinator:** `PATCH /sessions/{session_id}/metadata`

---

## Transparent Forwarding

All other paths are forwarded to the Agent Coordinator as-is with authentication headers injected.

---

## Flow Diagram

```
Executor                     Runner Gateway                Agent Coordinator
   │                              │                              │
   │  POST /bind                  │                              │
   │  {session_id,                │                              │
   │   executor_session_id,       │                              │
   │   project_dir}               │                              │
   ├─────────────────────────────►│                              │
   │                              │                              │
   │                              │  Enrich:                     │
   │                              │  + hostname                  │
   │                              │  + executor_profile          │
   │                              │                              │
   │                              │  POST /sessions/{id}/bind    │
   │                              │  {executor_session_id,       │
   │                              │   hostname,                  │
   │                              │   executor_profile,          │
   │                              │   project_dir}               │
   │                              ├─────────────────────────────►│
   │                              │                              │
   │                              │◄─────────────────────────────┤
   │◄─────────────────────────────┤                              │
```

---

## Information Ownership

| Property | Owner | Provided By |
|----------|-------|-------------|
| `executor_session_id` | Executor | Executor |
| `project_dir` | Executor | Executor (per-invocation) |
| `hostname` | Runner | Gateway (enriched) |
| `executor_profile` | Runner | Gateway (enriched) |

---

## Implementation

- **Source:** `lib/runner_gateway.py`
- **Client:** `lib/session_client.py`
