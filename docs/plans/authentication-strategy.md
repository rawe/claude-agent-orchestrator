# Authentication Strategy for Agent Orchestrator Framework

## Executive Summary

This document outlines the authentication strategy to secure the agent-orchestrator framework, protecting:
1. **Agent Runtime API** - The central hub for sessions, jobs, agents, and events
2. **Launcher-Runtime Communication** - Secure channel for distributed job execution
3. **Dashboard & Chat-UI** - Web client authentication flows

---

## Current State Analysis

### Security Gaps Identified

| Component | Current State | Risk Level |
|-----------|--------------|------------|
| Agent Runtime REST API | No authentication | **CRITICAL** |
| WebSocket Endpoint | No authentication | **CRITICAL** |
| Launcher Registration | Weak ID-only check | **HIGH** |
| Dashboard/Chat-UI | No auth headers | **HIGH** |
| Context Store API | No authentication | **MEDIUM** |

### Attack Surface

```
External Attacker
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  Port 8765 - Agent Runtime (FULLY EXPOSED)           │
│  ├── POST /jobs - Create arbitrary jobs              │
│  ├── POST /agents - Inject malicious agents          │
│  ├── GET /sessions - Access all session data         │
│  ├── WS /ws - Real-time event stream                 │
│  └── DELETE /sessions/* - Destroy sessions           │
└──────────────────────────────────────────────────────┘
```

---

## Authentication Architecture

### Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AUTHENTICATION LAYER                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐  │
│  │ Dashboard   │    │  Chat-UI    │    │    Agent Launcher       │  │
│  │             │    │             │    │                         │  │
│  │ Bearer JWT  │    │ Bearer JWT  │    │ Shared Secret + TLS     │  │
│  │ (User Auth) │    │ (User Auth) │    │ (Service-to-Service)    │  │
│  └──────┬──────┘    └──────┬──────┘    └───────────┬─────────────┘  │
│         │                  │                       │                 │
│         │   ┌──────────────┴──────────────┐       │                 │
│         │   │                             │       │                 │
│         ▼   ▼                             ▼       ▼                 │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                      Agent Runtime                              │ │
│  │  ┌────────────────────────────────────────────────────────┐    │ │
│  │  │              Authentication Middleware                  │    │ │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │    │ │
│  │  │  │ JWT Verifier │  │ API Key Auth │  │ Launcher Auth│  │    │ │
│  │  │  └──────────────┘  └──────────────┘  └──────────────┘  │    │ │
│  │  └────────────────────────────────────────────────────────┘    │ │
│  │                              │                                  │ │
│  │                              ▼                                  │ │
│  │  ┌────────────────────────────────────────────────────────┐    │ │
│  │  │                 Protected Endpoints                     │    │ │
│  │  │  /sessions  /jobs  /agents  /events  /launcher  /ws    │    │ │
│  │  └────────────────────────────────────────────────────────┘    │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Authentication Methods

### 1. API Key Authentication (Service-to-Service)

**Use Case**: Agent Launcher ↔ Agent Runtime communication

**Mechanism**:
- Pre-shared secret key configured via environment variables
- HMAC-based request signing for integrity
- Key rotation support via multiple active keys

**Implementation**:

```python
# Agent Runtime - Environment Configuration
LAUNCHER_API_KEYS = os.getenv("LAUNCHER_API_KEYS", "").split(",")
# Example: LAUNCHER_API_KEYS=key1:secret1,key2:secret2

# Request Header
Authorization: ApiKey <key_id>:<signature>
X-Timestamp: 1702745678
X-Nonce: <random-uuid>

# Signature = HMAC-SHA256(secret, f"{method}|{path}|{timestamp}|{nonce}|{body_hash}")
```

**Protected Endpoints**:
- `POST /launcher/register`
- `GET /launcher/jobs`
- `POST /launcher/jobs/{id}/started`
- `POST /launcher/jobs/{id}/completed`
- `POST /launcher/jobs/{id}/failed`
- `POST /launcher/heartbeat`

### 2. Bearer Token / JWT Authentication (User-facing)

**Use Case**: Dashboard & Chat-UI → Agent Runtime

**Mechanism**:
- JWT tokens with configurable expiration
- Supports multiple identity providers (future: OAuth2/OIDC)
- Initial implementation: Simple API key-based token generation

**Token Structure**:
```json
{
  "sub": "user_id_or_client_id",
  "iat": 1702745678,
  "exp": 1702832078,
  "scope": ["sessions:read", "sessions:write", "jobs:create"],
  "aud": "agent-runtime"
}
```

**Request Header**:
```
Authorization: Bearer <jwt_token>
```

**Protected Endpoints**:
- All `/sessions/*` endpoints
- All `/jobs/*` endpoints (except launcher-specific)
- All `/agents/*` endpoints
- All `/events/*` endpoints
- WebSocket `/ws` (token via query param or first message)

### 3. WebSocket Authentication

**Mechanism**:
- Token passed as query parameter during connection
- Validated on handshake before upgrade
- Connection closed with 4001 code if invalid

```typescript
// Client
const ws = new WebSocket(`${wsUrl}?token=${accessToken}`);

// Server
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    if not await verify_jwt(token):
        await websocket.close(code=4001, reason="Unauthorized")
        return
```

---

## Launcher-Runtime Secure Communication

### Registration Flow

```
┌─────────────────┐                         ┌─────────────────┐
│  Agent Launcher │                         │  Agent Runtime  │
└────────┬────────┘                         └────────┬────────┘
         │                                           │
         │  1. POST /launcher/register               │
         │  Headers:                                 │
         │    Authorization: ApiKey key1:sig        │
         │    X-Timestamp: 1702745678               │
         │    X-Nonce: uuid                         │
         │  Body: {hostname, project_dir, type}     │
         │─────────────────────────────────────────▶│
         │                                           │
         │  2. Verify signature                      │
         │  3. Generate launcher_id + session_token │
         │                                           │
         │  Response: {                              │
         │    launcher_id: "uuid",                   │
         │    session_token: "jwt-for-this-session", │
         │    poll_endpoint: "/launcher/jobs",       │
         │    ...                                    │
         │  }                                        │
         │◀─────────────────────────────────────────│
         │                                           │
         │  4. Use session_token for subsequent      │
         │     requests (polling, heartbeat, etc.)   │
         │                                           │
```

### Polling & Heartbeat

```python
# Agent Launcher - lib/api_client.py
class AuthenticatedApiClient:
    def __init__(self, base_url: str, api_key_id: str, api_key_secret: str):
        self.base_url = base_url
        self.api_key_id = api_key_id
        self.api_key_secret = api_key_secret
        self.session_token: Optional[str] = None  # Set after registration

    def _sign_request(self, method: str, path: str, body: bytes) -> dict:
        timestamp = str(int(time.time()))
        nonce = str(uuid.uuid4())
        body_hash = hashlib.sha256(body).hexdigest()

        message = f"{method}|{path}|{timestamp}|{nonce}|{body_hash}"
        signature = hmac.new(
            self.api_key_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        return {
            "Authorization": f"ApiKey {self.api_key_id}:{signature}",
            "X-Timestamp": timestamp,
            "X-Nonce": nonce
        }

    async def poll_for_jobs(self, launcher_id: str) -> Optional[dict]:
        # Use session_token after registration
        headers = {"Authorization": f"Bearer {self.session_token}"}
        response = await self.client.get(
            f"/launcher/jobs?launcher_id={launcher_id}",
            headers=headers,
            timeout=35.0
        )
        return response.json() if response.status_code == 200 else None
```

### Security Properties

| Property | Mechanism |
|----------|-----------|
| **Authentication** | API Key signature verification |
| **Integrity** | HMAC signature includes body hash |
| **Replay Protection** | Timestamp + Nonce checking (5-min window) |
| **Session Binding** | Session token ties launcher to registration |
| **Revocation** | Deregister endpoint invalidates session token |

---

## Dashboard & Chat-UI Authentication

### Initial Implementation (API Key Based)

For MVP, use a simple API key authentication that can be configured via environment:

```
# Dashboard/Chat-UI Environment
VITE_API_KEY=dashboard-api-key-uuid-here
```

```typescript
// services/api.ts
const api = axios.create({
  baseURL: config.apiUrl,
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${config.apiKey}`,
  },
});
```

### Future: OAuth2/OIDC Integration

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │────▶│  Auth0/     │────▶│   Agent     │
│ Dashboard   │     │  Keycloak   │     │   Runtime   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       │ 1. Login redirect │                   │
       │──────────────────▶│                   │
       │                   │                   │
       │ 2. Auth + Token   │                   │
       │◀──────────────────│                   │
       │                   │                   │
       │ 3. API Request with Bearer Token       │
       │───────────────────────────────────────▶│
       │                                        │
       │ 4. Verify JWT (using JWKS)             │
       │                                        │
       │ 5. Response                            │
       │◀───────────────────────────────────────│
```

---

## Agent Runtime Implementation

### Middleware Architecture

```python
# servers/agent-runtime/auth/middleware.py

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from enum import Enum
from typing import Optional
import jwt
import hmac
import hashlib

class AuthMethod(Enum):
    JWT_BEARER = "jwt"
    API_KEY = "api_key"
    LAUNCHER_SESSION = "launcher_session"

class AuthContext:
    """Carries authentication context through request lifecycle"""
    def __init__(
        self,
        method: AuthMethod,
        subject: str,
        scopes: list[str],
        metadata: dict = None
    ):
        self.method = method
        self.subject = subject
        self.scopes = scopes
        self.metadata = metadata or {}

# Dependency for protected routes
async def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
) -> AuthContext:

    # Try API Key auth first (for launcher)
    if auth_header := request.headers.get("Authorization", ""):
        if auth_header.startswith("ApiKey "):
            return await verify_api_key(request, auth_header)

    # Try Bearer token
    if credentials:
        return await verify_jwt(credentials.credentials)

    raise HTTPException(status_code=401, detail="Authentication required")

# Route protection example
@app.post("/jobs")
async def create_job(
    job_create: JobCreate,
    auth: AuthContext = Depends(require_auth)
):
    if "jobs:create" not in auth.scopes:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    # ... rest of handler
```

### Endpoint Protection Matrix

| Endpoint | Auth Method | Required Scopes |
|----------|-------------|-----------------|
| `GET /health` | None | - |
| `GET /sessions` | JWT | `sessions:read` |
| `POST /sessions` | JWT | `sessions:create` |
| `GET /sessions/{id}` | JWT | `sessions:read` |
| `DELETE /sessions/{id}` | JWT | `sessions:delete` |
| `POST /jobs` | JWT | `jobs:create` |
| `GET /jobs/{id}` | JWT | `jobs:read` |
| `POST /jobs/{id}/stop` | JWT | `jobs:write` |
| `GET /agents` | JWT | `agents:read` |
| `POST /agents` | JWT | `agents:create` |
| `PATCH /agents/{name}` | JWT | `agents:write` |
| `DELETE /agents/{name}` | JWT | `agents:delete` |
| `POST /launcher/register` | API Key | (launcher scope) |
| `GET /launcher/jobs` | Session Token | (launcher scope) |
| `POST /launcher/heartbeat` | Session Token | (launcher scope) |
| `WS /ws` | JWT (query) | `events:read` |

---

## Environment Configuration

### Agent Runtime

```bash
# .env for Agent Runtime

# JWT Configuration
JWT_SECRET_KEY=<32+ byte random secret>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# API Keys for Launchers (comma-separated key_id:secret pairs)
LAUNCHER_API_KEYS=launcher1:$(openssl rand -hex 32),launcher2:$(openssl rand -hex 32)

# API Keys for Dashboard/Chat-UI (simple bearer tokens)
CLIENT_API_KEYS=dashboard:$(openssl rand -hex 32),chatui:$(openssl rand -hex 32)

# Nonce/Replay protection
AUTH_NONCE_CACHE_TTL=300  # 5 minutes
AUTH_TIMESTAMP_TOLERANCE=300  # 5 minutes

# Optional: JWKS for external IdP
# JWKS_URL=https://your-idp.com/.well-known/jwks.json
```

### Agent Launcher

```bash
# .env for Agent Launcher

AGENT_RUNTIME_URL=http://localhost:8765
LAUNCHER_API_KEY_ID=launcher1
LAUNCHER_API_KEY_SECRET=<secret from runtime config>
```

### Dashboard / Chat-UI

```bash
# .env for Dashboard
VITE_API_URL=http://localhost:8765
VITE_WS_URL=ws://localhost:8765/ws
VITE_API_KEY=dashboard:<api-key-from-runtime>
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goal**: Protect Agent Runtime with basic API key authentication

1. **Create auth module** (`servers/agent-runtime/auth/`)
   - `middleware.py` - Authentication middleware
   - `jwt_handler.py` - JWT creation/verification
   - `api_key.py` - API key verification with HMAC
   - `config.py` - Auth configuration from environment

2. **Add authentication middleware to FastAPI app**
   - Implement `require_auth` dependency
   - Add to all protected routes
   - Keep `/health` endpoint public

3. **Update Agent Launcher**
   - Add signature generation to `api_client.py`
   - Handle session tokens from registration response
   - Update all API calls to include auth headers

4. **Basic testing**
   - Add integration tests for auth flows
   - Test with/without valid credentials

### Phase 2: Client Integration (Week 3)

**Goal**: Secure Dashboard and Chat-UI connections

1. **Update frontend API clients**
   - Add API key configuration
   - Include Bearer token in requests
   - Handle 401 responses gracefully

2. **WebSocket authentication**
   - Add token query parameter
   - Validate on connection handshake
   - Auto-reconnect with token refresh

3. **Error handling**
   - Display auth errors to users
   - Redirect to error page on persistent failures

### Phase 3: Enhanced Security (Week 4+)

**Goal**: Production-ready security features

1. **Rate limiting**
   - Add per-client rate limits
   - Protect against brute force

2. **Audit logging**
   - Log all authenticated requests
   - Track failed auth attempts

3. **Key rotation**
   - Support multiple active keys
   - Graceful key expiration

4. **TLS/HTTPS**
   - Configure TLS for production
   - Update all URLs to HTTPS

5. **Optional: OAuth2 integration**
   - Add OIDC provider support
   - User-based authentication

---

## Security Considerations

### Secrets Management

- **Never commit secrets** to version control
- Use environment variables or secret managers
- Rotate keys periodically
- Use different keys per environment

### Token Security

- **Short-lived tokens**: 24h max for JWTs
- **Secure transmission**: HTTPS in production
- **No sensitive data in tokens**: Only include necessary claims
- **Validate all claims**: exp, iat, aud, sub

### Replay Protection

- **Timestamp validation**: Reject requests >5 minutes old
- **Nonce caching**: Prevent replay within cache window
- **Rate limiting**: Prevent brute force attempts

### Error Handling

- **Generic error messages**: Don't leak auth details
- **Audit logging**: Log all auth failures
- **Alerting**: Monitor for suspicious patterns

---

## File Structure

```
servers/agent-runtime/
├── auth/
│   ├── __init__.py
│   ├── config.py           # Auth configuration
│   ├── middleware.py       # FastAPI auth middleware
│   ├── jwt_handler.py      # JWT operations
│   ├── api_key.py          # API key verification
│   ├── nonce_cache.py      # Replay protection
│   └── scopes.py           # Permission definitions
├── main.py                 # Updated with auth middleware
└── ...

servers/agent-launcher/
├── lib/
│   ├── api_client.py       # Updated with auth
│   ├── auth.py             # Signature generation
│   └── ...
└── ...

interfaces/chat-ui/
├── src/
│   ├── services/
│   │   ├── api.ts          # Updated with auth headers
│   │   └── auth.ts         # Auth token management
│   └── contexts/
│       └── WebSocketContext.tsx  # Updated with token
└── ...

dashboard/
├── src/
│   ├── services/
│   │   ├── api.ts          # Updated with auth headers
│   │   └── auth.ts         # Auth token management
│   └── ...
└── ...
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_auth.py

def test_jwt_creation():
    token = create_jwt(subject="user1", scopes=["sessions:read"])
    claims = decode_jwt(token)
    assert claims["sub"] == "user1"
    assert "sessions:read" in claims["scope"]

def test_api_key_signature():
    signature = sign_request("POST", "/jobs", b'{"type":"start"}', secret)
    assert verify_signature(signature, "POST", "/jobs", b'{"type":"start"}', secret)

def test_expired_token_rejected():
    token = create_jwt(subject="user1", expires_in=-1)  # Already expired
    with pytest.raises(AuthError):
        decode_jwt(token)
```

### Integration Tests

```python
# tests/integration/test_auth_flow.py

async def test_unauthenticated_request_rejected():
    response = await client.post("/jobs", json={"type": "start_session"})
    assert response.status_code == 401

async def test_valid_token_accepted():
    token = create_test_token(scopes=["jobs:create"])
    response = await client.post(
        "/jobs",
        json={"type": "start_session"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200

async def test_launcher_registration_with_api_key():
    headers = sign_launcher_request("POST", "/launcher/register", body)
    response = await client.post("/launcher/register", json=body, headers=headers)
    assert response.status_code == 200
    assert "session_token" in response.json()
```

---

## Migration Guide

### For Existing Deployments

1. **Generate secrets**:
   ```bash
   # Generate JWT secret
   openssl rand -hex 32 > jwt_secret.txt

   # Generate launcher API keys
   echo "launcher1:$(openssl rand -hex 32)" > launcher_keys.txt

   # Generate client API keys
   echo "dashboard:$(openssl rand -hex 32)" > client_keys.txt
   ```

2. **Update environment**:
   ```bash
   # Agent Runtime
   export JWT_SECRET_KEY=$(cat jwt_secret.txt)
   export LAUNCHER_API_KEYS=$(cat launcher_keys.txt)
   export CLIENT_API_KEYS=$(cat client_keys.txt)

   # Agent Launcher
   export LAUNCHER_API_KEY_ID=launcher1
   export LAUNCHER_API_KEY_SECRET=<secret from launcher_keys.txt>

   # Dashboard/Chat-UI
   export VITE_API_KEY=dashboard:<key from client_keys.txt>
   ```

3. **Restart services** in order:
   - Agent Runtime (must be up first to validate tokens)
   - Agent Launcher (will re-register with auth)
   - Dashboard/Chat-UI (will use new API key)

4. **Verify**:
   ```bash
   # Test health (should work without auth)
   curl http://localhost:8765/health

   # Test protected endpoint (should fail without auth)
   curl http://localhost:8765/sessions
   # Expected: 401 Unauthorized

   # Test with token
   curl -H "Authorization: Bearer <token>" http://localhost:8765/sessions
   # Expected: 200 OK
   ```

---

## Summary

This authentication strategy provides:

1. **Layered security** with multiple auth methods for different use cases
2. **Backward compatibility** through phased implementation
3. **Flexibility** to add OAuth2/OIDC in the future
4. **Defense in depth** with signature verification, replay protection, and rate limiting

The implementation protects all critical endpoints while maintaining the existing architecture and communication patterns.
