# Context Store Token-Based Scoping

**Status:** Draft
**Date:** 2026-01-11

## Overview

An alternative approach to Context Store scoping using signed JWT tokens. The Agent Coordinator issues tokens that encode namespace and scope_filters. The Context Store Server validates tokens and extracts scope, eliminating the need for explicit scope parameters in the API.

This approach also implicitly secures the Context Store - access is only possible with a valid token signed by a trusted Coordinator.

**Key Principles:**
1. Coordinator signs tokens with private key, Context Store validates with public key
2. Token encodes namespace + scope_filters - no explicit scope params needed in API
3. Server-to-server trust independent of user authentication (Auth0)
4. Generic pattern applicable to other services (knowledge graph, etc.)
5. Deactivatable - falls back to unauthenticated mode for development

## Motivation

### Problems Solved

| Problem | How Tokens Solve It |
|---------|---------------------|
| Context Store security | Access requires valid token from trusted Coordinator |
| Scope parameter complexity | Namespace/filters encoded in token, not in every API call |
| CLI parameter burden | CLI just passes token, no `--namespace` or `--scope-filter` flags needed |
| Server-to-server trust | Cryptographic verification without shared secrets per request |

### Relationship to Approach 1 (Explicit API)

| Aspect | Approach 1 (Explicit API) | Token-Based |
|--------|---------------------------|-------------|
| Namespace in URL | Yes (`/namespaces/{ns}/...`) | No (extracted from token) |
| Scope in params | Yes (`?scope_filters={...}`) | No (extracted from token) |
| Security | None (trusts caller) | Cryptographic (JWT signature) |
| Standalone operation | Yes | Requires Coordinator (or auth disabled) |
| CLI complexity | Flags for namespace/scope | Just token env var |

## Architecture

### Token Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Token Flow                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Run Created                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  POST /runs                                                         │    │
│  │  {                                                                  │    │
│  │    "agent_name": "implementer",                                     │    │
│  │    "context": {                                                     │    │
│  │      "namespace": "project-alpha",                                  │    │
│  │      "scope_filters": {"root_session_id": "ses_001"}               │    │
│  │    }                                                                │    │
│  │  }                                                                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  2. Coordinator Issues Token                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Agent Coordinator                                                  │    │
│  │  ┌───────────────────────────────────────────────────────────────┐ │    │
│  │  │  Signs JWT with private key:                                  │ │    │
│  │  │  {                                                            │ │    │
│  │  │    "namespace": "project-alpha",                              │ │    │
│  │  │    "scope_filters": {"root_session_id": "ses_001"},          │ │    │
│  │  │    "run_id": "run_abc123",                                    │ │    │
│  │  │    "iat": 1736600000,                                         │ │    │
│  │  │    "exp": 1736603600  // +1 hour                              │ │    │
│  │  │  }                                                            │ │    │
│  │  └───────────────────────────────────────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  3. Token in Run Assignment                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Run assigned to Runner includes:                                   │    │
│  │  {                                                                  │    │
│  │    "run_id": "run_abc123",                                         │    │
│  │    "context_store_token": "eyJhbGciOiJSUzI1NiIs..."               │    │
│  │  }                                                                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  4. Executor Sends Requests to MCP Server with Token                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Executor → MCP Server (HTTP/MCP protocol):                         │    │
│  │    X-Service-Token: eyJhbGciOiJSUzI1NiIs...                        │    │
│  │                                                                     │    │
│  │  MCP Server is a separate service, receives token per-request       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  5. MCP Server Uses Token                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  MCP Server                                                         │    │
│  │  ┌───────────────────────────────────────────────────────────────┐ │    │
│  │  │  1. Receives token from Executor request header               │ │    │
│  │  │  2. LLM calls: doc_query(tags="architecture")                 │ │    │
│  │  │  3. MCP Server spawns CLI with token in env var:              │ │    │
│  │  │       CONTEXT_STORE_TOKEN=eyJ... doc-query --tags arch        │ │    │
│  │  │  4. CLI calls Context Store Server:                           │ │    │
│  │  │       GET /documents?tags=architecture                        │ │    │
│  │  │       Authorization: Bearer eyJhbGciOiJSUzI1NiIs...           │ │    │
│  │  └───────────────────────────────────────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  6. Context Store Validates & Extracts Scope                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Context Store Server                                               │    │
│  │  ┌───────────────────────────────────────────────────────────────┐ │    │
│  │  │  1. Verify JWT signature (Coordinator's public key)           │ │    │
│  │  │  2. Check expiration                                          │ │    │
│  │  │  3. Extract: namespace="project-alpha"                        │ │    │
│  │  │             scope_filters={"root_session_id":"ses_001"}       │ │    │
│  │  │  4. Apply to query                                            │ │    │
│  │  └───────────────────────────────────────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Trust Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Public/Private Key Trust                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Agent Coordinator                         Context Store Server             │
│   ┌─────────────────────┐                  ┌─────────────────────┐          │
│   │                     │                  │                     │          │
│   │  Private Key        │                  │  Public Key         │          │
│   │  (signs tokens)     │                  │  (verifies tokens)  │          │
│   │                     │                  │                     │          │
│   │  Configured via:    │                  │  Configured via:    │          │
│   │  COORDINATOR_       │                  │  TRUSTED_ISSUER_    │          │
│   │  PRIVATE_KEY        │                  │  PUBLIC_KEY         │          │
│   │                     │                  │                     │          │
│   └─────────────────────┘                  └─────────────────────┘          │
│                                                                              │
│   Independent of Auth0 - this is server-to-server trust only                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Token Structure

### JWT Payload

```json
{
  "iss": "agent-coordinator",
  "sub": "run_abc123",
  "iat": 1736600000,
  "exp": 1736603600,
  "namespace": "project-alpha",
  "scope_filters": {
    "root_session_id": "ses_001"
  }
}
```

| Field | Purpose |
|-------|---------|
| `iss` | Issuer identifier (for multi-coordinator setups) |
| `sub` | Run ID (for audit/logging) |
| `iat` | Issued at timestamp |
| `exp` | Expiration timestamp (run duration, e.g., +1 hour) |
| `namespace` | Document namespace (required) |
| `scope_filters` | Optional filters for finer-grained scoping |

### JWT Header

```json
{
  "alg": "RS256",
  "typ": "JWT"
}
```

Using RS256 (RSA + SHA-256) for asymmetric signing - Coordinator has private key, Context Store only needs public key.

## API Design

### With Token Auth Enabled

No namespace in URL - extracted from token:

```
GET /documents
GET /documents?tags=architecture
GET /documents/{id}
POST /documents
PUT /documents/{id}/content
DELETE /documents/{id}

All requests require:
  Authorization: Bearer <token>

Server extracts namespace and scope_filters from token.
```

### With Token Auth Disabled (Development Mode)

Falls back to explicit API (no filtering applied):

```
GET /documents
POST /documents

No Authorization header required.
No namespace filtering - all documents visible.
```

**Note:** When auth is disabled, the Context Store operates without scoping. This is intended for local development only.

## Subcomponent Changes

### Agent Coordinator

| Area | Change |
|------|--------|
| **Key management** | Store private key for signing (env var or secrets manager) |
| **Token generation** | Generate JWT when run is created, include in run assignment |
| **Run context** | Add `context_store_token` field to run assignment payload |
| **Token library** | Use standard JWT library (e.g., PyJWT, python-jose) |

**Token generation (simplified):**

```python
import jwt
from datetime import datetime, timedelta

def generate_context_store_token(run_id: str, context: dict) -> str:
    payload = {
        "iss": "agent-coordinator",
        "sub": run_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1),
        "namespace": context["namespace"],
        "scope_filters": context.get("scope_filters", {})
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")
```

### Context Store Server

| Area | Change |
|------|--------|
| **Configuration** | `CONTEXT_STORE_AUTH_ENABLED` (bool), `TRUSTED_ISSUER_PUBLIC_KEY` (PEM) |
| **Middleware** | JWT validation middleware - extract and verify token |
| **Request context** | Store extracted namespace/scope_filters in request state |
| **Query filtering** | Apply namespace/scope_filters from request state (not URL/params) |
| **Error responses** | 401 Unauthorized for missing/invalid token |

**Middleware (simplified):**

```python
from fastapi import Request, HTTPException
import jwt

async def validate_token(request: Request):
    if not AUTH_ENABLED:
        return  # Skip validation in dev mode

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
        request.state.namespace = payload["namespace"]
        request.state.scope_filters = payload.get("scope_filters", {})
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
```

### MCP Server

| Area | Change |
|------|--------|
| **Token reception** | Extract token from Executor's request header (`X-Service-Token`) |
| **CLI invocation** | Set `CONTEXT_STORE_TOKEN` env var when spawning CLI subprocesses |
| **Tool definitions** | No changes - namespace/scope not exposed to LLM |

**MCP Server handling (simplified):**

```python
# MCP Server receives token from Executor's request header
# and passes it to CLI subprocess via environment variable

async def handle_tool_call(request: Request, tool_name: str, params: dict):
    # Extract token from incoming request header
    token = request.headers.get("X-Service-Token")

    if tool_name == "doc_query":
        # Spawn CLI with token in environment
        env = os.environ.copy()
        env["CONTEXT_STORE_TOKEN"] = token

        result = subprocess.run(
            ["doc-query", "--tags", params.get("tags", "")],
            env=env,
            capture_output=True
        )
        return result.stdout
```

### CLI Commands

| Area | Change |
|------|--------|
| **Token source** | Read `CONTEXT_STORE_TOKEN` from environment |
| **HTTP requests** | Attach `Authorization: Bearer <token>` header if token present |
| **No new flags** | Remove need for `--namespace` and `--scope-filter` when token provided |
| **Fallback** | If no token, operate without auth (dev mode only) |

**CLI behavior:**

```bash
# With token (normal operation via MCP Server)
CONTEXT_STORE_TOKEN=eyJ... doc-query --tags architecture
# → Token attached, namespace/scope from token

# Without token (standalone dev mode, auth disabled on server)
doc-query --tags architecture
# → No auth, no filtering, sees all documents
```

### Agent Runner / Executor

| Area | Change |
|------|--------|
| **Run assignment** | Receive `context_store_token` from Coordinator in run payload |
| **MCP requests** | Include token in HTTP header (`X-Service-Token`) when calling MCP Server |

## Configuration

### Agent Coordinator

| Variable | Description |
|----------|-------------|
| `CONTEXT_STORE_SIGNING_KEY` | Private key (PEM) for signing tokens |
| `CONTEXT_STORE_TOKEN_EXPIRY` | Token lifetime (default: `3600` seconds / 1 hour) |

### Context Store Server

| Variable | Description |
|----------|-------------|
| `CONTEXT_STORE_AUTH_ENABLED` | Enable token auth (default: `false`) |
| `CONTEXT_STORE_TRUSTED_PUBLIC_KEY` | Public key (PEM) for verifying tokens |
| `CONTEXT_STORE_ISSUER` | Expected `iss` claim (default: `agent-coordinator`) |

### CLI

| Variable | Description |
|----------|-------------|
| `CONTEXT_STORE_TOKEN` | JWT token (set by MCP Server when spawning CLI subprocess) |

### Token Flow

| Phase | Mechanism |
|-------|-----------|
| Coordinator → Executor | Token in run assignment payload |
| Executor → MCP Server | HTTP header (`X-Service-Token`) per-request |
| MCP Server → CLI | Environment variable when spawning subprocess |
| CLI → Context Store | HTTP header (`Authorization: Bearer`) |

## Operation Modes

### Mode 1: Auth Enabled (Production)

```
CONTEXT_STORE_AUTH_ENABLED=true
CONTEXT_STORE_TRUSTED_PUBLIC_KEY=<public-key-pem>
```

- All requests require valid token
- Namespace/scope extracted from token
- Invalid/expired token → 401 Unauthorized
- Context Store is secured

### Mode 2: Auth Disabled (Development)

```
CONTEXT_STORE_AUTH_ENABLED=false
```

- No token required
- No namespace filtering applied
- All documents visible to all requests
- CLI works standalone without token
- **Not for production use**

## Security Considerations

### What This Secures

| Threat | Mitigation |
|--------|------------|
| Unauthorized access to Context Store | Requires valid token from Coordinator |
| Token forgery | RS256 signature verification |
| Token replay after expiration | Expiration claim (`exp`) checked |
| LLM manipulating scope | Scope in token, not in tool parameters |

### What This Does NOT Secure

| Aspect | Notes |
|--------|-------|
| User authentication | Handled separately by Auth0 on Coordinator |
| Transport security | Requires HTTPS in production |
| Key compromise | Standard key rotation practices apply |

### Key Management

- Private key should be stored securely (env var, secrets manager)
- Public key can be distributed freely
- Consider key rotation strategy for production

## Libraries and Standards

Use established libraries - no custom cryptography:

| Language | Library | Notes |
|----------|---------|-------|
| Python | `PyJWT` or `python-jose` | Well-maintained, supports RS256 |
| Node.js | `jsonwebtoken` | Standard JWT library |

JWT is RFC 7519 - widely supported, well-understood security properties.

## Applicability to Other Services

This pattern is generic and can secure other namespace-scoped services:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Generic Server-to-Server Token Auth                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Agent Coordinator (Token Issuer)                                           │
│           │                                                                  │
│           ├──── Token ────►  Context Store Server                           │
│           │                                                                  │
│           ├──── Token ────►  Knowledge Graph Server (future)                │
│           │                                                                  │
│           └──── Token ────►  Other Namespace-Scoped Service                 │
│                                                                              │
│   All services trust Coordinator's public key                                │
│   All tokens contain namespace + service-specific claims                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Migration Strategy

### Phase 1: Add Token Support (Backward Compatible)

1. Implement token generation in Coordinator
2. Add token validation middleware to Context Store (disabled by default)
3. Update Executor to include token in MCP Server request headers
4. Update MCP Server to extract token from request header and pass to CLI via env var
5. Update CLI to read token from env var and attach to Context Store requests

### Phase 2: Enable in Staging

1. Enable `CONTEXT_STORE_AUTH_ENABLED=true` in staging
2. Verify token flow works end-to-end
3. Test expiration handling

### Phase 3: Production Rollout

1. Generate production key pair
2. Configure Coordinator with private key
3. Configure Context Store with public key
4. Enable auth, monitor for 401 errors

## Future Considerations

### Permissions (Not in Scope)

Token could include permissions for fine-grained access control:

```json
{
  "namespace": "project-alpha",
  "permissions": ["read", "write"]  // or ["read"] for read-only
}
```

### Token Refresh

For very long runs, could implement token refresh:

```
1. Token nearing expiration
2. MCP Server requests refresh from Coordinator
3. Coordinator issues new token (if run still active)
```

### Multi-Coordinator Trust

Support multiple trusted issuers:

```
CONTEXT_STORE_TRUSTED_PUBLIC_KEYS={"coord-1": "<key1>", "coord-2": "<key2>"}
```

## References

### Related Design Documents

- [External Service Token Architecture](./external-service-token-architecture-with-scoping.md) - Foundational pattern for external service integration
- [Context Store Scoping](../context-store-scoping/context-store-scoping.md) - Approach 1 (Explicit API)

### Component Documentation

- [Context Store Architecture](../../components/context-store/README.md) - Component overview
- [Context Store Server](../../components/context-store/SERVER.md) - Server architecture
- [MCP Server Architecture](../../components/context-store/MCP.md) - MCP integration

### Implementation Documentation

- [Context Store Server README](../../../servers/context-store/README.md) - Server implementation, API endpoints, environment variables
- [Semantic Search Architecture](../../../servers/context-store/docs/architecture-semantic-search.md) - Vector search implementation
- [Document Relations](../../../servers/context-store/docs/architecture-context-store-relations.md) - Parent-child and peer relations

### External References

- [JWT RFC 7519](https://tools.ietf.org/html/rfc7519) - JSON Web Token standard
- [PyJWT Documentation](https://pyjwt.readthedocs.io/) - Python JWT library
