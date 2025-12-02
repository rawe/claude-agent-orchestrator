"""Indexer for semantic search - handles chunking, embedding, and storage."""

import logging
from typing import Optional

from .config import config

logger = logging.getLogger(__name__)


def chunk_text(text: str) -> list[dict]:
    """
    Split text into overlapping chunks.

    Returns a list of dicts with char_start, char_end for each chunk.
    """
    chunks = []
    text_length = len(text)

    if text_length == 0:
        return chunks

    start = 0
    while start < text_length:
        end = min(start + config.chunk_size, text_length)
        chunks.append({
            "char_start": start,
            "char_end": end,
            "text": text[start:end],
        })

        # Move to next chunk with overlap
        start = start + config.chunk_size - config.chunk_overlap

        # Avoid infinite loop for very small texts
        if start >= text_length:
            break

    return chunks


# Lazy-loaded clients (only initialized when semantic search is enabled)
_embeddings = None
_es_client = None


def _get_embeddings():
    """Get or create Ollama embeddings client."""
    global _embeddings
    if _embeddings is None:
        from langchain_ollama import OllamaEmbeddings
        _embeddings = OllamaEmbeddings(
            base_url=config.ollama_base_url,
            model=config.ollama_model,
        )
    return _embeddings


def _get_es_client():
    """Get or create Elasticsearch client."""
    global _es_client
    if _es_client is None:
        from elasticsearch import Elasticsearch
        _es_client = Elasticsearch(config.elasticsearch_url)
        _ensure_index_exists()
    return _es_client


def _ensure_index_exists():
    """Create the Elasticsearch index if it doesn't exist."""
    es = _get_es_client()

    if not es.indices.exists(index=config.elasticsearch_index):
        mapping = {
            "mappings": {
                "properties": {
                    "context_store_document_id": {"type": "keyword"},
                    "char_start": {"type": "integer"},
                    "char_end": {"type": "integer"},
                    "embedding": {
                        "type": "dense_vector",
                        "dims": 768,
                        "index": True,
                        "similarity": "cosine"
                    }
                }
            }
        }
        es.indices.create(index=config.elasticsearch_index, body=mapping)
        logger.info(f"Created Elasticsearch index: {config.elasticsearch_index}")


def index_document(document_id: str, content: str) -> bool:
    """
    Index a document for semantic search.

    Chunks the content, generates embeddings, and stores in Elasticsearch.
    Returns True if indexing succeeded, False otherwise.
    """
    if not config.enabled:
        return False

    try:
        # Chunk the content
        chunks = chunk_text(content)
        if not chunks:
            logger.warning(f"No chunks generated for document {document_id}")
            return True  # Empty document is not an error

        # Get embeddings for all chunk texts
        embeddings_client = _get_embeddings()
        texts = [chunk["text"] for chunk in chunks]
        embeddings = embeddings_client.embed_documents(texts)

        # Store chunks in Elasticsearch
        es = _get_es_client()
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            doc = {
                "context_store_document_id": document_id,
                "char_start": chunk["char_start"],
                "char_end": chunk["char_end"],
                "embedding": embedding,
            }
            es.index(index=config.elasticsearch_index, document=doc)

        logger.info(f"Indexed {len(chunks)} chunks for document {document_id}")
        return True

    except Exception as e:
        logger.warning(f"Failed to index document {document_id}: {e}")
        return False


def delete_document_index(document_id: str) -> bool:
    """
    Delete all indexed chunks for a document.

    Returns True if deletion succeeded, False otherwise.
    """
    if not config.enabled:
        return False

    try:
        es = _get_es_client()

        # Delete all chunks with this document ID
        es.delete_by_query(
            index=config.elasticsearch_index,
            body={
                "query": {
                    "term": {
                        "context_store_document_id": document_id
                    }
                }
            }
        )

        logger.info(f"Deleted index entries for document {document_id}")
        return True

    except Exception as e:
        logger.warning(f"Failed to delete index for document {document_id}: {e}")
        return False
