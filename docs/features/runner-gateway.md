# Runner Gateway

**Status:** Implemented
**Version:** 1.0

## Overview

The Runner Gateway is a local HTTP server within each Agent Runner that decouples executors from the Agent Coordinator. It provides a security boundary, handles authentication, and enriches requests with runner-owned data.

Executors communicate only with the gateway—they never interact directly with the Coordinator.

## Motivation

### The Problem: Tight Coupling

Before the Runner Gateway, executors needed to:

1. **Know coordinator credentials** - Each executor needed access to Auth0 M2M tokens
2. **Know runner context** - Executors had to know hostname, executor profile, etc.
3. **Handle authentication** - Every executor implemented token management

This created several issues:

| Issue | Impact |
|-------|--------|
| Security risk | Credentials scattered across executor processes |
| Code duplication | Every executor reimplemented auth logic |
| Tight coupling | Executors knew too much about coordinator API |
| Testing difficulty | Hard to test executors in isolation |

### The Solution: Gateway Pattern

The Runner Gateway solves this by acting as a proxy between executors and the Coordinator:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Before: Direct Communication                                       │
│                                                                     │
│  Executor ─────────────────────────────────────────► Coordinator    │
│  - Needs auth credentials                                           │
│  - Knows hostname, profile                                          │
│  - Implements token refresh                                         │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  After: Gateway Pattern                                             │
│                                                                     │
│  Executor ──► Runner Gateway ──► Coordinator                        │
│  - No credentials                                                   │
│  - Sends only executor-owned data                                   │
│  - Simple HTTP client                                               │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Concepts

### Information Ownership

The gateway enforces a clean separation of concerns based on who **owns** data:

| Property | Owner | Rationale |
|----------|-------|-----------|
| `executor_session_id` | Executor | Created by the AI framework (e.g., Claude SDK) |
| `project_dir` | Executor | Can vary per invocation within same runner |
| `hostname` | Runner | Machine identity, constant for runner lifetime |
| `executor_profile` | Runner | Configuration choice, set at runner startup |

**Principle:** Each component only sends data it owns. The gateway enriches requests with runner-owned data before forwarding.

### Request Enrichment

When an executor sends a request, the gateway adds runner context:

```
Executor sends:                    Gateway enriches and forwards:
┌────────────────────────┐         ┌────────────────────────────────┐
│ POST /bind             │         │ POST /sessions/{id}/bind       │
│ {                      │         │ Authorization: Bearer <token>  │
│   session_id,          │  ────►  │ {                              │
│   executor_session_id, │         │   executor_session_id,         │
│   project_dir          │         │   project_dir,                 │
│ }                      │         │   hostname,        ← enriched  │
└────────────────────────┘         │   executor_profile ← enriched  │
                                   │ }                              │
                                   └────────────────────────────────┘
```

### Authentication Boundary

The gateway is the **single point of authentication**:

- Runner authenticates to Coordinator (Auth0 M2M or API key)
- Gateway stores credentials and injects auth headers
- Executors make unauthenticated requests to localhost
- Credentials never leave the runner process

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Agent Runner                                │
│  Owns: hostname, executor_profile, auth credentials                 │
│                                                                     │
│   ┌──────────────────────────────────────────────────────────────┐  │
│   │  Runner Gateway (http://127.0.0.1:{port})                    │  │
│   │                                                               │  │
│   │  Gateway-specific endpoints:                                  │  │
│   │    POST /bind     → Enriches, forwards to /sessions/{}/bind  │  │
│   │    POST /events   → Routes to /sessions/{}/events            │  │
│   │    PATCH /metadata → Routes to /sessions/{}/metadata         │  │
│   │                                                               │  │
│   │  All other paths:                                             │  │
│   │    → Forward as-is with auth headers                         │  │
│   └──────────────────────────────────────────────────────────────┘  │
│         ▲                                                           │
│         │ HTTP (localhost, no auth)                                 │
│   ┌─────┴──────────────────────────────────────────────────────┐   │
│   │  Executor Instance                                          │   │
│   │  - Uses SessionClient (lib/session_client.py)               │   │
│   │  - Sends only: session_id, executor_session_id, project_dir │   │
│   └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
         │
         │ HTTP (with Authorization header)
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Agent Coordinator                              │
│  Receives complete payloads (API unchanged)                         │
└─────────────────────────────────────────────────────────────────────┘
```

## How It Works

### 1. Runner Startup

When the runner starts, it creates a gateway with runner-owned data:

```python
gateway = RunnerGateway(
    coordinator_url="http://localhost:8765",
    auth0_client=auth0_client,
    hostname="dev-machine",
    executor_profile="coding",
)
gateway.start()  # Binds to dynamic port
```

### 2. Executor Environment

The runner sets `AGENT_ORCHESTRATOR_API_URL` to point to the gateway before spawning executors:

```python
os.environ["AGENT_ORCHESTRATOR_API_URL"] = gateway.url  # e.g., http://127.0.0.1:54321
```

Executors use this URL without knowing it's a local gateway.

### 3. Executor Requests

Executors use `SessionClient` to communicate:

```python
from session_client import SessionClient

client = SessionClient(api_url)  # Points to gateway

# Bind to session (gateway adds hostname, executor_profile)
client.bind(
    session_id="ses_abc123",
    executor_session_id="uuid-from-sdk",
    project_dir="/path/to/project",
)

# Add event (gateway routes to correct endpoint)
client.add_event(session_id, {"event_type": "message", ...})
```

### 4. Gateway Processing

For each request, the gateway:

1. Receives request from executor
2. Enriches with runner data (if applicable)
3. Adds authentication headers
4. Forwards to Coordinator
5. Returns response to executor

## Benefits

| Benefit | Description |
|---------|-------------|
| **Security** | Credentials isolated in runner process |
| **Simplicity** | Executors are simple HTTP clients |
| **Decoupling** | Executors don't know Coordinator API details |
| **Testability** | Easy to mock gateway for executor testing |
| **Extensibility** | Gateway can add caching, batching, retry logic |
| **Multi-runner** | Each runner has own port, supports multiple per machine |

## Implementation

| Component | Location | Purpose |
|-----------|----------|---------|
| Runner Gateway | `servers/agent-runner/lib/runner_gateway.py` | Local HTTP server |
| Session Client | `servers/agent-runner/lib/session_client.py` | HTTP client for executors |
| Gateway startup | `servers/agent-runner/agent-runner` | Creates gateway with runner config |

## API Reference

For detailed endpoint documentation, see [Runner Gateway API](../../servers/agent-runner/docs/runner-gateway-api.md).

## References

- [Executor Profiles](./executor-profiles.md) - Uses Runner Gateway for executor-coordinator communication
- [ADR-010: Session Identity and Executor Abstraction](../adr/ADR-010-session-identity-and-executor-abstraction.md)
