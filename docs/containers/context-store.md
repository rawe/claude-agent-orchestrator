# AOF Context Store

The Context Store is a document management and synchronization server for the Agent Orchestration Framework. It provides document storage, tagging, relations, and optional semantic search capabilities.

## Image

```
ghcr.io/rawe/aof-context-store:<version>
```

## Quick Start

```bash
docker run -d \
  --name aof-context-store \
  -p 8766:8766 \
  -e CORS_ORIGINS=* \
  -v context-store-data:/app/document-data \
  ghcr.io/rawe/aof-context-store:<version>
```

## Environment Variables

### Core Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DOCUMENT_SERVER_HOST` | No | `0.0.0.0` | Host to bind the server |
| `DOCUMENT_SERVER_PORT` | No | `8766` | Port to listen on |
| `DOCUMENT_SERVER_STORAGE` | No | `./document-data/files` | Directory for file storage |
| `DOCUMENT_SERVER_DB` | No | `./document-data/documents.db` | Path to SQLite database |
| `DOCUMENT_SERVER_PUBLIC_URL` | No | `http://localhost:8766` | Public URL for document links (important for Docker/proxy setups) |
| `CORS_ORIGINS` | No | `http://localhost:5173,http://localhost:3000` | Allowed CORS origins (comma-separated) |

### MCP Server (Optional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MCP_ENABLED` | No | `false` | Enable MCP HTTP server |
| `MCP_HTTP_HOST` | No | `0.0.0.0` | MCP server bind host |
| `MCP_HTTP_PORT` | No | `9501` | MCP server port |

### Semantic Search (Optional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SEMANTIC_SEARCH_ENABLED` | No | `false` | Enable semantic search feature |
| `OLLAMA_BASE_URL` | If semantic enabled | `http://localhost:11434` | Ollama service URL |
| `OLLAMA_EMBEDDING_MODEL` | No | `nomic-embed-text` | Embedding model to use |
| `ELASTICSEARCH_URL` | If semantic enabled | `http://localhost:9200` | Elasticsearch URL |
| `ELASTICSEARCH_INDEX` | No | `context-store-vectors` | Elasticsearch index name |
| `CHUNK_SIZE` | No | `1000` | Characters per chunk for indexing |
| `CHUNK_OVERLAP` | No | `200` | Overlap between chunks |

## Ports

| Port | Protocol | Description |
|------|----------|-------------|
| 8766 | HTTP | Context Store REST API |
| 9501 | HTTP | MCP HTTP server (when `MCP_ENABLED=true`) |

## Volumes

| Path | Description |
|------|-------------|
| `/app/document-data` | Document storage directory containing files and SQLite database |

### Volume Structure

```
/app/document-data/
├── files/           # Stored document files
│   ├── doc_abc123
│   └── doc_def456
└── documents.db     # SQLite metadata database
```

## API Endpoints

### Documents

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/documents` | GET | List documents (with filtering) |
| `/documents` | POST | Create document (file upload or placeholder) |
| `/documents/{id}` | GET | Download document (supports partial content) |
| `/documents/{id}/metadata` | GET | Get document metadata only |
| `/documents/{id}/content` | PUT | Replace document content |
| `/documents/{id}/content` | PATCH | Edit document content (surgical updates) |
| `/documents/{id}` | DELETE | Delete document (cascades to children) |

### Relations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/relations/definitions` | GET | List available relation types |
| `/relations` | POST | Create bidirectional relation |
| `/documents/{id}/relations` | GET | Get relations for a document |
| `/relations/{id}` | PATCH | Update relation note |
| `/relations/{id}` | DELETE | Delete relation (both directions) |

### Search

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/search?q=query` | GET | Semantic search (requires `SEMANTIC_SEARCH_ENABLED=true`) |

## Health Check

The container includes a built-in health check that queries the `/health` endpoint:

```bash
# Check health manually
curl http://localhost:8766/health
```

## Example: Basic Setup

```bash
docker run -d \
  --name aof-context-store \
  -p 8766:8766 \
  -e CORS_ORIGINS=* \
  -v context-store-data:/app/document-data \
  ghcr.io/rawe/aof-context-store:<version>
```

## Example: With Semantic Search

Semantic search requires Ollama running locally and Elasticsearch:

```bash
docker run -d \
  --name aof-context-store \
  -p 8766:8766 \
  -e CORS_ORIGINS=* \
  -e SEMANTIC_SEARCH_ENABLED=true \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  -e ELASTICSEARCH_URL=http://elasticsearch:9200 \
  -v context-store-data:/app/document-data \
  ghcr.io/rawe/aof-context-store:<version>
```

**Important:** See [Semantic Search Setup](#semantic-search-setup) for Ollama requirements.

## Example: Production Setup

```bash
docker run -d \
  --name aof-context-store \
  -p 8766:8766 \
  -e CORS_ORIGINS=https://your-dashboard.example.com \
  -e DOCUMENT_SERVER_PUBLIC_URL=https://api.example.com:8766 \
  -v /var/lib/aof/context-store:/app/document-data \
  ghcr.io/rawe/aof-context-store:<version>
```

## Docker Compose

### Basic

```yaml
services:
  context-store:
    image: ghcr.io/rawe/aof-context-store:<version>
    ports:
      - "8766:8766"
    environment:
      CORS_ORIGINS: "*"
    volumes:
      - context-store-data:/app/document-data
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8766/health')"]
      interval: 30s
      timeout: 3s
      retries: 3

volumes:
  context-store-data:
```

### With Semantic Search

```yaml
services:
  context-store:
    image: ghcr.io/rawe/aof-context-store:<version>
    ports:
      - "8766:8766"
    environment:
      CORS_ORIGINS: "*"
      SEMANTIC_SEARCH_ENABLED: "true"
      OLLAMA_BASE_URL: http://host.docker.internal:11434  # Ollama runs locally
      ELASTICSEARCH_URL: http://elasticsearch:9200
    volumes:
      - context-store-data:/app/document-data
    depends_on:
      - elasticsearch

  elasticsearch:
    image: elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - es-data:/usr/share/elasticsearch/data

volumes:
  context-store-data:
  es-data:
```

**Important:** Ollama must run locally on your host machine. See [Semantic Search Setup](#semantic-search-setup).

## Semantic Search Setup

Semantic search is an **optional feature** that enables natural language queries across documents. It requires two external dependencies: **Ollama** (for embeddings) and **Elasticsearch** (for vector storage).

### Why Ollama Must Run Locally

Ollama should run directly on your host machine (not in a container) because:

1. **GPU Access** - Ollama benefits significantly from GPU acceleration for generating embeddings
2. **Model Management** - Models are large and need to be pulled/managed locally
3. **Performance** - Direct hardware access provides better performance than containerized execution

### Required Embedding Model

The Context Store uses the **`nomic-embed-text`** model for generating embeddings. This model must be pulled before enabling semantic search.

```bash
# Install Ollama (if not already installed)
# macOS
brew install ollama

# Or download from https://ollama.ai

# Start Ollama service
ollama serve

# Pull the required embedding model
ollama pull nomic-embed-text
```

Verify the model is available:

```bash
ollama list
# Should show: nomic-embed-text
```

### Configuring OLLAMA_BASE_URL

The `OLLAMA_BASE_URL` configuration depends on how you run the Context Store:

| Context Store Runs | OLLAMA_BASE_URL |
|--------------------|-----------------|
| Locally (not in Docker) | `http://localhost:11434` (default) |
| In Docker container | `http://host.docker.internal:11434` |
| In Docker on Linux | `http://172.17.0.1:11434` (Docker bridge IP) |

**Docker Desktop (macOS/Windows):** Use `host.docker.internal` to reach services on the host.

**Docker on Linux:** The `host.docker.internal` hostname may not work by default. Use the Docker bridge gateway IP (`172.17.0.1`) or add `--add-host=host.docker.internal:host-gateway` to your docker run command.

### Elasticsearch

Elasticsearch can run in a container since it doesn't require special hardware access. See the [Docker Compose with Semantic Search](#with-semantic-search) example above.

### Complete Setup Checklist

1. Install and start Ollama locally
2. Pull the embedding model: `ollama pull nomic-embed-text`
3. Start Elasticsearch (container is fine)
4. Set `SEMANTIC_SEARCH_ENABLED=true`
5. Configure `OLLAMA_BASE_URL` based on your setup (see table above)
6. Configure `ELASTICSEARCH_URL` (default: `http://localhost:9200`)

## Features

### Document Storage
- Upload files via multipart form or create placeholders
- Automatic MIME type detection
- SHA256 checksums for integrity
- Partial content retrieval for text files

### Document Editing
- Full content replacement (PUT)
- Surgical edits via string replacement or offset-based (PATCH)
- Follows Claude Edit tool semantics

### Tagging
- Add tags during upload or via metadata
- Filter documents by tags
- Tag-based organization

### Relations
- Bidirectional relations between documents
- Built-in types: parent-child, related, predecessor-successor
- Cascade delete for parent-child hierarchies
- Notes on relation edges

### Semantic Search (Optional)
- Natural language queries
- Vector embeddings via Ollama
- Elasticsearch for vector storage
- Returns matching document sections with character offsets

## MCP Server

The container includes an optional **MCP (Model Context Protocol) HTTP server** that exposes document management tools to MCP clients like Claude Desktop or Claude Code.

### Enabling MCP Server

Set `MCP_ENABLED=true` to start the MCP server alongside the Context Store API:

```bash
docker run -d \
  --name aof-context-store \
  -p 8766:8766 \
  -p 9501:9501 \
  -e CORS_ORIGINS=* \
  -e MCP_ENABLED=true \
  -v context-store-data:/app/document-data \
  ghcr.io/rawe/aof-context-store:<version>
```

### MCP Endpoint

When enabled, the MCP server is available at:

```
http://localhost:9501/mcp
```

### MCP Tools Available

The MCP server provides these tools to MCP clients:

| Tool | Description |
|------|-------------|
| `doc_create` | Create placeholder document (returns ID) |
| `doc_write` | Write/replace document content |
| `doc_edit` | Surgically edit document content |
| `doc_push` | Upload file from filesystem |
| `doc_read` | Read document content |
| `doc_pull` | Download document to filesystem |
| `doc_query` | Query by filename pattern and/or tags |
| `doc_search` | Semantic search by natural language |
| `doc_info` | Get metadata and relations |
| `doc_link` | Manage document relations |
| `doc_delete` | Delete a document |

### Configuring MCP Clients

**Claude Desktop (HTTP mode):**

```json
{
  "mcpServers": {
    "context-store": {
      "type": "http",
      "url": "http://localhost:9501/mcp"
    }
  }
}
```

### Docker Compose with MCP

```yaml
services:
  context-store:
    image: ghcr.io/rawe/aof-context-store:<version>
    ports:
      - "8766:8766"
      - "9501:9501"
    environment:
      CORS_ORIGINS: "*"
      MCP_ENABLED: "true"
    volumes:
      - context-store-data:/app/document-data

volumes:
  context-store-data:
```
