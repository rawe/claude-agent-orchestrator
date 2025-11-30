"""Configuration module for document sync client."""
import os


class Config:
    """Configuration for document sync client with environment variable support."""

    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 8766
    DEFAULT_SCHEME = "http"

    def __init__(self):
        """Initialize configuration from environment variables or defaults."""
        self.host = os.getenv("DOC_SYNC_HOST", self.DEFAULT_HOST)
        self.port = int(os.getenv("DOC_SYNC_PORT", str(self.DEFAULT_PORT)))
        self.scheme = os.getenv("DOC_SYNC_SCHEME", self.DEFAULT_SCHEME)

    @property
    def base_url(self) -> str:
        """Construct the full base URL for the document server."""
        return f"{self.scheme}://{self.host}:{self.port}"
