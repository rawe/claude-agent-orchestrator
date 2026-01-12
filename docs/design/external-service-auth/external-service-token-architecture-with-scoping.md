# External Service Token Architecture with Scoping

**Status:** Draft
**Date:** 2026-01-11

## Overview

This document describes the architectural pattern for integrating external services with the Agent Orchestrator framework using signed tokens for access control and data scoping. External services are standalone servers (not hosted on the Coordinator) that agents interact with via MCP.

The Coordinator acts as the trust anchor, issuing signed tokens that encode:
1. **Access authorization** - Proof that the request originates from a valid run
2. **Data scope** - Namespace and filters that control what data the agent can access

**First implementation:** Context Store Server

**Future candidates:** Knowledge graph (Neo4J), vector databases, specialized domain services

## Problem Statement

When agents interact with external services, we need to solve:

| Problem | Without This Pattern |
|---------|---------------------|
| **Access control** | Any client can access the service |
| **Data isolation** | Agents see all data, no project/tenant boundaries |
| **Scope enforcement** | Agents could access data outside their intended scope |
| **Trust establishment** | No way for services to verify requests are legitimate |

## Architecture

### Component Roles

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Component Responsibilities                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Agent Coordinator (Trust Anchor)                                           │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  - Holds private key for signing tokens                             │   │
│   │  - Issues tokens when runs are created                              │   │
│   │  - Embeds scope (namespace, filters) in token payload               │   │
│   │  - Determines scope based on run context                            │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   MCP Server (Token Carrier / Service Adapter)                               │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  - Receives token from Executor in HTTP header (per-request)        │   │
│   │  - Acts as adapter between LLM tool calls and external service API  │   │
│   │  - Attaches token to all outbound requests to external services     │   │
│   │  - Does NOT expose scope parameters to LLM (hides in tool defs)     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   External Service (Token Consumer)                                          │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  - Holds Coordinator's public key for verification                  │   │
│   │  - Validates token signature on every request                       │   │
│   │  - Extracts scope from token payload                                │   │
│   │  - Applies scope to all data operations                             │   │
│   │  - Rejects requests with invalid/expired tokens                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Token Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Token Flow                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Run Creation                                                             │
│     ┌───────────────────────────────────────────────────────────────────┐   │
│     │  POST /runs                                                       │   │
│     │  {                                                                │   │
│     │    "agent_name": "implementer",                                   │   │
│     │    "context": {                                                   │   │
│     │      "namespace": "project-alpha",                                │   │
│     │      "scope_filters": {"root_session_id": "ses_001"}             │   │
│     │    }                                                              │   │
│     │  }                                                                │   │
│     └───────────────────────────────────────────────────────────────────┘   │
│                              │                                               │
│                              ▼                                               │
│  2. Coordinator Signs Token                                                  │
│     ┌───────────────────────────────────────────────────────────────────┐   │
│     │  Token Payload:                                                   │   │
│     │  {                                                                │   │
│     │    "iss": "agent-coordinator",                                    │   │
│     │    "sub": "run_abc123",                                           │   │
│     │    "exp": 1736603600,                                             │   │
│     │    "services": {                                                  │   │
│     │      "context-store": {                                           │   │
│     │        "namespace": "project-alpha",                              │   │
│     │        "scope_filters": {"root_session_id": "ses_001"}           │   │
│     │      },                                                           │   │
│     │      "knowledge-graph": {                                         │   │
│     │        "namespace": "project-alpha",                              │   │
│     │        "graph_id": "kg_001"                                       │   │
│     │      }                                                            │   │
│     │    }                                                              │   │
│     │  }                                                                │   │
│     └───────────────────────────────────────────────────────────────────┘   │
│                              │                                               │
│                              ▼                                               │
│  3. Token Delivered to Executor                                              │
│     ┌───────────────────────────────────────────────────────────────────┐   │
│     │  Run assignment includes:                                         │   │
│     │  {                                                                │   │
│     │    "run_id": "run_abc123",                                        │   │
│     │    "service_token": "eyJhbGciOiJSUzI1NiIs..."                    │   │
│     │  }                                                                │   │
│     └───────────────────────────────────────────────────────────────────┘   │
│                              │                                               │
│                              ▼                                               │
│  4. Executor Sends Requests to MCP Server with Token                         │
│     ┌───────────────────────────────────────────────────────────────────┐   │
│     │  Executor → MCP Server (HTTP/MCP protocol):                       │   │
│     │    X-Service-Token: eyJhbGciOiJSUzI1NiIs...                      │   │
│     │                                                                   │   │
│     │  MCP Server is a separate service (not spawned by Executor)       │   │
│     │  Token passed in header with each request                         │   │
│     └───────────────────────────────────────────────────────────────────┘   │
│                              │                                               │
│                              ▼                                               │
│  5. MCP Server Forwards Token to External Services                           │
│     ┌───────────────────────────────────────────────────────────────────┐   │
│     │  LLM: doc_query(tags="architecture")                              │   │
│     │                                                                   │   │
│     │  MCP Server:                                                      │   │
│     │    1. Extracts token from incoming request header                 │   │
│     │    2. Builds request to external service:                         │   │
│     │       GET /documents?tags=architecture                            │   │
│     │       Authorization: Bearer eyJhbGciOiJSUzI1NiIs...              │   │
│     │                                                                   │   │
│     │  (Token passed through, external service extracts its scope)      │   │
│     └───────────────────────────────────────────────────────────────────┘   │
│                              │                                               │
│                              ▼                                               │
│  6. External Service Validates and Applies Scope                             │
│     ┌───────────────────────────────────────────────────────────────────┐   │
│     │  Context Store Server:                                            │   │
│     │    1. Verify JWT signature (Coordinator's public key)             │   │
│     │    2. Check expiration                                            │   │
│     │    3. Extract: services["context-store"]                          │   │
│     │       → namespace = "project-alpha"                               │   │
│     │       → scope_filters = {"root_session_id": "ses_001"}           │   │
│     │    4. Apply to query                                              │   │
│     └───────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Trust Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Trust Relationships                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                      Agent Coordinator                                       │
│                      ┌──────────────┐                                       │
│                      │ Private Key  │                                       │
│                      │ (signs)      │                                       │
│                      └──────┬───────┘                                       │
│                             │                                                │
│              ┌──────────────┼──────────────┐                                │
│              │              │              │                                │
│              ▼              ▼              ▼                                │
│     ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                     │
│     │Context Store │ │Knowledge     │ │Future        │                     │
│     │Server        │ │Graph Server  │ │Service       │                     │
│     │              │ │              │ │              │                     │
│     │ Public Key   │ │ Public Key   │ │ Public Key   │                     │
│     │ (verifies)   │ │ (verifies)   │ │ (verifies)   │                     │
│     └──────────────┘ └──────────────┘ └──────────────┘                     │
│                                                                              │
│   All external services trust the same Coordinator public key               │
│   This is independent of user authentication (Auth0)                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Token Structure

### Multi-Service Payload

The token contains scope information for all services the run may access:

```json
{
  "iss": "agent-coordinator",
  "sub": "run_abc123",
  "iat": 1736600000,
  "exp": 1736603600,
  "services": {
    "context-store": {
      "namespace": "project-alpha",
      "scope_filters": {
        "root_session_id": "ses_001"
      }
    },
    "knowledge-graph": {
      "namespace": "project-alpha",
      "graph_id": "kg_001"
    }
  }
}
```

| Field | Purpose |
|-------|---------|
| `iss` | Issuer (for multi-coordinator setups) |
| `sub` | Run ID (audit trail) |
| `iat` | Issued at timestamp |
| `exp` | Expiration (run lifetime, e.g., 1 hour) |
| `services` | Per-service scope configuration |

### Service Scope Extraction

Each service extracts only its relevant section:

```python
# Context Store extracts:
scope = payload["services"].get("context-store", {})
namespace = scope.get("namespace")
scope_filters = scope.get("scope_filters", {})

# Knowledge Graph extracts:
scope = payload["services"].get("knowledge-graph", {})
namespace = scope.get("namespace")
graph_id = scope.get("graph_id")
```

### Security Note

> **Known concern:** With a single token for multiple services, each service can read the scope configuration of other services in the payload. For the current use case (internal services within the same deployment), this is acceptable. For future multi-tenant or security-sensitive deployments, consider service-specific tokens or encrypted payload sections.

## Scoping Pattern

All services implementing this pattern follow the same scoping model:

### Namespace

- **Required** - Primary isolation boundary
- **Semantics** - Project, tenant, or workflow identifier
- **Behavior** - Complete isolation between namespaces

### Scope Filters

- **Optional** - Finer-grained scoping within namespace
- **Semantics** - Service-specific (e.g., `root_session_id`, `graph_id`)
- **Behavior** - Filters data within namespace

### Visibility Rules

| Document/Entity | Visible When |
|-----------------|--------------|
| Namespace-scoped (no filters) | Always visible within namespace |
| Filter-scoped | Visible when filters match OR no filters in request |

```
Namespace: project-alpha
├── Scoped data (e.g., root_session_id: ses_001)
│   └── Visible only to matching requests
├── Scoped data (e.g., root_session_id: ses_002)
│   └── Visible only to matching requests
└── Namespace-wide data (no filters)
    └── Visible to ALL requests in namespace
```

## Concrete Example: Context Store

### Service Configuration

```bash
# Context Store Server
CONTEXT_STORE_AUTH_ENABLED=true
CONTEXT_STORE_TRUSTED_PUBLIC_KEY=<coordinator-public-key-pem>
CONTEXT_STORE_SERVICE_NAME=context-store  # Key in token payload
```

### Token Extraction

```python
def extract_scope(token_payload: dict) -> Scope:
    service_scope = token_payload.get("services", {}).get("context-store", {})
    return Scope(
        namespace=service_scope.get("namespace"),
        scope_filters=service_scope.get("scope_filters", {})
    )
```

### API Behavior

With auth enabled, all endpoints:
1. Require `Authorization: Bearer <token>` header
2. Extract namespace and scope_filters from token
3. Apply to query/create operations

```
# Request
GET /documents?tags=architecture
Authorization: Bearer eyJ...

# Server extracts from token:
#   namespace = "project-alpha"
#   scope_filters = {"root_session_id": "ses_001"}

# Query becomes:
#   WHERE namespace = "project-alpha"
#   AND (scope_filters = {} OR scope_filters @> {"root_session_id": "ses_001"})
```

### Document Creation

Documents inherit scope from token:

```
POST /documents
Authorization: Bearer eyJ...
Body: {"filename": "notes.md", "tags": ["notes"]}

# Server extracts from token and stores:
#   namespace = "project-alpha"
#   scope_filters = {"root_session_id": "ses_001"}
```

## Adding New External Services

To integrate a new service with this pattern:

### 1. Define Service Scope Schema

Determine what scope fields the service needs:

```python
# Example: Knowledge Graph Service
{
  "namespace": "project-alpha",  # Standard
  "graph_id": "kg_001",          # Service-specific
  "read_only": false             # Service-specific
}
```

### 2. Configure Trust

Service trusts Coordinator's public key:

```bash
SERVICE_AUTH_ENABLED=true
SERVICE_TRUSTED_PUBLIC_KEY=<coordinator-public-key-pem>
SERVICE_NAME=knowledge-graph  # Key in token payload
```

### 3. Implement Token Middleware

```python
async def validate_and_extract_scope(request: Request):
    token = extract_bearer_token(request)
    payload = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])

    service_scope = payload["services"].get(SERVICE_NAME, {})
    if not service_scope.get("namespace"):
        raise HTTPException(403, "No access to this service")

    request.state.namespace = service_scope["namespace"]
    request.state.scope = service_scope
```

### 4. Update Coordinator

Add service scope to token generation:

```python
def generate_service_token(run_id: str, context: dict) -> str:
    payload = {
        "iss": "agent-coordinator",
        "sub": run_id,
        "exp": datetime.utcnow() + timedelta(hours=1),
        "services": {
            "context-store": {
                "namespace": context["namespace"],
                "scope_filters": context.get("scope_filters", {})
            },
            "knowledge-graph": {  # New service
                "namespace": context["namespace"],
                "graph_id": context.get("graph_id")
            }
        }
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")
```

### 5. Update MCP Server

Pass token to new service:

```python
class KnowledgeGraphClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token

    def query(self, cypher: str):
        return httpx.post(
            f"{self.base_url}/query",
            json={"cypher": cypher},
            headers={"Authorization": f"Bearer {self.token}"}
        )
```

## Operation Modes

### Mode 1: Auth Enabled (Production)

- Token required on all requests
- Scope extracted from token
- Invalid token → 401 Unauthorized
- Missing service scope → 403 Forbidden

### Mode 2: Auth Disabled (Development)

- No token required
- No scoping applied
- All data visible
- **Not for production**

## Configuration Summary

### Agent Coordinator

| Variable | Description |
|----------|-------------|
| `SERVICE_TOKEN_PRIVATE_KEY` | Private key (PEM) for signing |
| `SERVICE_TOKEN_EXPIRY` | Token lifetime (default: 3600s) |

### External Services (each)

| Variable | Description |
|----------|-------------|
| `<SERVICE>_AUTH_ENABLED` | Enable token auth |
| `<SERVICE>_TRUSTED_PUBLIC_KEY` | Coordinator's public key |
| `<SERVICE>_SERVICE_NAME` | Key in token `services` object |

## Token Passing by Phase

| Phase | From | To | Mechanism |
|-------|------|-----|-----------|
| Run creation | Coordinator | Runner/Executor | Token in run assignment payload |
| Tool execution | Executor | MCP Server | HTTP header (`X-Service-Token`) |
| Service call | MCP Server | External Service | HTTP header (`Authorization: Bearer`) |

> **Implementation note:** Specific MCP Server implementations may have additional internal layers (e.g., CLI tools). Token passing within those layers is implementation-specific. For example, the Context Store MCP Server spawns CLI subprocesses and passes the token via environment variable.

## Future Considerations

### Namespace Alignment Across Services

Option to interpret namespace globally so the same namespace applies to all services:

```json
{
  "global_namespace": "project-alpha",
  "services": {
    "context-store": { "scope_filters": {...} },
    "knowledge-graph": { "graph_id": "..." }
  }
}
```

### Per-Service Tokens

For enhanced security, issue separate tokens per service:

```
SERVICE_TOKEN_CONTEXT_STORE=eyJ...
SERVICE_TOKEN_KNOWLEDGE_GRAPH=eyJ...
```

### Permission Levels

Add read/write permissions per service:

```json
{
  "services": {
    "context-store": {
      "namespace": "project-alpha",
      "permissions": ["read", "write"]
    }
  }
}
```

### Token Refresh

For long-running sessions, implement token refresh mechanism.

## References

### Implementation Documentation

- [Context Store Server README](../../../servers/context-store/README.md) - First implementing service
- [Context Store MCP](../../components/context-store/MCP.md) - MCP integration pattern

### External References

- [JWT RFC 7519](https://tools.ietf.org/html/rfc7519) - JSON Web Token standard
- [PyJWT Documentation](https://pyjwt.readthedocs.io/) - Python JWT library
