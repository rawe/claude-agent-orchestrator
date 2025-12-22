# Migration Guide: API Keys to OIDC (Auth0)

## Overview

This guide describes how to migrate from static API key authentication to OIDC with Auth0. The migration is designed to be gradual, allowing both authentication methods to work simultaneously during the transition period.


## Migration Phases

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MIGRATION TIMELINE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 1          Phase 2              Phase 3            Phase 4           │
│  Auth0 Setup      Backend Dual-Auth    Frontend Migration API Key Removal   │
│                                                                             │
│  ┌──────────┐     ┌──────────────┐     ┌──────────────┐   ┌──────────────┐  │
│  │ Configure│     │ Coordinator  │     │ Dashboard    │   │ Remove API   │  │
│  │ Auth0    │────▶│ accepts both │────▶│ Chat UI      │──▶│ key support  │  │
│  │ Tenant   │     │ API keys +   │     │ use OIDC     │   │ from all     │  │
│  │          │     │ OIDC tokens  │     │              │   │ components   │  │
│  └──────────┘     └──────────────┘     └──────────────┘   └──────────────┘  │
│                                                                             │
│  No downtime      No downtime          Gradual rollout    Cleanup           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

Phase 1-4 are done. This document details Phase 5: Cleanup.


## Phase 5: Cleanup

After all components are using OIDC successfully:

### Step 5.1: Remove API Key Support from Coordinator

```python
# Remove from auth.py:
# - ADMIN_API_KEY handling
# - Legacy token validation

# Update validate_startup_config():
def validate_startup_config() -> None:
    if AUTH_DISABLED:
        return
    if not AUTH0_DOMAIN or not AUTH0_AUDIENCE:
        raise AuthConfigError(
            "AUTH0_DOMAIN and AUTH0_AUDIENCE must be set when auth is enabled."
        )
```

### Step 5.2: Remove API Key from Frontends

```typescript
// Remove from config:
// - VITE_AGENT_ORCHESTRATOR_API_KEY
// - VITE_USE_OIDC_AUTH (always OIDC now)
// - Legacy auth code paths
```

### Step 5.3: Remove API Key from Agent Runner

```python
# Remove from config.py:
# - ENV_API_KEY
# - api_key property

# Remove from api_client.py:
# - api_key fallback
```

### Step 5.4: Remove Environment Variables

```bash
# Remove from all environments:
# - ADMIN_API_KEY
# - AGENT_ORCHESTRATOR_API_KEY
# - VITE_AGENT_ORCHESTRATOR_API_KEY
```

---


---

## Testing Checklist


### Phase 5 (Cleanup)
- [ ] API keys no longer work
- [ ] Only OIDC authentication accepted
- [ ] Error messages reference OIDC, not API keys
- [ ] Documentation updated

---
