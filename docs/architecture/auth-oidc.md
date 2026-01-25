# OIDC Authentication Architecture with Auth0

## Overview

This document describes the authentication architecture using OpenID Connect (OIDC) with Auth0 as the Identity Provider (IdP). This replaces the static API key approach with industry-standard token-based authentication.

For setup instructions, see `docs/guides/auth0-setup.md`.

## System Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AUTH0 (IdP)                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Users     │  │   Roles     │  │    APIs     │  │   M2M Applications  │ │
│  │  Database   │  │ Permissions │  │  (audience) │  │   (Agent Runner)    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
         │                    │                              │
         │ Authorization      │ Access Token                 │ Client Credentials
         │ Code Flow + PKCE   │ Validation                   │ Flow
         ▼                    ▼                              ▼
┌─────────────────┐    ┌─────────────────┐           ┌─────────────────┐
│    Dashboard    │───▶│      Agent      │◀──────────│   Agent Runner  │
│    (React SPA)  │    │   Coordinator   │           │  (Python/M2M)   │
└─────────────────┘    │   (FastAPI)     │           └─────────────────┘
         │             └─────────────────┘
         │                    ▲
┌─────────────────┐           │
│    Chat UI      │───────────┘
│    (React SPA)  │
└─────────────────┘
```

---

## Authentication Flows

### Flow 1: Human Users (Dashboard, Chat UI)

Uses **Authorization Code Flow with PKCE** (Proof Key for Code Exchange).

```
User         Dashboard        Auth0           Agent Coordinator
  │              │              │                    │
  │ Click Login  │              │                    │
  │─────────────▶│              │                    │
  │              │ Generate PKCE│                    │
  │              │ Redirect     │                    │
  │◀─────────────│              │                    │
  │              │              │                    │
  │─────────────────────────────▶ /authorize        │
  │              │              │                    │
  │◀─────────────────────────────│ Login Page       │
  │              │              │                    │
  │ Authenticate─────────────────▶                  │
  │              │              │                    │
  │◀───────────────────────────── Redirect + code   │
  │              │              │                    │
  │─────────────▶│ Exchange code│                    │
  │              │─────────────▶│                    │
  │              │◀─────────────│ access_token      │
  │              │              │                    │
  │              │ API Request + Bearer token        │
  │              │─────────────────────────────────▶│
  │              │◀─────────────────────────────────│
```

### Flow 2: Machine-to-Machine (Agent Runner)

Uses **Client Credentials Flow**.

```
Agent Runner              Auth0              Agent Coordinator
     │                      │                       │
     │ POST /oauth/token    │                       │
     │ grant_type=          │                       │
     │ client_credentials   │                       │
     │─────────────────────▶│                       │
     │                      │                       │
     │◀─────────────────────│                       │
     │ { access_token }     │                       │
     │                      │                       │
     │ Cache token          │                       │
     │                      │                       │
     │ API Request + Bearer token                   │
     │─────────────────────────────────────────────▶│
     │◀─────────────────────────────────────────────│
```

---

## Auth0 Configuration Summary

### API (Resource Server)

| Setting | Value |
|---------|-------|
| Identifier (audience) | `https://agent-coordinator.local` |
| Signing Algorithm | RS256 |
| Enable RBAC | Yes |
| Add Permissions in Token | Yes |

### Permissions

| Permission | Description |
|------------|-------------|
| `admin:full` | Full administrative access |
| `runner:execute` | Register runners, poll for runs, report status |
| `user:runs` | Start runs on allowed blueprints |
| `user:sessions` | Read own sessions |
| `blueprints:read` | Read allowed blueprints |

### Roles

| Role | Permissions |
|------|-------------|
| `admin` | All permissions |
| `runner` | `runner:execute` |
| `user` | `user:runs`, `user:sessions`, `blueprints:read` |

### Applications

| Application | Type | Auth Method |
|-------------|------|-------------|
| Dashboard | Single Page Application | PKCE |
| Chat UI | Single Page Application | PKCE |
| Agent Runner | Machine to Machine | Client Credentials |

---

## Token Structure

### Access Token Claims

| Claim | Description |
|-------|-------------|
| `iss` | Issuer (`https://{domain}/`) |
| `sub` | Subject (user or client ID) |
| `aud` | Audience (API identifier) |
| `exp` | Expiration timestamp |
| `iat` | Issued at timestamp |
| `permissions` | Array of granted permissions |

### Custom Claims (Optional)

Blueprint access can be added via Auth0 Actions:
- Namespace: `https://agent-orchestrator.your-org.com/`
- Claim: `allowed_blueprints` (array of blueprint names)

---

## Permission Matrix

| Endpoint | Required Permission |
|----------|---------------------|
| `POST /runner/register` | `runner:execute` |
| `GET /runner/runs` | `runner:execute` |
| `POST /runner/runs/{id}/*` | `runner:execute` |
| `POST /runner/heartbeat` | `runner:execute` |
| `POST /runs` | `user:runs` + blueprint access |
| `GET /sessions/{id}` | `user:sessions` (own) or `admin:full` |
| `GET /sse/sessions` | `user:sessions` (own) or `admin:full` |
| `GET /blueprints` | `blueprints:read` (filtered) or `admin:full` |
| All other endpoints | `admin:full` |

---

## Token Validation

The Agent Coordinator validates tokens by:

1. Fetching JWKS from `https://{AUTH0_DOMAIN}/.well-known/jwks.json`
2. Extracting `kid` from JWT header
3. Verifying signature using RS256
4. Validating claims: `iss`, `aud`, `exp`
5. Extracting `permissions` for authorization

---

## Environment Variables

### Agent Coordinator

| Variable | Description |
|----------|-------------|
| `AUTH_ENABLED` | Set to `true` to enable authentication |
| `AUTH0_DOMAIN` | Auth0 tenant domain |
| `AUTH0_AUDIENCE` | API identifier |

### Dashboard / Chat UI

| Variable | Description |
|----------|-------------|
| `VITE_AUTH0_DOMAIN` | Auth0 tenant domain |
| `VITE_AUTH0_CLIENT_ID` | SPA client ID |
| `VITE_AUTH0_AUDIENCE` | API identifier |

### Agent Runner

| Variable | Description |
|----------|-------------|
| `AUTH0_DOMAIN` | Auth0 tenant domain |
| `AUTH0_CLIENT_ID` | M2M client ID |
| `AUTH0_CLIENT_SECRET` | M2M client secret |
| `AUTH0_AUDIENCE` | API identifier |

---

## SSE Authentication

EventSource API doesn't support custom headers. Two approaches:

| Approach | Method | Security |
|----------|--------|----------|
| Query Parameter | `?api_key={token}` | Token in logs/history |
| Fetch-based SSE | `ReadableStream` with headers | Recommended |

---

## Security Considerations

### Token Storage (SPAs)
- Store in memory only (not localStorage)
- Use refresh tokens for persistence

### Token Lifetime

| Token Type | Recommended TTL |
|------------|-----------------|
| Access Token (User) | 1 hour |
| Access Token (M2M) | 24 hours |
| Refresh Token | 7-30 days (with rotation) |

### Validation Requirements
- Always validate `aud` (audience)
- Always validate `iss` (issuer)
- Always check `exp` (expiration)
- Use RS256 (asymmetric signing)
- Cache JWKS with periodic refresh

---

## Comparison with API Keys

| Aspect | API Keys | OIDC (Auth0) |
|--------|----------|--------------|
| Setup complexity | Low | Medium |
| User management | Manual | Centralized |
| Token expiration | Manual rotation | Automatic |
| Revocation | Config change + restart | Immediate |
| Audit trail | Application logs | Auth0 logs |
| SSO support | No | Yes |
| MFA support | No | Yes |
| Per-user tracking | Limited | Full |
| Blueprint access | Config-based | Claims-based |

---

## Implementation Files

| Component | File |
|-----------|------|
| Coordinator Auth | `servers/agent-coordinator/auth.py` |
| Dashboard Auth | `dashboard/src/App.tsx`, `src/services/auth.ts` |
| Chat UI Auth | `interfaces/chat-ui/src/App.tsx` |
| Runner Auth | `servers/agent-runner/lib/auth0_client.py` |
