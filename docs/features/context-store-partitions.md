# Context Store Partitions

**Status:** Implemented
**Affects:** Context Store Server, MCP Server, Plugin Client, Dashboard

## Overview

Partitions provide isolated document spaces within the Context Store. Each partition is completely isolated—documents in one partition are invisible to queries in another.

**Key Characteristics:**
- Single-tier partition model (one `partition` parameter per operation)
- Complete isolation between partitions (no cross-partition queries)
- Globally unique document IDs across all partitions
- Relations cannot cross partition boundaries

## Motivation

### The Problem

Without partitions, all documents share a single namespace. Different projects, sessions, or tenants could see each other's documents, creating data leakage risks and organizational confusion.

### The Solution

Partitions create isolated document spaces. Each partition has its own documents, relations, and search scope. When no partition is specified, operations use the internal `_global` partition transparently.

## Key Concepts

| Term | Definition |
|------|------------|
| **Partition** | Named isolated document space with its own documents and relations |
| **Global Partition** | Internal `_global` partition used when no partition is specified |
| **Document Isolation** | Complete separation—documents in partition A are invisible to partition B |
| **Partition Routing** | Mechanism directing requests to the correct partition based on configuration |

```
┌─────────────────────────────────────────────────────────────────┐
│                      Context Store                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Partition: "_global"              Partition: "project-alpha"   │
│  ┌────────────────────────┐        ┌────────────────────────┐   │
│  │  doc_a1b2...           │        │  doc_x9y8...           │   │
│  │  doc_c3d4...           │        │  doc_z7w6...           │   │
│  └────────────────────────┘        └────────────────────────┘   │
│                                                                  │
│  Complete isolation: No cross-partition access                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Server

The Context Store Server provides the partition API and enforces isolation.

### API

#### Partition Lifecycle

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/partitions` | POST | Create a new partition |
| `/partitions` | GET | List all partitions |
| `/partitions/{partition}` | DELETE | Delete partition and all its documents |

**Partition naming:** Alphanumeric characters and hyphens only.

**Restrictions:** The `_global` partition cannot be deleted.

#### Partitioned Endpoints

All document, relation, and search operations have partition-scoped endpoints:

| Endpoint Pattern | Purpose |
|------------------|---------|
| `/partitions/{partition}/documents` | Document CRUD |
| `/partitions/{partition}/documents/{id}/content` | Read/write document content |
| `/partitions/{partition}/documents/{id}/relations` | Document relations |
| `/partitions/{partition}/relations` | Relation management |
| `/partitions/{partition}/search` | Search within partition |

**Error:** Returns `404` if the specified partition does not exist.

#### Endpoints Without Partition Prefix

Endpoints without a partition prefix operate on the internal `_global` partition:

| Endpoint | Internal Routing |
|----------|------------------|
| `/documents` | → `/partitions/_global/documents` |
| `/relations` | → `/partitions/_global/relations` |
| `/search` | → `/partitions/_global/search` |

These endpoints provide the default document space when no partition is specified.

### Storage

Documents are stored in partition subdirectories:

```
document-data/
├── files/
│   ├── _global/
│   │   ├── doc_a1b2c3d4...
│   │   └── doc_e5f6a7b8...
│   └── project-alpha/
│       ├── doc_x9y8z7w6...
│       └── doc_m3n4o5p6...
└── documents.db
```

The database includes a `partition` column on the `documents` table with indexes for efficient partition-scoped queries.

### Semantic Search

When semantic search is enabled, the Elasticsearch index includes a `partition` field. All search queries filter by partition.

---

## Clients

Three clients connect to the Context Store Server with partition support.

### MCP Server

The MCP Server (`mcps/context-store/`) provides MCP tools for AI agents. Partition configuration is transparent to agents—they cannot see or select partitions.

#### stdio Mode

Partition set via environment variable at startup (immutable for session):

| Variable | Default | Description |
|----------|---------|-------------|
| `CONTEXT_STORE_PARTITION` | *(global)* | Partition for all operations |
| `CONTEXT_STORE_PARTITION_AUTO_CREATE` | `false` | Create partition if missing |

```bash
CONTEXT_STORE_PARTITION=my-project uv run --script context-store-mcp.py
```

#### HTTP Mode

Partition set per-request via HTTP headers:

| Header | Description |
|--------|-------------|
| `X-Context-Store-Partition` | Partition name |
| `X-Context-Store-Partition-Auto-Create` | Set to `true` to create if missing |

HTTP mode ignores environment variables—each request specifies its own partition context.

#### Auto-Create Behavior

By default, requests to a non-existent partition return HTTP 404. This protects against typos creating unintended partitions.

Enable auto-create for development workflows where partitions should be created on first use.

### Plugin Client

The Plugin Client (`plugins/context-store/`) provides Python CLI commands for document operations.

#### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DOC_SYNC_HOST` | `localhost` | Server hostname |
| `DOC_SYNC_PORT` | `8766` | Server port |
| `DOC_SYNC_PARTITION` | *(global)* | Default partition for all operations |

#### Per-Operation Override

All client methods accept an optional `partition` parameter to override the default:

```python
client = DocumentClient(config)

# Uses default partition from DOC_SYNC_PARTITION
client.query_documents()

# Overrides to specific partition
client.query_documents(partition="project-alpha")
```

### TypeScript SDK

The TypeScript SDK (`packages/context-store-sdk`) provides typed access for the Dashboard and other TypeScript applications.

#### Configuration

```typescript
import { ContextStoreClient } from '@rawe/context-store-sdk';

// Default partition (global)
const client = new ContextStoreClient({
  baseUrl: 'http://localhost:8766'
});

// With default partition
const client = new ContextStoreClient({
  baseUrl: 'http://localhost:8766',
  partition: 'my-project'
});
```

#### Per-Operation Override

All methods accept an optional `partition` parameter:

```typescript
// Uses client's default partition
await client.documents.list();

// Overrides to specific partition
await client.documents.list('project-beta');
```

See [SDK README](../../packages/context-store-sdk/README.md) for full API documentation.

---

## Dashboard Integration

The Dashboard uses the TypeScript SDK and provides partition management UI:

- **Partition Sidebar:** Lists all partitions with document counts
- **Partition Selection:** Click to view partition's documents
- **Create Partition:** Modal for creating new partitions
- **Delete Partition:** Confirmation dialog before deletion
