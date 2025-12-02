# Semantic Search Architecture

High-level architecture for adding semantic retrieval to the Context Store Server.

## Existing Context Store Server

The Context Store Server is a FastAPI application that stores documents with metadata and tags. It provides:
- `POST /documents` - Upload documents
- `GET /documents` - Query/list documents
- `GET /documents/{id}` - Download document content
- `GET /documents/{id}/metadata` - Get document metadata
- `DELETE /documents/{id}` - Delete document

Storage: SQLite (metadata) + File system (content). See `servers/context-store/README.md` for details.

---

## Design Principles

- **KISS**: Keep it simple, avoid over-engineering
- **YAGNI**: Only build what's needed now
- **Feature Toggle**: Entire feature can be enabled/disabled via environment variable

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Context Store Server                             │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                         FastAPI Application                          ││
│  │                                                                      ││
│  │  ┌──────────────┐   ┌─────────────────┐   ┌───────────────────────┐ ││
│  │  │ CRUD Docs    │   │ Semantic Search │   │ Partial Read          │ ││
│  │  │ (existing)   │   │ GET /search     │   │ GET /documents/{id}   │ ││
│  │  │              │   │ (if enabled)    │   │ ?offset=X&limit=Y     │ ││
│  │  └──────────────┘   └─────────────────┘   └───────────────────────┘ ││
│  └─────────────────────────────────────────────────────────────────────┘│
│           │                     │                        │               │
│           ▼                     ▼                        ▼               │
│  ┌──────────────┐      ┌──────────────┐         ┌──────────────┐        │
│  │   SQLite     │      │ Elasticsearch │         │ File Storage │        │
│  │ (source of   │      │ (chunk index  │         │  (content)   │        │
│  │   truth)     │      │    only)      │         │              │        │
│  └──────────────┘      └──────────────┘         └──────────────┘        │
│                               ▲                                          │
│                               │                                          │
│                        ┌──────────────┐      ┌──────────────┐           │
│                        │   Indexer    │─────▶│    Ollama    │           │
│                        │  (LangChain) │      │ (embeddings) │           │
│                        └──────────────┘      └──────────────┘           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Docker Compose Services

```
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│ context-store   │   │ elasticsearch   │   │ ollama          │
│   (FastAPI)     │──▶│  (vector DB)    │   │ (external/local)│
│   port: 8766    │   │  port: 9200     │   │ port: 11434     │
└─────────────────┘   └─────────────────┘   └─────────────────┘
        │                                           ▲
        └───────────────────────────────────────────┘
                    embeddings API
```

**Note**: Ollama runs locally on the host machine (not in Docker). The context-store container connects to it via the configured base URL.

---

## Data Model & Relationships

### Source of Truth

**SQLite is the source of truth** for all document metadata. Elasticsearch is **only a chunk index** for semantic search.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              SQLite                                      │
│                         (Source of Truth)                                │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ documents table                                                    │  │
│  │ ┌─────────────────────────────────────────────────────────────┐   │  │
│  │ │ id (context_store_document_id) │ filename │ metadata │ ... │   │  │
│  │ │ doc_abc123                      │ guide.md │ {...}    │     │   │  │
│  │ │ doc_def456                      │ api.md   │ {...}    │     │   │  │
│  │ └─────────────────────────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 1:N relationship
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           Elasticsearch                                  │
│                         (Chunk Index Only)                               │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ context-store-vectors index                                        │  │
│  │ ┌─────────────────────────────────────────────────────────────┐   │  │
│  │ │ _id (auto) │ context_store_document_id │ char_start/end │...│   │  │
│  │ │ es_001     │ doc_abc123                 │ 0-1000         │   │   │  │
│  │ │ es_002     │ doc_abc123                 │ 800-1800       │   │   │  │
│  │ │ es_003     │ doc_abc123                 │ 1600-2600      │   │   │  │
│  │ │ es_004     │ doc_def456                 │ 0-1000         │   │   │  │
│  │ │ es_005     │ doc_def456                 │ 800-1800       │   │   │  │
│  │ └─────────────────────────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Relationship

| Storage | Purpose | ID Field |
|---------|---------|----------|
| SQLite | Document metadata (source of truth) | `id` = Context Store Document ID |
| Elasticsearch | Chunk embeddings (search index) | `context_store_document_id` = foreign key to SQLite |
| File Storage | Document content | Filename derived from Context Store Document ID |

**One document → Multiple chunks**: A single document in SQLite maps to N chunk entries in Elasticsearch, all sharing the same `context_store_document_id`.

---

## Feature Toggle

### Environment Variable

```bash
SEMANTIC_SEARCH_ENABLED=true|false  # default: false
```

### Behavior When Disabled (`false`)

- `GET /search` endpoint returns `404 Not Found`
- No indexing occurs on document upload/delete
- Elasticsearch connection is not established
- Ollama is not called
- Zero overhead on existing functionality

### Behavior When Enabled (`true`)

- `GET /search` endpoint is active
- Documents are indexed synchronously on upload
- Index entries are deleted on document deletion

---

## Environment Variables

| Variable | Description | Default | Required When |
|----------|-------------|---------|---------------|
| `SEMANTIC_SEARCH_ENABLED` | Enable/disable semantic search | `false` | - |
| `OLLAMA_BASE_URL` | Ollama API base URL | `http://localhost:11434` | Semantic enabled |
| `OLLAMA_EMBEDDING_MODEL` | Embedding model name | `nomic-embed-text` | Semantic enabled |
| `ELASTICSEARCH_URL` | Elasticsearch URL | `http://localhost:9200` | Semantic enabled |
| `ELASTICSEARCH_INDEX` | Index name for vectors | `context-store-vectors` | Semantic enabled |
| `CHUNK_SIZE` | Characters per chunk | `1000` | Semantic enabled |
| `CHUNK_OVERLAP` | Overlap between chunks | `200` | Semantic enabled |

---

## Dependencies

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
semantic = [
    "langchain-ollama>=1.0.0",
    "langchain-elasticsearch>=0.4.0",
]
```

This keeps semantic search dependencies optional. Install with:
```bash
uv sync --extra semantic
```

---

## Indexing Strategy: Transparent (Synchronous)

**Simplest approach**: Index documents during the upload request.

### On Document Upload (`POST /documents`)

```
1. Save file to disk (existing)
2. Save metadata to SQLite (existing)
3. IF semantic search enabled:
   a. Extract text content from document
   b. Split into chunks (fixed-size with overlap)
   c. Generate embeddings via Ollama
   d. Store in Elasticsearch with document reference
4. Return response
```

### On Document Delete (`DELETE /documents/{id}`)

```
1. Delete file from disk (existing)
2. Delete metadata from SQLite (existing)
3. IF semantic search enabled:
   a. Delete all chunks from Elasticsearch WHERE context_store_document_id = {id}
```

**Elasticsearch Deletion Query**:
```json
{
  "query": {
    "term": {
      "context_store_document_id": "doc_abc123"
    }
  }
}
```

This deletes ALL chunk entries for that document in a single operation.

### Error Handling

- If Ollama is unavailable: Log warning, continue without indexing
- If Elasticsearch is unavailable: Log warning, continue without indexing
- Document operations succeed even if indexing fails (graceful degradation)

---

## Configuration

All semantic search settings are centralized in `src/semantic/config.py`:

```python
# src/semantic/config.py
from dataclasses import dataclass
import os


@dataclass
class SemanticConfig:
    """Central configuration for semantic search."""

    # Feature toggle
    enabled: bool = False

    # Ollama settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "nomic-embed-text"

    # Elasticsearch settings
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index: str = "context-store-vectors"

    # Chunking settings (configurable here)
    chunk_size: int = 1000          # characters per chunk
    chunk_overlap: int = 200        # overlap between chunks

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


# Singleton instance
config = SemanticConfig.from_env()
```

---

## Chunking Strategy

**Simple approach**: Fixed-size chunks with overlap.

- **Default chunk size**: 1000 characters
- **Default overlap**: 200 characters
- **Configurable**: Via `SemanticConfig` in `src/semantic/config.py`

```
Document Text (5000 chars total)
├── Chunk 0: chars 0-1000
├── Chunk 1: chars 800-1800   (200 char overlap)
├── Chunk 2: chars 1600-2600
├── Chunk 3: chars 2400-3400
└── ...
```

### Elasticsearch Index Entry Structure

Each chunk stored in Elasticsearch has the following structure:

```json
{
  "_id": "auto-generated-by-elasticsearch",
  "context_store_document_id": "doc_abc123",
  "char_start": 0,
  "char_end": 1000,
  "embedding": [0.1, 0.2, ...]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `_id` | string | Auto-generated by Elasticsearch |
| `context_store_document_id` | keyword | Foreign key to SQLite document ID |
| `char_start` | integer | Starting character offset |
| `char_end` | integer | Ending character offset |
| `embedding` | dense_vector | Vector embedding (768 dimensions) |

**Elasticsearch Index Mapping**:
```json
{
  "mappings": {
    "properties": {
      "context_store_document_id": { "type": "keyword" },
      "char_start": { "type": "integer" },
      "char_end": { "type": "integer" },
      "embedding": {
        "type": "dense_vector",
        "dims": 768,
        "index": true,
        "similarity": "cosine"
      }
    }
  }
}
```

---

## API Endpoints

### New: Semantic Search

```
GET /search?q={query}&limit=10
```

**Availability**: Only when `SEMANTIC_SEARCH_ENABLED=true`

**Request Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `q` | string | Yes | - | Natural language search query |
| `limit` | int | No | 10 | Maximum documents to return |

**Response** (`200 OK`):

Results are aggregated by document. Multiple matching chunks per document are returned as separate sections.

```json
{
  "query": "search query",
  "results": [
    {
      "document_id": "doc_abc123",
      "filename": "guide.md",
      "document_url": "http://localhost:8766/documents/doc_abc123",
      "sections": [
        { "score": 0.92, "offset": 2000, "limit": 1000 },
        { "score": 0.85, "offset": 5000, "limit": 1000 }
      ]
    },
    {
      "document_id": "doc_def456",
      "filename": "reference.md",
      "document_url": "http://localhost:8766/documents/doc_def456",
      "sections": [
        { "score": 0.78, "offset": 0, "limit": 1000 }
      ]
    }
  ]
}
```

**Response when disabled** (`404 Not Found`):
```json
{
  "detail": "Semantic search is not enabled"
}
```

### Enhanced: Partial Document Read

```
GET /documents/{document_id}?offset=2000&limit=1000
```

**New Optional Parameters** (text content types only):
| Parameter | Type | Description |
|-----------|------|-------------|
| `offset` | int | Starting character position (0-indexed) |
| `limit` | int | Number of characters to return |

**Behavior**:
- If neither provided: Returns full document (current behavior)
- If provided for `text/*` content types: Returns partial content
- If provided for binary content types: Returns `400 Bad Request`

**Response Headers for Partial Content** (`206 Partial Content`):
```
Content-Type: text/markdown
X-Total-Chars: 5000
X-Char-Range: 2000-3000
```

---

## Terminology: Internal vs API

| Context | Terms | Usage |
|---------|-------|-------|
| **Elasticsearch (internal)** | `char_start`, `char_end` | Absolute character positions stored in index |
| **API (external)** | `offset`, `limit` | Client-facing interface for retrieval |

**Translation** (done by server):
- `offset` = `char_start`
- `limit` = `char_end - char_start`

The client never sees `char_start`/`char_end`. The search endpoint returns `offset`/`limit` directly.

---

## Workflow: Search and Retrieve

```
┌────────┐                       ┌────────────────┐
│ Client │                       │ Context Store  │
└───┬────┘                       └───────┬────────┘
    │                                    │
    │ 1. GET /search?q=...               │
    │───────────────────────────────────▶│
    │                                    │
    │ 2. Response with offset/limit      │
    │◀───────────────────────────────────│
    │   {                                │
    │     "results": [{                  │
    │       "document_id": "doc_123",    │
    │       "sections": [                │
    │         { "offset": 2000,          │
    │           "limit": 1000 }          │
    │       ]                            │
    │     }]                             │
    │   }                                │
    │                                    │
    │ 3. GET /documents/doc_123          │
    │    ?offset=2000&limit=1000         │
    │───────────────────────────────────▶│
    │                                    │
    │ 4. Partial document content        │
    │◀───────────────────────────────────│
    │                                    │
```

---

## Docker Compose Changes

Add Elasticsearch service:

```yaml
services:
  context-store:
    # ... existing config ...
    environment:
      - SEMANTIC_SEARCH_ENABLED=${SEMANTIC_SEARCH_ENABLED:-false}
      - OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-http://host.docker.internal:11434}
      - OLLAMA_EMBEDDING_MODEL=${OLLAMA_EMBEDDING_MODEL:-nomic-embed-text}
      - ELASTICSEARCH_URL=http://elasticsearch:9200
    depends_on:
      elasticsearch:
        condition: service_healthy

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9200/_cluster/health"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  es_data:
```

**Note**: `host.docker.internal` allows the container to reach Ollama running on the host machine.

---

## File Structure

```
servers/context-store/
├── src/
│   ├── main.py              # Add /search endpoint, feature toggle
│   ├── models.py            # Add SearchResult, SectionInfo models
│   ├── storage.py           # (unchanged)
│   ├── database.py          # (unchanged)
│   └── semantic/            # New module (only loaded if enabled)
│       ├── __init__.py
│       ├── config.py        # Central configuration (chunk size, URLs, etc.)
│       ├── indexer.py       # Chunking + embedding + ES storage
│       └── search.py        # Query embedding + ES search
├── pyproject.toml           # Add optional semantic dependencies
└── ...
```

---

## Implementation Phases

### Phase 1: Foundation
- Add feature toggle and environment variables
- Add Elasticsearch to Docker Compose
- Create semantic module structure

### Phase 2: Indexing
- Implement chunking logic
- Integrate LangChain + Ollama for embeddings
- Integrate LangChain + Elasticsearch for storage
- Hook into document upload/delete

### Phase 3: Search
- Implement `/search` endpoint
- Query embedding and similarity search

### Phase 4: Partial Read
- Add `offset` and `limit` parameters to document read endpoint
- Return partial content with appropriate headers

---

## References

- [LangChain Ollama Embeddings](https://python.langchain.com/docs/integrations/text_embedding/ollama/)
- [LangChain Elasticsearch Vector Store](https://python.langchain.com/docs/integrations/vectorstores/elasticsearch/)
- [langchain-ollama on PyPI](https://pypi.org/project/langchain-ollama/) (v1.0.0)
- [langchain-elasticsearch on PyPI](https://pypi.org/project/langchain-elasticsearch/) (v0.4.0)

---

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Embedding Model | `nomic-embed-text` | Good general purpose, 768 dimensions |
| Chunk Size | 1000 chars | Balance between context and precision |
| Chunk Overlap | 200 chars | Ensures continuity across chunk boundaries |
| Configuration | Centralized in `config.py` | Single place to adjust all settings |
