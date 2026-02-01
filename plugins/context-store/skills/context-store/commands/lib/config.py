"""Configuration module for document sync client."""
import os


class Config:
    """Configuration for document sync client with environment variable support."""

    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 8766
    DEFAULT_SCHEME = "http"

    def __init__(self):
        """Initialize configuration from environment variables or defaults.

        Environment Variables:
            DOC_SYNC_HOST: Server hostname (default: localhost)
            DOC_SYNC_PORT: Server port (default: 8766)
            DOC_SYNC_SCHEME: URL scheme (default: http)
            DOC_SYNC_PARTITION: Default partition name (default: None = global partition)
        """
        self.host = os.getenv("DOC_SYNC_HOST", self.DEFAULT_HOST)
        self.port = int(os.getenv("DOC_SYNC_PORT", str(self.DEFAULT_PORT)))
        self.scheme = os.getenv("DOC_SYNC_SCHEME", self.DEFAULT_SCHEME)
        # Partition: empty string or unset -> None (global partition)
        partition_env = os.getenv("DOC_SYNC_PARTITION", "")
        self.partition = partition_env if partition_env else None

    @property
    def base_url(self) -> str:
        """Construct the full base URL for the document server."""
        return f"{self.scheme}://{self.host}:{self.port}"
