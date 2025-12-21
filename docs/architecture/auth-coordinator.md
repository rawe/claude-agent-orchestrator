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
| `WS /sessions/stream` | ✓ | ✗ | ✓ (own runs) |
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

### WebSocket Authentication

Pass key as query parameter during handshake:
```
ws://coordinator:8765/sessions/stream?token=ak_user_xxxx
```
Validate before upgrading connection. Reject invalid tokens with HTTP 401.

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

### WebSocket Authentication

Same as API Keys - pass in query param:
```
ws://coordinator:8765/sessions/stream?token=eyJhbG...
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

## WebSocket Authentication Methods

**Good news: WebSocket authentication is straightforward.** Multiple methods available with different trade-offs.

### Method 1: Query Parameter

```javascript
const ws = new WebSocket("ws://coordinator:8765/sessions/stream?token=xxx");
```

```python
@app.websocket("/sessions/stream")
async def ws_endpoint(websocket: WebSocket, token: str = Query(...)):
    if not validate_token(token):
        await websocket.close(code=4001)
        return
    await websocket.accept()
```

| Pros | Cons |
|------|------|
| Simple, works everywhere | Token appears in server logs |
| Pre-accept validation | Visible in browser history |
| Easy to implement | May leak via Referer header |

**Mitigation:** Use short-lived tokens (minutes, not days).

---

### Method 2: HTTP Header (Authorization)

```python
# Python/Node.js client - works
import websockets
async with websockets.connect(url, extra_headers={"Authorization": "Bearer xxx"}) as ws:
    ...
```

```javascript
// Browser - does NOT work!
const ws = new WebSocket(url, { headers: { "Authorization": "Bearer xxx" } });  // Ignored
```

| Pros | Cons |
|------|------|
| Token not in URL/logs | **Not supported in browsers** |
| Standard auth pattern | Only for server-to-server |
| Pre-accept validation | Native apps, Node.js clients |

**Verdict:** Good for Agent Runner, not viable for Dashboard.

---

### Method 3: Cookies (Session-Based)

```python
# Server sets cookie on login
response.set_cookie("session_token", token, httponly=True, secure=True, samesite="strict")

# WebSocket handler reads cookie automatically
@app.websocket("/sessions/stream")
async def ws_endpoint(websocket: WebSocket):
    token = websocket.cookies.get("session_token")
    if not validate_token(token):
        await websocket.close(code=4001)
        return
    await websocket.accept()
```

| Pros | Cons |
|------|------|
| No token in URL/logs | Requires session management |
| HttpOnly prevents XSS theft | Cross-origin complexity |
| Secure flag enforces HTTPS | Doesn't fit Agent Runner |
| SameSite prevents CSRF | Cookie-based state |

**Verdict:** Good for Dashboard if using cookie-based sessions.

---

### Method 4: First Message Authentication

Accept connection, require token as first message:

```python
@app.websocket("/sessions/stream")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()

    # First message must be auth token
    try:
        auth_msg = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
        if not validate_token(auth_msg.get("token")):
            await websocket.close(code=4001)
            return
    except asyncio.TimeoutError:
        await websocket.close(code=4001)
        return

    # Authenticated - proceed with normal messages
    await stream_events(websocket)
```

```javascript
// Client
const ws = new WebSocket("ws://coordinator:8765/sessions/stream");
ws.onopen = () => ws.send(JSON.stringify({ token: "xxx" }));
```

| Pros | Cons |
|------|------|
| No token in URL/logs | Connection briefly open before auth |
| Works with all clients | Resource exhaustion risk |
| Browser + native support | Slightly more complex protocol |

**Mitigation:** Short timeout (5s), connection rate limiting.

---

### Method 5: Sec-WebSocket-Protocol Header

Browsers allow setting the `Sec-WebSocket-Protocol` header:

```javascript
// Browser - token encoded in subprotocol
const ws = new WebSocket(url, ["bearer.eyJhbGciOiJIUzI1NiIs..."]);
```

```python
@app.websocket("/sessions/stream")
async def ws_endpoint(websocket: WebSocket):
    protocols = websocket.headers.get("sec-websocket-protocol", "").split(",")
    token = None
    for p in protocols:
        p = p.strip()
        if p.startswith("bearer."):
            token = p[7:]  # Remove "bearer." prefix
            break

    if not validate_token(token):
        await websocket.close(code=4001)
        return

    await websocket.accept(subprotocol=f"bearer.{token}")
```

| Pros | Cons |
|------|------|
| Works in browsers | Misuse of protocol header (hacky) |
| Token not in URL/logs | Some proxies may log this header |
| Pre-accept validation | Visible in browser dev tools |

---

### Security Comparison

| Method | Token in Logs | Browser Support | Pre-Accept Validation | Complexity |
|--------|---------------|-----------------|----------------------|------------|
| Query Param | Yes | ✓ | ✓ | Low |
| HTTP Header | No | ✗ | ✓ | Low |
| Cookies | No | ✓ | ✓ | Medium |
| First Message | No | ✓ | ✗ | Medium |
| Subprotocol | No* | ✓ | ✓ | Medium |

### Recommended: Multi-Method Support

Support multiple methods on the server to accommodate different clients:

```python
@app.websocket("/sessions/stream")
async def ws_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    validated_token = None

    # Method 1: Authorization header (Agent Runner, CLI tools)
    auth_header = websocket.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        validated_token = auth_header[7:]

    # Method 2: Cookie (Dashboard with session management)
    if not validated_token:
        validated_token = websocket.cookies.get("session_token")

    # Method 3: Query param fallback (simple clients, development)
    if not validated_token:
        validated_token = token

    # Validate
    if not validated_token or not validate_token(validated_token):
        await websocket.close(code=4001)
        return

    await websocket.accept()
    await stream_events(websocket, validated_token)
```

| Client | Recommended Method |
|--------|-------------------|
| Agent Runner (Python) | HTTP Header |
| Dashboard (Browser) | Cookie or First Message |
| CLI tools | HTTP Header or Query Param |
| Development/Testing | Query Param |

**Verdict: No architecture change needed.** WebSocket protection is not significantly harder than REST protection. The multi-method approach provides flexibility for all client types.

---

## Next Steps

1. Choose approach (recommend starting with #1)
2. Detail the implementation for chosen approach
3. Define migration path for local → public deployment
