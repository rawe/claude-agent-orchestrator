"""Configuration for the Context Store client."""

import os
from typing import Optional


# HTTP Header for partition in HTTP mode
HEADER_CONTEXT_STORE_PARTITION = "X-Context-Store-Partition"
HEADER_CONTEXT_STORE_PARTITION_AUTO_CREATE = "X-Context-Store-Partition-Auto-Create"


class Config:
    """Configuration for Context Store client with environment variable support.

    Environment Variables:
        CONTEXT_STORE_HOST: Server hostname (default: localhost)
        CONTEXT_STORE_PORT: Server port (default: 8766)
        CONTEXT_STORE_SCHEME: URL scheme (default: http)
        CONTEXT_STORE_PARTITION: Partition name for stdio mode (default: None = global)
        CONTEXT_STORE_PARTITION_AUTO_CREATE: Auto-create partition if missing (default: false)
    """

    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 8766
    DEFAULT_SCHEME = "http"

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        scheme: str | None = None,
        partition: str | None = None,
        partition_auto_create: bool | None = None,
    ):
        """Initialize configuration from parameters or environment variables.

        Args:
            host: Server hostname (overrides CONTEXT_STORE_HOST env var)
            port: Server port (overrides CONTEXT_STORE_PORT env var)
            scheme: URL scheme (overrides CONTEXT_STORE_SCHEME env var)
            partition: Partition name (overrides CONTEXT_STORE_PARTITION env var)
            partition_auto_create: Auto-create partition (overrides CONTEXT_STORE_PARTITION_AUTO_CREATE env var)
        """
        self.host = host or os.getenv("CONTEXT_STORE_HOST", self.DEFAULT_HOST)
        self.port = port or int(os.getenv("CONTEXT_STORE_PORT", str(self.DEFAULT_PORT)))
        self.scheme = scheme or os.getenv("CONTEXT_STORE_SCHEME", self.DEFAULT_SCHEME)
        self.partition = partition or os.getenv("CONTEXT_STORE_PARTITION") or None
        if partition_auto_create is not None:
            self.partition_auto_create = partition_auto_create
        else:
            self.partition_auto_create = (
                os.getenv("CONTEXT_STORE_PARTITION_AUTO_CREATE", "").lower() == "true"
            )

    @property
    def base_url(self) -> str:
        """Construct the full base URL for the Context Store server."""
        return f"{self.scheme}://{self.host}:{self.port}"


def get_partition_from_context(config: Config) -> Optional[str]:
    """Get partition from HTTP headers (HTTP mode) or config (stdio mode).

    In HTTP mode, reads from X-Context-Store-Partition header.
    In stdio mode, uses config.partition from CONTEXT_STORE_PARTITION env var.

    No fallback between modes - HTTP mode ignores env var.

    Returns:
        Partition name or None (None = use global partition endpoints)
    """
    try:
        from fastmcp.server.dependencies import get_http_headers

        headers = get_http_headers()
        # If we have HTTP headers, we're in HTTP mode - use header only
        # Headers are returned with lowercase keys
        if headers is not None:
            return headers.get(HEADER_CONTEXT_STORE_PARTITION.lower())
    except Exception:
        # Not in HTTP context or FastMCP not available - use stdio mode
        pass

    # stdio mode - use config
    return config.partition


def get_partition_auto_create_from_context(config: Config) -> bool:
    """Get auto-create setting from HTTP headers or config.

    In HTTP mode, reads from X-Context-Store-Partition-Auto-Create header.
    In stdio mode, uses config.partition_auto_create from CONTEXT_STORE_PARTITION_AUTO_CREATE env var.

    No fallback between modes - HTTP mode ignores env var.

    Returns:
        True if auto-create is enabled, False otherwise
    """
    try:
        from fastmcp.server.dependencies import get_http_headers

        headers = get_http_headers()
        if headers is not None:
            value = headers.get(HEADER_CONTEXT_STORE_PARTITION_AUTO_CREATE.lower(), "")
            return value.lower() == "true"
    except Exception:
        pass

    return config.partition_auto_create
