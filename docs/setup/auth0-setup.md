# Auth0 Setup Guide

This guide documents the steps to configure Auth0 authentication for the Agent Orchestrator Framework.

## Overview

| Component | Auth0 Application Type | Status |
|-----------|------------------------|--------|
| Dashboard | Single Page Application | Implemented |
| Chat UI | Single Page Application | Implemented |
| Agent Coordinator | API (Resource Server) | Implemented |
| Agent Runner | Machine-to-Machine | Implemented |

---

## Part 1: Auth0 Configuration

### 1.1 Create Auth0 Account

1. Go to [auth0.com](https://auth0.com) and sign up
2. Create a new tenant (e.g., `your-org`)
3. Note your tenant domain: `your-org.auth0.com`

### 1.2 Create API (Resource Server)

The API represents your Agent Coordinator backend.

1. Navigate to **Applications → APIs**
2. Click **Create API**
3. Configure:

| Field | Value | Notes |
|-------|-------|-------|
| Name | `Agent Coordinator API` | Display name |
| Identifier | `https://agent-coordinator.local` | This becomes the `audience` value. Can be any unique URI. |
| Signing Algorithm | `RS256` | Asymmetric signing (recommended) |

4. Click **Create**
5. Go to the **Settings** tab of the newly created API
6. Scroll down to **Access Token Settings**
7. Set **JSON Web Token (JWT) Profile** to: **RFC 9068 (Recommended)**

> **Why RFC 9068?** This profile standardizes JWT access tokens with proper claims (`iss`, `sub`, `aud`, `exp`, `iat`, `jti`, `client_id`). It ensures interoperability and follows OAuth 2.0 best practices.

8. Click **Save**

### 1.3 Create Dashboard Application

1. Navigate to **Applications → Applications**
2. Click **Create Application**
3. Configure:

| Field | Value |
|-------|-------|
| Name | `Agent Orchestrator Dashboard` |
| Application Type | **Single Page Application** |

4. Click **Create**
5. Go to the **Settings** tab
6. Configure URLs:

| Field | Development | Production |
|-------|-------------|------------|
| Allowed Callback URLs | `http://localhost:3000` | `https://dashboard.your-domain.com` |
| Allowed Logout URLs | `http://localhost:3000` | `https://dashboard.your-domain.com` |
| Allowed Web Origins | `http://localhost:3000` | `https://dashboard.your-domain.com` |

> **Note**: Separate multiple URLs with commas.

7. Scroll down and click **Save Changes**
8. Copy these values for later:

| Value | Where to Find |
|-------|---------------|
| Domain | Settings → Domain (e.g., `your-org.auth0.com`) |
| Client ID | Settings → Client ID |

### 1.4 Create Chat UI Application (Optional)

Repeat step 1.3 for the Chat UI with appropriate URLs:

| Field | Development | Production |
|-------|-------------|------------|
| Allowed Callback URLs | `http://localhost:5173` | `https://chat.your-domain.com` |
| Allowed Logout URLs | `http://localhost:5173` | `https://chat.your-domain.com` |
| Allowed Web Origins | `http://localhost:5173` | `https://chat.your-domain.com` |

### 1.5 Create Agent Runner Application (For Backend M2M)

This is for machine-to-machine authentication between Agent Runner and Agent Coordinator.

1. Navigate to **Applications → Applications**
2. Click **Create Application**
3. Configure:

| Field | Value |
|-------|-------|
| Name | `Agent Runner` |
| Application Type | **Machine to Machine** |

4. Click **Create**
5. Select the API to authorize: **Agent Coordinator API**
6. Select permissions (scopes) to grant: (define these in API settings first)
7. **Important**: Configure Grant Type:
   - Go to **Settings** tab
   - Scroll to **Credentials** section
   - Change **Authentication Method** from `Token Vault` to `Client Credentials`
   - Click **Save Changes**

> **Why?** Auth0 may default to "Token Vault" which doesn't support the `client_credentials` grant. Without this change, you'll get error: `Grant type 'client_credentials' not allowed for the client.`

8. Verify API authorization: Go to **APIs** tab → confirm **Agent Coordinator API** is listed and authorized.

9. Copy these values:

| Value | Where to Find |
|-------|---------------|
| Client ID | Settings → Client ID |
| Client Secret | Settings → Client Secret |

> **Security**: Never expose Client Secret in frontend code or version control.

### 1.6 Summary of Auth0 Values

After setup, you should have:

```
# Auth0 Tenant
AUTH0_DOMAIN=your-org.auth0.com

# API Identifier (audience)
AUTH0_AUDIENCE=https://agent-coordinator.local

# Dashboard App
DASHBOARD_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Chat UI App (if created)
CHAT_UI_CLIENT_ID=yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy

# Agent Runner M2M (for backend)
RUNNER_CLIENT_ID=zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz
RUNNER_CLIENT_SECRET=<keep-secret>
```

---

## Part 2: Dashboard Configuration

### 2.1 Environment Variables

Create or update `dashboard/.env.local`:

```bash
# Existing configuration
VITE_AGENT_ORCHESTRATOR_API_URL=http://localhost:8765
VITE_DOCUMENT_SERVER_URL=http://localhost:8766
VITE_AGENT_ORCHESTRATOR_API_KEY=your-api-key-here

# Auth0 Configuration
VITE_AUTH0_DOMAIN=your-org.auth0.com
VITE_AUTH0_CLIENT_ID=your-dashboard-client-id
VITE_AUTH0_AUDIENCE=https://agent-coordinator.local
```

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_AUTH0_DOMAIN` | Yes | Your Auth0 tenant domain |
| `VITE_AUTH0_CLIENT_ID` | Yes | Dashboard application Client ID |
| `VITE_AUTH0_AUDIENCE` | Yes | API identifier (must match Auth0 API) |

### 2.2 Behavior

With Auth0 configured:

| State | UI Shows | API Auth |
|-------|----------|----------|
| Not logged in | Login button | Falls back to `VITE_AGENT_ORCHESTRATOR_API_KEY` |
| Logged in | User name + avatar + logout | Uses Auth0 access token |

### 2.3 Testing

1. Start the dashboard: `npm run dev`
2. Click **Login** button in header
3. Authenticate with Auth0
4. Verify:
   - User name appears in header
   - Open DevTools → Network → check API requests have `Authorization: Bearer eyJ...` header

### 2.4 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Callback URL mismatch" | Add your URL to Allowed Callback URLs in Auth0 |
| Login works but no API token | Verify `VITE_AUTH0_AUDIENCE` matches API Identifier exactly |
| "Invalid audience" error | Re-login after adding/changing audience |

---

## Part 3: Agent Coordinator Configuration (Backend)

> **Status**: Implemented in `servers/agent-coordinator/auth.py`

### 3.1 Environment Variables

Add to root `.env` or set in your environment:

```bash
# Auth0 Configuration
AUTH0_DOMAIN=your-org.auth0.com
AUTH0_AUDIENCE=https://agent-coordinator.local

# Legacy API Key (keep during migration)
ADMIN_API_KEY=your-current-api-key

# Disable auth for development (optional)
AUTH_DISABLED=false
```

| Variable | Required | Description |
|----------|----------|-------------|
| `AUTH0_DOMAIN` | Yes* | Your Auth0 tenant domain |
| `AUTH0_AUDIENCE` | Yes* | API identifier (for token validation) |
| `ADMIN_API_KEY` | Yes* | Legacy API key (for migration period) |
| `AUTH_DISABLED` | No | Set `true` to disable all auth |

*At least one auth method (API key or OIDC) must be configured.

### 3.2 Token Validation

The Agent Coordinator validates JWT tokens by:

1. Checking if token looks like a JWT (3 dot-separated parts)
2. Fetching JWKS from `https://{AUTH0_DOMAIN}/.well-known/jwks.json`
3. Extracting the key ID (`kid`) from JWT header
4. Verifying JWT signature using RS256 with the matching public key
5. Validating claims:
   - `iss` (issuer) = `https://{AUTH0_DOMAIN}/`
   - `aud` (audience) = `{AUTH0_AUDIENCE}`
   - `exp` (expiration) > current time

### 3.3 Dual-Auth Period

Both authentication methods work simultaneously:

```
Request with Bearer token
         │
         ▼
┌─────────────────────┐
│ Is it API key?      │──Yes──▶ Return role: admin, auth_type: api_key
└─────────────────────┘
         │ No
         ▼
┌─────────────────────┐
│ Is it a JWT?        │──Yes──▶ Validate with Auth0 JWKS
└─────────────────────┘         │
         │ No                   ▼
         ▼              ┌─────────────────────┐
    403 Forbidden       │ Extract permissions │
                        │ Map to role         │
                        └─────────────────────┘
```

### 3.4 Role Mapping

The coordinator maps Auth0 permissions to roles:

| Auth0 Permission | Assigned Role |
|------------------|---------------|
| `admin:full` | `admin` |
| `runner:execute` | `runner` |
| `user:runs` or `user:sessions` | `user` |
| (valid JWT, no permissions) | `authenticated` |

### 3.5 Auth Info Returned

On successful authentication, `verify_api_key()` returns:

```python
# API Key auth
{"role": "admin", "auth_type": "api_key"}

# OIDC auth
{
    "role": "user",           # Mapped from permissions
    "auth_type": "oidc",
    "sub": "auth0|123...",    # User ID from Auth0
    "email": "user@example.com",
    "permissions": ["user:runs", "user:sessions"]
}
```

### 3.6 Testing

1. Start coordinator with Auth0 env vars set
2. Login to Dashboard
3. Make an API call
4. Check coordinator logs for: `JWT validated for sub: auth0|xxxxx`

---

## Part 4: Agent Runner Configuration (Backend M2M)

> **Status**: Implemented in `servers/agent-runner/lib/auth0_client.py`

### 4.1 Environment Variables

```bash
# Auth0 M2M Configuration
AUTH0_DOMAIN=your-org.auth0.com
AUTH0_CLIENT_ID=your-runner-client-id
AUTH0_CLIENT_SECRET=your-runner-client-secret
AUTH0_AUDIENCE=https://agent-coordinator.local

# Legacy API Key (keep during migration)
AGENT_ORCHESTRATOR_API_KEY=your-current-api-key
```

| Variable | Required | Description |
|----------|----------|-------------|
| `AUTH0_DOMAIN` | Yes* | Your Auth0 tenant domain |
| `AUTH0_CLIENT_ID` | Yes* | M2M application Client ID |
| `AUTH0_CLIENT_SECRET` | Yes* | M2M application Client Secret |
| `AUTH0_AUDIENCE` | Yes* | API identifier |
| `AGENT_ORCHESTRATOR_API_KEY` | No | Legacy API key (fallback) |

*All four Auth0 variables must be set for OIDC authentication. Falls back to API key if not configured.

### 4.2 Token Flow

The Agent Runner uses Client Credentials flow:

```
┌──────────────┐                    ┌──────────┐
│ Agent Runner │                    │  Auth0   │
└──────┬───────┘                    └────┬─────┘
       │                                 │
       │ POST /oauth/token               │
       │ grant_type=client_credentials   │
       │ client_id=...                   │
       │ client_secret=...               │
       │ audience=...                    │
       │────────────────────────────────▶│
       │                                 │
       │◀────────────────────────────────│
       │ { access_token, expires_in }    │
       │                                 │
```

### 4.3 Token Caching

The `Auth0M2MClient` automatically:
- Caches access tokens in memory
- Refreshes 60 seconds before expiry
- Falls back to API key if token request fails

### 4.4 Auth Priority

The API client uses this order:
1. **Auth0 token** (if all 4 env vars configured)
2. **API key** (fallback if Auth0 not configured or token fails)

### 4.5 Testing

Start the runner and check logs for:
```
Auth0 M2M authentication enabled
Obtained new Auth0 access token (expires in 86400s)
```

---

## Part 5: Chat UI Configuration

> **Status**: Implemented in `interfaces/chat-ui/src/`

### 5.1 Environment Variables

Create `interfaces/chat-ui/.env.local`:

```bash
# Existing configuration
VITE_API_URL=http://localhost:8765
VITE_AGENT_ORCHESTRATOR_API_KEY=your-api-key-here

# Auth0 Configuration
VITE_AUTH0_DOMAIN=your-org.auth0.com
VITE_AUTH0_CLIENT_ID=your-chat-ui-client-id
VITE_AUTH0_AUDIENCE=https://agent-coordinator.local
```

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_AUTH0_DOMAIN` | Yes | Your Auth0 tenant domain |
| `VITE_AUTH0_CLIENT_ID` | Yes | Chat UI application Client ID |
| `VITE_AUTH0_AUDIENCE` | Yes | API identifier (must match Auth0 API) |

### 5.2 Behavior

Same as Dashboard - when all Auth0 variables are set, login is required before using the app.

### 5.3 Auth0 Application Setup

In Auth0 Dashboard, create a separate SPA for Chat UI:

| Field | Development | Production |
|-------|-------------|------------|
| Allowed Callback URLs | `http://localhost:5173` | `https://chat.your-domain.com` |
| Allowed Logout URLs | `http://localhost:5173` | `https://chat.your-domain.com` |
| Allowed Web Origins | `http://localhost:5173` | `https://chat.your-domain.com` |

---

## Quick Reference

### Auth0 Dashboard URLs

| Page | URL |
|------|-----|
| Dashboard | https://manage.auth0.com/dashboard |
| Applications | https://manage.auth0.com/dashboard/us/{tenant}/applications |
| APIs | https://manage.auth0.com/dashboard/us/{tenant}/apis |

### Required Auth0 Settings per Component

| Component | Domain | Client ID | Client Secret | Audience |
|-----------|--------|-----------|---------------|----------|
| Dashboard | Yes | Yes | No | Yes |
| Chat UI | Yes | Yes | No | Yes |
| Agent Coordinator | Yes | No | No | Yes |
| Agent Runner | Yes | Yes | Yes | Yes |

### Environment Variable Naming

| Component | Prefix | Example |
|-----------|--------|---------|
| Dashboard | `VITE_` | `VITE_AUTH0_DOMAIN` |
| Chat UI | `VITE_` | `VITE_AUTH0_DOMAIN` |
| Agent Coordinator | None | `AUTH0_DOMAIN` |
| Agent Runner | None | `AUTH0_DOMAIN` |
