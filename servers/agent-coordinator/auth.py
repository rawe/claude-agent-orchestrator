"""Authentication module for Agent Coordinator.

Supports both API key and OIDC (Auth0) authentication.
See docs/architecture/auth-coordinator.md for design rationale.

Environment Variables:
    AUTH_DISABLED: Set to 'true' to disable authentication (development only).
    ADMIN_API_KEY: API key for admin access (optional if using OIDC).
    AUTH0_DOMAIN: Auth0 tenant domain (e.g., 'your-org.auth0.com').
    AUTH0_AUDIENCE: API identifier configured in Auth0.

Usage:
    Clients can authenticate via:
    1. Authorization header: Bearer <api_key_or_jwt>
    2. Query parameter: ?api_key=<token> (for SSE/EventSource)
"""

import os
import logging
from typing import Optional
from functools import lru_cache

import jwt
import httpx
from fastapi import HTTPException, Security, Query
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

# Environment variables
AUTH_DISABLED = os.getenv("AUTH_DISABLED", "").lower() in ("true", "1", "yes")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

# Auth0/OIDC configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE", "")

# API key header extractor
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


class AuthConfigError(Exception):
    """Raised when auth configuration is invalid."""
    pass


class JWKSClient:
    """Simple JWKS client for fetching Auth0 public keys."""

    def __init__(self, domain: str):
        self.jwks_url = f"https://{domain}/.well-known/jwks.json"
        self._keys: dict = {}
        self._http = httpx.Client(timeout=10.0)

    def get_signing_key(self, kid: str) -> dict:
        """Get the signing key for the given key ID."""
        if kid not in self._keys:
            self._refresh_keys()
        if kid not in self._keys:
            raise ValueError(f"Key {kid} not found in JWKS")
        return self._keys[kid]

    def _refresh_keys(self):
        """Fetch keys from JWKS endpoint."""
        try:
            response = self._http.get(self.jwks_url)
            response.raise_for_status()
            jwks = response.json()
            self._keys = {key["kid"]: key for key in jwks.get("keys", [])}
            logger.debug(f"Refreshed JWKS, found {len(self._keys)} keys")
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            raise


@lru_cache()
def get_jwks_client() -> Optional[JWKSClient]:
    """Get cached JWKS client (singleton)."""
    if not AUTH0_DOMAIN:
        return None
    return JWKSClient(AUTH0_DOMAIN)


def _is_jwt(token: str) -> bool:
    """Check if a token looks like a JWT (has 3 dot-separated parts)."""
    return token.count(".") == 2


def _validate_jwt(token: str) -> Optional[dict]:
    """Validate a JWT token against Auth0.

    Returns:
        Token claims if valid, None if invalid.
    """
    if not AUTH0_DOMAIN or not AUTH0_AUDIENCE:
        return None

    jwks_client = get_jwks_client()
    if not jwks_client:
        return None

    try:
        # Decode header to get key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            logger.debug("JWT missing kid in header")
            return None

        # Get signing key from JWKS
        jwk = jwks_client.get_signing_key(kid)
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)

        # Decode and validate token
        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=AUTH0_AUDIENCE,
            issuer=f"https://{AUTH0_DOMAIN}/",
        )

        logger.debug(f"JWT validated for sub: {claims.get('sub')}")
        return claims

    except jwt.ExpiredSignatureError:
        logger.debug("JWT expired")
        return None
    except jwt.InvalidAudienceError:
        logger.debug("JWT invalid audience")
        return None
    except jwt.InvalidIssuerError:
        logger.debug("JWT invalid issuer")
        return None
    except Exception as e:
        logger.debug(f"JWT validation failed: {e}")
        return None


def validate_startup_config() -> None:
    """Validate auth configuration on startup.

    Raises:
        AuthConfigError: If authentication is enabled but not properly configured.
    """
    if AUTH_DISABLED:
        logger.warning("Authentication is DISABLED - all requests will be allowed")
        return

    has_api_key = bool(ADMIN_API_KEY)
    has_oidc = bool(AUTH0_DOMAIN and AUTH0_AUDIENCE)

    if not has_api_key and not has_oidc:
        raise AuthConfigError(
            "Authentication is enabled but no auth method configured. "
            "Set ADMIN_API_KEY for API key auth, or AUTH0_DOMAIN + AUTH0_AUDIENCE for OIDC, "
            "or set AUTH_DISABLED=true for development."
        )

    if has_oidc:
        logger.info(f"OIDC authentication enabled (Auth0 domain: {AUTH0_DOMAIN})")
    if has_api_key:
        logger.info("API key authentication enabled")


async def verify_api_key(
    authorization: str = Security(api_key_header),
    api_key: Optional[str] = Query(None, description="API key or JWT (for SSE/EventSource)")
) -> dict | None:
    """FastAPI dependency to verify authentication.

    Supports:
    1. API key authentication (static key)
    2. OIDC JWT authentication (Auth0)

    Returns:
        dict with auth info if authenticated, None if auth disabled.

    Raises:
        HTTPException 401: Missing or malformed credentials.
        HTTPException 403: Invalid credentials.
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

    # Check if it's an API key (not a JWT)
    if ADMIN_API_KEY and token == ADMIN_API_KEY:
        return {"role": "admin", "auth_type": "api_key"}

    # Try JWT validation if it looks like a JWT
    if _is_jwt(token) and AUTH0_DOMAIN:
        claims = _validate_jwt(token)
        if claims:
            # Extract permissions from token
            permissions = claims.get("permissions", [])

            # Map permissions to role
            if "admin:full" in permissions:
                role = "admin"
            elif "runner:execute" in permissions:
                role = "runner"
            elif "user:runs" in permissions or "user:sessions" in permissions:
                role = "user"
            else:
                role = "authenticated"  # Valid token but no specific permissions

            return {
                "role": role,
                "auth_type": "oidc",
                "sub": claims.get("sub"),
                "email": claims.get("email"),
                "permissions": permissions,
            }

    raise HTTPException(status_code=403, detail="Invalid credentials")
