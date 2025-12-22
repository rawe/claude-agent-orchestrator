"""Authentication module for Agent Coordinator.

Simple API key authentication with startup validation.
See docs/architecture/auth-coordinator.md for design rationale.

Environment Variables:
    AUTH_DISABLED: Set to 'true' to disable authentication (development only).
                   Default: false
    ADMIN_API_KEY: Required API key for all endpoints when AUTH_DISABLED=false.
                   Application will fail to start if not set.

Usage:
    Clients must include the API key in requests:
        Authorization: Bearer <api_key>

    For SSE/EventSource (which doesn't support custom headers):
        ?api_key=<api_key>
"""

import os
from typing import Optional
from fastapi import HTTPException, Security, Query
from fastapi.security import APIKeyHeader

# Environment variables
AUTH_DISABLED = os.getenv("AUTH_DISABLED", "").lower() in ("true", "1", "yes")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

# API key header extractor
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


class AuthConfigError(Exception):
    """Raised when auth configuration is invalid."""
    pass


def validate_startup_config() -> None:
    """Validate auth configuration on startup.

    Raises:
        AuthConfigError: If AUTH_DISABLED=false and ADMIN_API_KEY is not set.
    """
    if not AUTH_DISABLED and not ADMIN_API_KEY:
        raise AuthConfigError(
            "Authentication is enabled but ADMIN_API_KEY is not set. "
            "Either set ADMIN_API_KEY environment variable or set AUTH_DISABLED=true for development."
        )


async def verify_api_key(
    authorization: str = Security(api_key_header),
    api_key: Optional[str] = Query(None, description="API key (for SSE/EventSource)")
) -> dict | None:
    """FastAPI dependency to verify API key.

    Supports two authentication methods:
    1. Authorization header: Bearer <api_key>
    2. Query parameter: ?api_key=<api_key> (for SSE/EventSource which doesn't support headers)

    Returns:
        dict with role info if authenticated, None if auth disabled.

    Raises:
        HTTPException 401: Missing or malformed credentials.
        HTTPException 403: Invalid API key.
    """
    if AUTH_DISABLED:
        return None

    token = None

    # Try Authorization header first
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
        else:
            raise HTTPException(
                status_code=401,
                detail="Invalid Authorization header format. Use 'Bearer <token>'"
            )
    # Fall back to query parameter (for SSE/EventSource)
    elif api_key:
        token = api_key

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing credentials. Use 'Authorization: Bearer <token>' header or '?api_key=<token>' query parameter."
        )

    # Validate against admin key
    if token == ADMIN_API_KEY:
        return {"role": "admin"}

    raise HTTPException(status_code=403, detail="Invalid API key")
