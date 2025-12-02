"""Central configuration for semantic search."""

from dataclasses import dataclass
import os


@dataclass
class SemanticConfig:
    """Central configuration for semantic search.

    All settings can be configured via environment variables.
    When disabled, the semantic search feature has zero overhead.
    """

    # Feature toggle
    enabled: bool = False

    # Ollama settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "nomic-embed-text"

    # Elasticsearch settings
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index: str = "context-store-vectors"

    # Chunking settings
    chunk_size: int = 1000  # characters per chunk
    chunk_overlap: int = 200  # overlap between chunks

    @classmethod
    def from_env(cls) -> "SemanticConfig":
        """Load configuration from environment variables."""
        return cls(
            enabled=os.getenv("SEMANTIC_SEARCH_ENABLED", "false").lower() == "true",
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"),
            elasticsearch_url=os.getenv("ELASTICSEARCH_URL", "http://localhost:9200"),
            elasticsearch_index=os.getenv("ELASTICSEARCH_INDEX", "context-store-vectors"),
            chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
        )


# Singleton instance - loaded once at module import
config = SemanticConfig.from_env()
