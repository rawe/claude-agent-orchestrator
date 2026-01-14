"""Configuration for the Context Store client."""

import os


class Config:
    """Configuration for Context Store client with environment variable support.

    Environment Variables:
        CONTEXT_STORE_HOST: Server hostname (default: localhost)
        CONTEXT_STORE_PORT: Server port (default: 8766)
        CONTEXT_STORE_SCHEME: URL scheme (default: http)
    """

    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 8766
    DEFAULT_SCHEME = "http"

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        scheme: str | None = None,
    ):
        """Initialize configuration from parameters or environment variables.

        Args:
            host: Server hostname (overrides CONTEXT_STORE_HOST env var)
            port: Server port (overrides CONTEXT_STORE_PORT env var)
            scheme: URL scheme (overrides CONTEXT_STORE_SCHEME env var)
        """
        self.host = host or os.getenv("CONTEXT_STORE_HOST", self.DEFAULT_HOST)
        self.port = port or int(os.getenv("CONTEXT_STORE_PORT", str(self.DEFAULT_PORT)))
        self.scheme = scheme or os.getenv("CONTEXT_STORE_SCHEME", self.DEFAULT_SCHEME)

    @property
    def base_url(self) -> str:
        """Construct the full base URL for the Context Store server."""
        return f"{self.scheme}://{self.host}:{self.port}"
