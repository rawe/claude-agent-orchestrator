# Agent Coordinator Authentication Architecture

## Scope

Authentication applies **only to the Agent Coordinator** (port 8765). Explicitly excluded:
- Context Store (port 8766) - remains internal/local only
- MCP Servers - run as subprocesses, inherit caller's context

## Deployment Context

```
┌────────────────────────────────────────────────────────────────┐
│                         PUBLIC NET                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Agent Coordinator :8765                        │  │
│  │  ← PROTECTED (this document)                              │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                         LOCAL NET                              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐   │
│  │   Dashboard    │  │  Agent Runner  │  │ Context Store  │   │
│  │   (React App)  │  │   (Polling)    │  │  (Unprotected) │   │
│  └────────────────┘  └────────────────┘  └────────────────┘   │
└────────────────────────────────────────────────────────────────┘
```

## Access Roles

| Role | Purpose | Permissions |
|------|---------|-------------|
| **Admin** | Full system control | All API endpoints, all blueprints |
| **Runner** | Technical agent execution | Register, poll runs, report status, heartbeat |
| **User** | External API consumer | Start runs (limited blueprints), read session results |

### Permission Matrix

| Endpoint | Admin | Runner | User |
|----------|-------|--------|------|
| `POST /runner/register` | ✓ | ✓ | ✗ |
| `GET /runner/runs` (long-poll) | ✓ | ✓ | ✗ |
| `POST /runner/runs/{id}/status` | ✓ | ✓ | ✗ |
| `POST /runner/heartbeat` | ✓ | ✓ | ✗ |
| `POST /runs` (start agent run) | ✓ | ✗ | ✓ (filtered) |
| `GET /sessions/{id}` | ✓ | ✗ | ✓ (own runs) |
| `GET /sse/sessions` | ✓ | ✗ | ✓ (own runs) |
| `GET /blueprints` | ✓ | ✗ | ✓ (allowed only) |
| All other endpoints | ✓ | ✗ | ✗ |

### User Blueprint Filtering

Users can only:
- See blueprints explicitly assigned to them
- Start runs using those blueprints
- Access sessions they created

---

## Approach 1: Static API Keys (Simplest)

### Concept

Pre-generated API keys with embedded role. Keys stored in environment/config on Coordinator.

```
Authorization: Bearer ak_admin_xxxx...
Authorization: Bearer ak_runner_xxxx...
Authorization: Bearer ak_user_xxxx...
```

### Key Structure

```python
# Coordinator config (env or JSON file)
API_KEYS = {
    "ak_admin_a1b2c3...": {"role": "admin"},
    "ak_runner_d4e5f6...": {"role": "runner"},
    "ak_user_g7h8i9...": {"role": "user", "allowed_blueprints": ["agent-1", "agent-2"]},
}
```

### Client Configuration

| Client | Configuration |
|--------|--------------|
| Dashboard | `VITE_AGENT_COORDINATOR_API_KEY` env var |
| Agent Runner | `AGENT_ORCHESTRATOR_API_KEY` env var |
| External Users | Receive key via secure channel |

### Pros & Cons

| Pros | Cons |
|------|------|
| Very simple to implement | No expiration (manual rotation) |
| Stateless validation | Key compromise = full role access |
| Easy debugging | No per-user tracking for "user" role |
| Works everywhere | Blueprint filtering is config-based |

---

## Approach 2: JWT Tokens (Balanced)

### Concept

JWT tokens with role claims. Admin creates tokens, clients use them for auth.

### Token Structure

```json
{
  "sub": "user-123",
  "role": "user",
  "allowed_blueprints": ["agent-1", "agent-2"],
  "exp": 1735689600,
  "iat": 1735603200
}
```

### Token Issuance

```
POST /auth/token  (Admin-only)
{
  "role": "user",
  "allowed_blueprints": ["agent-1"],
  "expires_in_days": 30
}
→ Returns: { "token": "eyJ..." }
```

### Client Configuration

Same as Approach 1, but tokens have expiration.

### Pros & Cons

| Pros | Cons |
|------|------|
| Built-in expiration | Slightly more complex |
| Self-contained claims | Token refresh needed |
| Auditable (sub field) | Need secure JWT secret |
| Per-user blueprint access | Can't revoke before expiration* |

*Can add token blacklist if needed, but adds state.

---

## Approach 3: OAuth2 with External IdP (Enterprise)

### Concept

Delegate authentication to external identity provider (Auth0, Keycloak, etc.). Agent Coordinator validates tokens.

### Flow

```
User/Dashboard → Login with IdP → Get OAuth2 token → Call Coordinator with token
Coordinator → Validate with IdP → Check role claims → Allow/Deny
```

### Role Mapping

Map IdP groups/claims to local roles:
```python
ROLE_MAPPING = {
    "orchestrator-admins": "admin",
    "orchestrator-runners": "runner",
    "orchestrator-users": "user"
}
```

### Pros & Cons

| Pros | Cons |
|------|------|
| Enterprise SSO | Most complex setup |
| Centralized user mgmt | External dependency |
| Token revocation | Overkill for small deployments |
| Audit trails | IdP cost/maintenance |

---

## Recommendation

**Start with Approach 1 (API Keys)** for initial deployment:
- Simplest to implement
- Sufficient for controlled access
- Easy to migrate to JWT later if needed

**Upgrade to Approach 2 (JWT)** when you need:
- Token expiration
- Per-user tracking
- Dynamic user provisioning

**Consider Approach 3** only for:
- Enterprise integration
- Existing IdP infrastructure
- Regulatory requirements

---

## Current Implementation

**Status**: Approach 1 (Static API Keys) implemented with Admin key only.

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AUTH_DISABLED` | No | `false` | Set to `true` to disable authentication (development only) |
| `ADMIN_API_KEY` | Yes* | - | API key for all endpoints (*required unless `AUTH_DISABLED=true`) |

### Startup Behavior

The Agent Coordinator validates authentication configuration on startup:

- If `AUTH_DISABLED=false` (default) and `ADMIN_API_KEY` is not set → **Server fails to start**
- If `AUTH_DISABLED=true` → Warning logged, all requests allowed without authentication
- If `ADMIN_API_KEY` is set → All requests require valid API key

### Client Authentication

Clients must include the API key in requests using one of two methods:

**1. Authorization Header (preferred)**
```
Authorization: Bearer <api_key>
```

**2. Query Parameter (for SSE/EventSource)**
```
?api_key=<api_key>
```

The query parameter method exists because the browser's `EventSource` API (used for SSE) doesn't support custom headers. Frontend applications use this method for SSE connections.

### HTTP Response Codes

| Code | Meaning |
|------|---------|
| 401 | Missing or malformed `Authorization` header |
| 403 | Invalid API key |

### Files

- `servers/agent-coordinator/auth.py` - Authentication module
- `servers/agent-coordinator/main.py` - Integration (startup validation, route protection)

### Client Implementation Status

All clients read from `AGENT_ORCHESTRATOR_API_KEY` environment variable.

| Client | Status | Files |
|--------|--------|-------|
| Agent Runner | Done | `lib/config.py`, `lib/api_client.py` |
| Claude Code Executor | Done | `lib/executor_config.py`, `lib/session_client.py`, `ao-claude-code-exec` |
| Test Executor | Done | `ao-test-exec` |
| Dashboard | Done | `src/utils/constants.ts`, `src/services/api.ts` |
| Chat UI | Done | `src/config/index.ts`, `src/services/api.ts` |
| Agent Orchestrator MCP | Pending | `mcps/agent-orchestrator/` |
| ao-* CLI commands | Pending | `plugins/orchestrator/` |

**Docker:** `docker-compose.yml` passes `AGENT_ORCHESTRATOR_API_KEY` to dashboard via `VITE_AGENT_ORCHESTRATOR_API_KEY`.

### Future Extensions

When role-based access (Runner, User) is needed:
1. Add `RUNNER_API_KEY` and/or user key configuration
2. Extend `verify_api_key()` to return role information
3. Add role-based route protection per the Permission Matrix above
