"""Search module for semantic search - handles query embedding and similarity search."""

import logging
from collections import defaultdict
from typing import Optional

from .config import config
from .indexer import _get_embeddings, _get_es_client

logger = logging.getLogger(__name__)


def search_documents(query: str, limit: int = 10) -> list[dict]:
    """
    Search for documents semantically similar to the query.

    Returns a list of results aggregated by document, with multiple
    matching sections per document.

    Args:
        query: Natural language search query
        limit: Maximum number of documents to return

    Returns:
        List of dicts with document_id, sections (offset, limit, score)
    """
    if not config.enabled:
        return []

    try:
        # Generate embedding for the query
        embeddings_client = _get_embeddings()
        query_embedding = embeddings_client.embed_query(query)

        # Search Elasticsearch
        es = _get_es_client()

        # KNN search for similar vectors
        search_body = {
            "knn": {
                "field": "embedding",
                "query_vector": query_embedding,
                "k": limit * 3,  # Get more chunks to aggregate by document
                "num_candidates": 100
            },
            "_source": ["context_store_document_id", "char_start", "char_end"]
        }

        response = es.search(
            index=config.elasticsearch_index,
            body=search_body
        )

        # Aggregate results by document
        doc_sections = defaultdict(list)
        for hit in response["hits"]["hits"]:
            doc_id = hit["_source"]["context_store_document_id"]
            char_start = hit["_source"]["char_start"]
            char_end = hit["_source"]["char_end"]
            score = hit["_score"]

            doc_sections[doc_id].append({
                "score": round(score, 4),
                "offset": char_start,
                "limit": char_end - char_start,
            })

        # Sort sections within each document by score (descending)
        for doc_id in doc_sections:
            doc_sections[doc_id].sort(key=lambda x: x["score"], reverse=True)

        # Convert to list and sort by highest section score
        results = []
        for doc_id, sections in doc_sections.items():
            results.append({
                "document_id": doc_id,
                "sections": sections,
            })

        # Sort by the highest scoring section in each document
        results.sort(key=lambda x: x["sections"][0]["score"], reverse=True)

        # Limit to requested number of documents
        return results[:limit]

    except Exception as e:
        logger.warning(f"Search failed: {e}")
        return []
