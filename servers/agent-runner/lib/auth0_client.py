"""Auth0 M2M (Machine-to-Machine) authentication client.

Uses the Client Credentials flow to obtain access tokens for API calls.
Tokens are cached and refreshed automatically before expiry.
"""

import time
import logging
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class TokenCache:
    """Cached access token with expiry."""
    access_token: str
    expires_at: float  # Unix timestamp


class Auth0M2MClient:
    """Client for Auth0 Client Credentials flow."""

    def __init__(
        self,
        domain: str,
        client_id: str,
        client_secret: str,
        audience: str,
    ):
        """Initialize Auth0 M2M client.

        Args:
            domain: Auth0 tenant domain (e.g., 'your-org.auth0.com')
            client_id: M2M application client ID
            client_secret: M2M application client secret
            audience: API identifier (must match coordinator's AUTH0_AUDIENCE)
        """
        self.domain = domain
        self.client_id = client_id
        self.client_secret = client_secret
        self.audience = audience
        self._token_cache: Optional[TokenCache] = None
        self._http = httpx.Client(timeout=30.0)

    @property
    def is_configured(self) -> bool:
        """Check if all required Auth0 settings are present."""
        return bool(
            self.domain
            and self.client_id
            and self.client_secret
            and self.audience
        )

    def get_access_token(self) -> Optional[str]:
        """Get a valid access token, refreshing if needed.

        Returns:
            Access token string, or None if not configured or on error.
        """
        if not self.is_configured:
            return None

        # Check cache (refresh 60 seconds before expiry)
        if self._token_cache and time.time() < self._token_cache.expires_at - 60:
            return self._token_cache.access_token

        # Request new token
        try:
            response = self._http.post(
                f"https://{self.domain}/oauth/token",
                json={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "audience": self.audience,
                },
            )
            response.raise_for_status()
            data = response.json()

            # Cache token
            self._token_cache = TokenCache(
                access_token=data["access_token"],
                expires_at=time.time() + data.get("expires_in", 3600),
            )

            logger.debug(f"Obtained new Auth0 access token (expires in {data.get('expires_in', 3600)}s)")
            return self._token_cache.access_token

        except httpx.HTTPStatusError as e:
            logger.error(f"Auth0 token request failed: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Auth0 token request failed: {e}")
            return None

    def close(self):
        """Close the HTTP client."""
        self._http.close()
