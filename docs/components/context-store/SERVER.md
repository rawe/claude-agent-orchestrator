# Context Store Server Architecture

The Context Store Server is the core FastAPI service that provides document storage, retrieval, and semantic search capabilities. It serves as the backend for document management operations used by agents and the MCP plugin.

## Overview

The server provides a RESTful API for:
- Document lifecycle management (create, read, update, delete)
- Metadata and tag-based organization
- Document relationships (hierarchical and peer links)
- Optional semantic search using vector embeddings

**Default Port**: 8766

## Architecture

```
                         ┌────────────────────────────────────┐
                         │         FastAPI Application        │
                         │                                    │
                         │  ┌────────────────────────────────┐│
                         │  │          API Layer             ││
                         │  │   (main.py - Endpoints)        ││
                         │  └────────────────────────────────┘│
                         │              │                     │
           ┌─────────────┼──────────────┼─────────────────────┤
           │             │              │                     │
           ▼             ▼              ▼                     ▼
    ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌─────────────────┐
    │ Storage  │  │ Database │  │   Models     │  │ Semantic Search │
    │  Layer   │  │  Layer   │  │   Layer      │  │    Module       │
    │          │  │          │  │              │  │   (optional)    │
    └──────────┘  └──────────┘  └──────────────┘  └─────────────────┘
         │             │                                │
         ▼             ▼                                ▼
    ┌──────────┐  ┌──────────┐                   ┌─────────────────┐
    │  Files   │  │  SQLite  │                   │  Elasticsearch  │
    │          │  │          │                   │  + Ollama       │
    └──────────┘  └──────────┘                   └─────────────────┘
```

### Internal Layers

| Layer | File | Responsibility |
|-------|------|----------------|
| **API** | `main.py` | FastAPI endpoints, request handling, response formatting |
| **Storage** | `storage.py` | File system operations, path traversal protection, checksum calculation |
| **Database** | `database.py` | SQLite metadata persistence, tag management, relation queries |
| **Models** | `models.py` | Pydantic models, relation definitions, request/response schemas |
| **Semantic** | `semantic/` | Vector embeddings, chunking, Elasticsearch integration |

## Features

### Document CRUD Operations

Standard lifecycle operations for documents:
- **Create**: Upload files or create placeholders for deferred content
- **Read**: Retrieve full or partial document content
- **Update**: Write/replace content, surgical edits
- **Delete**: Remove documents with cascade support

### Metadata and Tagging

Documents support:
- **Filename**: Original name with MIME type inference
- **Tags**: Array of strings for categorization (AND logic in queries)
- **Metadata**: Arbitrary key-value pairs (JSON)
- **Timestamps**: `created_at` and `updated_at` tracking
- **Checksum**: SHA256 hash of content

### Document Relations

Bidirectional relations between documents with three types:

| Definition | Description | Cascade Behavior |
|------------|-------------|------------------|
| `parent-child` | Hierarchical ownership | Deleting parent deletes all children |
| `related` | Peer association | Only relation removed on delete |
| `predecessor-successor` | Sequential ordering | Only relation removed on delete |

Each side of a relation can have its own note for context.

### Two-Phase Document Creation

Supports agent workflows where document IDs are needed before content is generated:

1. **Create Placeholder**: `POST /documents` with JSON body returns document ID immediately
2. **Write Content**: `PUT /documents/{id}/content` fills the placeholder

Placeholders have `size_bytes=0` and `checksum=null` until content is written.

### Surgical Editing

Two edit modes via `PATCH /documents/{id}/content`:

1. **String Replacement**: Find and replace text (follows Claude Edit semantics)
   - Must provide unique match or use `replace_all=true`
   - Returns count of replacements made

2. **Offset-Based**: Insert, replace, or delete at character position
   - Insert: `offset` + `new_string` (no length)
   - Replace: `offset` + `length` + `new_string`
   - Delete: `offset` + `length` + empty `new_string`

### Partial Content Retrieval

For text content types, retrieve document sections:
- `GET /documents/{id}?offset=2000&limit=1000`
- Returns HTTP 206 with `X-Total-Chars` and `X-Char-Range` headers

### Semantic Search (Optional)

When enabled, provides meaning-based document search:

- **Indexing**: Documents split into overlapping chunks, embedded via Ollama, stored in Elasticsearch
- **Search**: Query embedded and matched against stored vectors
- **Results**: Return matching document sections with relevance scores and character offsets

Requires `SEMANTIC_SEARCH_ENABLED=true` plus Ollama and Elasticsearch services.

## Storage Model

### File System

- **Location**: `./document-data/files/` (configurable)
- **Structure**: Flat directory with document IDs as filenames
- **Protection**: Path traversal validation on all operations

### SQLite Database

- **Location**: `./document-data/documents.db` (configurable)
- **Tables**:
  - `documents`: Core metadata (id, filename, content_type, size, checksum, timestamps)
  - `document_tags`: Tag associations with CASCADE delete
  - `document_relations`: Bidirectional relation storage

**SQLite is the source of truth** for all metadata. Elasticsearch only stores chunk embeddings for search.

### Elasticsearch (Semantic Search)

- **Index**: `context-store-vectors`
- **Document Structure**: `{ document_id, char_start, char_end, embedding }`
- **Relationship**: 1:N (one document maps to multiple chunks)

## Configuration

Key environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCUMENT_SERVER_HOST` | `0.0.0.0` | Server bind address |
| `DOCUMENT_SERVER_PORT` | `8766` | Server port |
| `DOCUMENT_SERVER_PUBLIC_URL` | `http://localhost:8766` | Base URL for document links |
| `DOCUMENT_SERVER_STORAGE` | `./document-data/files` | File storage directory |
| `DOCUMENT_SERVER_DB` | `./document-data/documents.db` | SQLite database path |
| `SEMANTIC_SEARCH_ENABLED` | `false` | Enable semantic search |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `ELASTICSEARCH_URL` | `http://localhost:9200` | Elasticsearch endpoint |

See the [main README](../../../servers/context-store/README.md) for complete configuration reference.

## Key Files

```
servers/context-store/
├── src/
│   ├── main.py           # FastAPI app, all endpoints
│   ├── models.py         # Pydantic models, relation definitions
│   ├── storage.py        # File system operations
│   ├── database.py       # SQLite operations
│   └── semantic/         # Semantic search module
│       ├── config.py     # Feature toggle, settings
│       ├── indexer.py    # Chunking, embedding, storage
│       └── search.py     # Query and retrieval
├── docs/
│   ├── architecture-semantic-search.md
│   ├── architecture-context-store-relations.md
│   └── architecture-document-write-api.md
└── README.md             # API reference documentation
```

## Related Documentation

### Architecture (this directory)
- [Context Store Overview](./README.md) - System architecture
- [CLI Architecture](./CLI.md) - CLI commands and skill integration
- [MCP Server Architecture](./MCP.md) - MCP protocol integration

### Detailed References (Server README)
- [Available Endpoints](../../../servers/context-store/README.md#available-endpoints) - Full API reference with request/response examples
- [Environment Variables](../../../servers/context-store/README.md#environment-variables) - Complete configuration reference
- [Semantic Search Setup](../../../servers/context-store/README.md#semantic-search-optional) - Ollama and Elasticsearch configuration
- [Document Relations API](../../../servers/context-store/README.md#document-relations) - Relation endpoints and examples
- [Starting the Server](../../../servers/context-store/README.md#starting-the-server) - Docker and local setup

### Deep Dive Architecture Docs
- [Semantic Search Architecture](../../../servers/context-store/docs/architecture-semantic-search.md) - Vector search implementation details
- [Relations Framework](../../../servers/context-store/docs/architecture-context-store-relations.md) - Document relations design decisions
- [Document Write API](../../../servers/context-store/docs/architecture-document-write-api.md) - Two-phase creation and editing internals
