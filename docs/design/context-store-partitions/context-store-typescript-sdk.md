# Context Store TypeScript SDK

**Status:** Implemented
**Date:** 2026-02-01

## 1. Overview

This document describes the design for a TypeScript SDK that provides programmatic access to the Context Store API. The SDK will be used internally by applications (like the dashboard) and can be published as an npm package.

**Goals:**
- Provide a clean, typed interface for all Context Store operations
- Abstract HTTP details and provide convenience methods
- Support partition isolation with transparent defaults
- Follow patterns established by `@rawe/agent-orchestrator-sdk`

**Non-Goals:**
- File system operations (push/pull with local paths) - browser environments don't have file system access
- MCP protocol support - that's handled by the MCP server

## 2. Configuration

### Client Initialization

```typescript
import { ContextStoreClient } from '@rawe/context-store-sdk';

const client = new ContextStoreClient({
  baseUrl: 'http://localhost:8766',
  partition?: string,              // Optional default partition
});
```

### Configuration Options

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `baseUrl` | `string` | Yes | - | Full URL to Context Store server |
| `partition` | `string` | No | `undefined` | Default partition for all operations |

### Partition Resolution

Per-call partition parameters override the client default:

```typescript
// Uses client default partition (or global if not set)
await client.documents.list();

// Overrides client default for this call only
await client.documents.list({ partition: 'other-partition' });
```

**URL Routing:**
- No partition (global): `GET /documents`
- With partition: `GET /partitions/{partition}/documents`

## 3. API Design

The SDK uses a **namespaced structure** with three domains:

```typescript
client.documents.*   // Document operations
client.relations.*   // Relation operations
client.partitions.*  // Partition operations
```

### 3.1 Documents

#### Methods

| Method | HTTP Endpoint | Description |
|--------|---------------|-------------|
| `upload(file, options)` | `POST /documents` (multipart) | Upload file with content |
| `create(options)` | `POST /documents` (JSON) | Create empty document placeholder |
| `write(id, content, options?)` | `PUT /documents/{id}/content` | Write/replace full text content |
| `edit(id, options)` | `PATCH /documents/{id}/content` | Surgical edit (find-replace or offset) |
| `createAndWrite(content, options)` | `POST` + `PUT` | Convenience: create + write in one call |
| `list(options?)` | `GET /documents` | Query/filter documents |
| `search(query, options?)` | `GET /search` | Semantic search |
| `getMetadata(id, options?)` | `GET /documents/{id}/metadata` | Get metadata without content |
| `read(id, options?)` | `GET /documents/{id}` | Read text content |
| `download(id, options?)` | `GET /documents/{id}` | Download as Blob or ArrayBuffer |
| `delete(id, options?)` | `DELETE /documents/{id}` | Delete document |

#### Method Signatures

```typescript
interface DocumentsApi {
  // Upload file with content (single step)
  upload(
    file: File | Blob,
    options: {
      filename?: string;
      tags?: string[];
      description?: string;
      partition?: string;
    }
  ): Promise<Document>;

  // Create empty document placeholder (step 1 of 2-step process)
  create(options: {
    filename: string;
    tags?: string[];
    description?: string;
    partition?: string;
  }): Promise<Document>;

  // Write/replace full text content (step 2, or standalone)
  write(
    id: string,
    content: string,
    options?: { partition?: string }
  ): Promise<Document>;

  // Surgical edit (find-replace or offset-based)
  edit(
    id: string,
    options: {
      oldString?: string;
      newString?: string;
      replaceAll?: boolean;
      offset?: number;
      length?: number;
      partition?: string;
    }
  ): Promise<Document>;

  // Convenience: create + write in one call
  createAndWrite(
    content: string,
    options: {
      filename: string;
      tags?: string[];
      description?: string;
      partition?: string;
    }
  ): Promise<Document>;

  // Query/filter documents
  list(options?: {
    filename?: string;
    tags?: string[];
    limit?: number;
    includeRelations?: boolean;
    partition?: string;
  }): Promise<Document[]>;

  // Semantic search
  search(
    query: string,
    options?: {
      limit?: number;
      includeRelations?: boolean;
      partition?: string;
    }
  ): Promise<SearchResult[]>;

  // Get metadata without content
  getMetadata(
    id: string,
    options?: { partition?: string }
  ): Promise<Document>;

  // Read text content (supports partial reads)
  read(
    id: string,
    options?: {
      offset?: number;
      limit?: number;
      partition?: string;
    }
  ): Promise<string>;

  // Download as Blob or ArrayBuffer
  download(
    id: string,
    options?: {
      responseType?: 'blob' | 'arraybuffer';
      partition?: string;
    }
  ): Promise<Blob | ArrayBuffer>;

  // Delete document
  delete(
    id: string,
    options?: { partition?: string }
  ): Promise<void>;
}
```

### 3.2 Relations

#### Methods

| Method | HTTP Endpoint | Description |
|--------|---------------|-------------|
| `getDefinitions(options?)` | `GET /relations/definitions` | List available relation types |
| `list(documentId, options?)` | `GET /documents/{id}/relations` | Get relations for a document |
| `create(options)` | `POST /relations` | Create bidirectional relation |
| `update(id, note, options?)` | `PATCH /relations/{id}` | Update relation note |
| `delete(id, options?)` | `DELETE /relations/{id}` | Delete relation |

#### Method Signatures

```typescript
interface RelationsApi {
  // List available relation types
  getDefinitions(options?: {
    partition?: string;
  }): Promise<RelationDefinition[]>;

  // Get relations for a document
  list(
    documentId: string,
    options?: { partition?: string }
  ): Promise<DocumentRelations>;

  // Create bidirectional relation
  create(options: {
    fromId: string;
    toId: string;
    definition: string;  // 'parent-child' | 'related' | 'predecessor-successor'
    fromToNote?: string;
    toFromNote?: string;
    partition?: string;
  }): Promise<Relation>;

  // Update relation note
  update(
    id: number,
    note: string,
    options?: { partition?: string }
  ): Promise<Relation>;

  // Delete relation
  delete(
    id: number,
    options?: { partition?: string }
  ): Promise<void>;
}
```

### 3.3 Partitions

#### Methods

| Method | HTTP Endpoint | Description |
|--------|---------------|-------------|
| `create(name, description?)` | `POST /partitions` | Create partition |
| `list()` | `GET /partitions` | List all partitions |
| `delete(name)` | `DELETE /partitions/{name}` | Delete partition and all documents |

#### Method Signatures

```typescript
interface PartitionsApi {
  // Create partition
  create(
    name: string,
    description?: string
  ): Promise<Partition>;

  // List all partitions
  list(): Promise<Partition[]>;

  // Delete partition and all documents
  delete(name: string): Promise<{ deletedDocumentCount: number }>;
}
```

## 4. Error Handling

The SDK uses a simple error class for all errors:

```typescript
class ContextStoreError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ContextStoreError';
  }
}
```

**Error messages** are constructed from HTTP response details:

```typescript
// Example error scenarios
throw new ContextStoreError('Document not found: doc_abc123');
throw new ContextStoreError('Partition "my-partition" does not exist');
throw new ContextStoreError('Failed to upload document: 413 Payload Too Large');
throw new ContextStoreError('Network error: Failed to fetch');
```

**Usage:**

```typescript
try {
  await client.documents.get('doc_abc123');
} catch (e) {
  if (e instanceof ContextStoreError) {
    console.error('Context Store error:', e.message);
  }
}
```

**Future expansion:** Additional error classes (e.g., `DocumentNotFoundError`, `ValidationError`) can be added when specific error handling is needed.

## 5. Type Definitions

### Core Types

```typescript
// Client configuration
interface ContextStoreClientConfig {
  baseUrl: string;
  partition?: string;
}

// Document
interface Document {
  id: string;
  filename: string;
  contentType: string;
  sizeBytes: number;
  createdAt: string;
  updatedAt: string;
  tags: string[];
  metadata: Record<string, string>;
  url: string;
  checksum?: string;
}

// Partition
interface Partition {
  name: string;
  description?: string;
  createdAt: string;
}

// Relation
interface Relation {
  id: number;
  documentId: string;
  relatedDocumentId: string;
  relationType: string;
  note?: string;
  createdAt: string;
  updatedAt: string;
}

// Relation definition
interface RelationDefinition {
  name: string;
  fromType: string;
  toType: string;
}

// Document relations grouped by type
interface DocumentRelations {
  documentId: string;
  relations: {
    parents: RelatedDocument[];
    children: RelatedDocument[];
    related: RelatedDocument[];
    predecessors: RelatedDocument[];
    successors: RelatedDocument[];
  };
}

interface RelatedDocument {
  relationId: number;
  document: Document;
  note?: string;
}

// Search result - matches server response structure
interface SearchResult {
  documentId: string;
  filename: string;
  documentUrl: string;
  sections: SearchSection[];
}

interface SearchSection {
  score: number;
  offset: number;
  limit: number;
}
```

## 6. Package Structure

```
packages/context-store-sdk/
├── src/
│   ├── index.ts           # Main exports
│   ├── client.ts          # ContextStoreClient class
│   ├── documents.ts       # DocumentsApi implementation
│   ├── relations.ts       # RelationsApi implementation
│   ├── partitions.ts      # PartitionsApi implementation
│   ├── errors.ts          # ContextStoreError class
│   ├── types.ts           # TypeScript interfaces
│   └── utils.ts           # URL building, fetch helpers
├── dist/                  # Compiled output (ESM)
├── package.json
├── tsconfig.json
└── README.md
```

### package.json

```json
{
  "name": "@rawe/context-store-sdk",
  "version": "0.1.0",
  "description": "TypeScript SDK for the Context Store API",
  "type": "module",
  "main": "./dist/index.js",
  "module": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "import": "./dist/index.js",
      "types": "./dist/index.d.ts"
    }
  },
  "files": ["dist", "README.md"],
  "scripts": {
    "build": "tsc",
    "dev": "tsc --watch",
    "clean": "rm -rf dist"
  },
  "devDependencies": {
    "typescript": "~5.6.2"
  }
}
```

### Workspace Integration

Add to root `package.json` workspaces:

```json
{
  "workspaces": [
    "packages/*",
    "apps/*"
  ]
}
```

The SDK can be used locally via workspace and published to npm when ready.

## 7. Integration Example

### Dashboard Integration

Replace direct axios calls in `apps/dashboard/src/services/documentService.ts` with SDK:

**Before (current implementation):**
```typescript
// documentService.ts
import axios from 'axios';

const documentApi = axios.create({
  baseURL: import.meta.env.VITE_DOCUMENT_SERVER_URL || 'http://localhost:8766',
});

export const documentService = {
  async listDocuments(partition?: string) {
    const path = partition ? `/partitions/${partition}/documents` : '/documents';
    const response = await documentApi.get(path);
    return response.data.documents;
  },
  // ... many more methods
};
```

**After (with SDK):**
```typescript
// documentService.ts
import { ContextStoreClient } from '@rawe/context-store-sdk';

const client = new ContextStoreClient({
  baseUrl: import.meta.env.VITE_DOCUMENT_SERVER_URL || 'http://localhost:8766',
});

export const documentService = {
  async listDocuments(partition?: string) {
    return client.documents.list({ partition });
  },

  async uploadDocument(file: File, tags: string[], partition?: string) {
    return client.documents.upload(file, { tags, partition });
  },

  async searchDocuments(query: string, partition?: string) {
    return client.documents.search(query, { partition });
  },

  async deleteDocument(id: string, partition?: string) {
    return client.documents.delete(id, { partition });
  },

  // Partitions
  async listPartitions() {
    return client.partitions.list();
  },

  async createPartition(name: string, description?: string) {
    return client.partitions.create(name, description);
  },

  // ... simplified API surface
};
```

### Verification

The dashboard app serves as the integration proof:
1. Build SDK: `npm run build -w @rawe/context-store-sdk`
2. Update dashboard to use SDK
3. Run dashboard: `./scripts/start-dashboard.sh`
4. Test all Context Store features work as before

## 8. Implementation Tasks

Ordered list for implementing the SDK:

1. **Create package structure**
   - Create `packages/context-store-sdk/` directory
   - Set up `package.json`, `tsconfig.json`
   - Add to workspace

2. **Implement core types**
   - Create `src/types.ts` with all interfaces
   - Create `src/errors.ts` with `ContextStoreError`

3. **Implement utilities**
   - Create `src/utils.ts` with URL building helpers
   - Implement partition-aware URL construction

4. **Implement PartitionsApi**
   - Create `src/partitions.ts`
   - Implement `create`, `list`, `delete`

5. **Implement DocumentsApi**
   - Create `src/documents.ts`
   - Implement all document methods
   - Include `createAndWrite` convenience method

6. **Implement RelationsApi**
   - Create `src/relations.ts`
   - Implement all relation methods

7. **Implement ContextStoreClient**
   - Create `src/client.ts`
   - Wire up namespaced APIs

8. **Create exports**
   - Create `src/index.ts`
   - Export client, types, and error

9. **Integration test with dashboard**
   - Update `documentService.ts` to use SDK
   - Verify all features work

10. **Documentation**
    - Create `README.md` with usage examples

## 9. References

### Existing Documentation

| Document | Description |
|----------|-------------|
| [context-store-partitions.md](context-store-partitions.md) | Core design for partition-based document isolation |
| [implementation-report.md](implementation-report.md) | Server and HTTP client implementation report |
| [mcp-server-partition-support.md](mcp-server-partition-support.md) | MCP server partition routing design |

### Relevant Code Files

**Context Store Server (API endpoints):**
- `servers/context-store/src/main.py` - FastAPI routes and endpoint definitions
- `servers/context-store/src/models.py` - Pydantic request/response models
- `servers/context-store/src/database.py` - Database operations

**Python HTTP Client (reference implementation):**
- `mcps/context-store/lib/http_client.py` - Async HTTP client with all operations
- `mcps/context-store/lib/config.py` - Client configuration

**MCP Implementation (tool-to-endpoint mapping):**
- `mcps/context-store/lib/tools.py` - MCP tool definitions and handlers
- `mcps/context-store/context-store-mcp.py` - MCP server entry point

**Existing TypeScript SDK (pattern reference):**
- `packages/agent-orchestrator-sdk/src/client.ts` - Client class pattern
- `packages/agent-orchestrator-sdk/src/types.ts` - TypeScript types
- `packages/agent-orchestrator-sdk/package.json` - Package configuration

**Dashboard Integration (target for SDK usage):**
- `apps/dashboard/src/services/documentService.ts` - Current direct API calls
- `apps/dashboard/src/hooks/useDocuments.ts` - React hooks using the service
- `apps/dashboard/src/types/document.ts` - Current TypeScript types
- `apps/dashboard/src/pages/Documents.tsx` - UI consuming the service

### API Endpoint Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/documents` | POST | Create document (multipart or JSON) |
| `/documents` | GET | List documents with filters |
| `/documents/{id}` | GET | Get document content |
| `/documents/{id}/metadata` | GET | Get document metadata |
| `/documents/{id}/content` | PUT | Write document content |
| `/documents/{id}/content` | PATCH | Edit document content |
| `/documents/{id}` | DELETE | Delete document |
| `/search` | GET | Semantic search |
| `/partitions` | POST | Create partition |
| `/partitions` | GET | List partitions |
| `/partitions/{name}` | DELETE | Delete partition |
| `/relations` | POST | Create relation |
| `/relations/definitions` | GET | List relation types |
| `/relations/{id}` | PATCH | Update relation |
| `/relations/{id}` | DELETE | Delete relation |
| `/documents/{id}/relations` | GET | Get document relations |

All document/relation/search endpoints also exist under `/partitions/{partition}/...` for partitioned access.
