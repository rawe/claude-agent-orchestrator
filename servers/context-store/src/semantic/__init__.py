"""Semantic search module for Context Store.

This module provides semantic search capabilities using:
- Ollama for embeddings
- Elasticsearch for vector storage and similarity search
- LangChain for orchestration

The entire feature can be enabled/disabled via SEMANTIC_SEARCH_ENABLED env var.
"""

from .config import SemanticConfig, config

__all__ = ["SemanticConfig", "config"]
