# @rawe/context-store-sdk

TypeScript SDK for the Context Store API.

## Overview

The Context Store is a document management service that supports:
- **Partitions** - Isolated namespaces for organizing documents (e.g., per session, per user, per project)
- **Documents** - Text and binary files with metadata, tags, and content operations
- **Relations** - Links between documents (parent/child, related, predecessor/successor)
- **Semantic Search** - Query documents by meaning (requires Elasticsearch)

This SDK provides three API classes and a unified client:

| Class | Purpose |
|-------|---------|
| `ContextStoreClient` | Unified client wiring all APIs together |
| `PartitionsApi` | Create, list, and delete partitions |
| `DocumentsApi` | Full document lifecycle: upload, create, read, write, edit, search, delete |
| `RelationsApi` | Link documents with semantic relationships |

Typical workflow:
1. Create a partition for your context (optional - can use global namespace)
2. Create/upload documents into the partition
3. Link documents with relations as needed
4. Read, edit, or search documents
5. Clean up by deleting documents or the entire partition

> **Note:** If you specify a `partition`, it must exist before performing document or relation operations.
> Either create it first with `client.partitions.create()`, or omit the partition to use the global namespace.

## Installation

```bash
npm install @rawe/context-store-sdk
```

## Quick Start

### Using ContextStoreClient (Recommended)

```typescript
import { ContextStoreClient } from '@rawe/context-store-sdk';

const client = new ContextStoreClient({
  baseUrl: 'http://localhost:8766',
  partition: 'my-session',
});

// Create a partition (optional)
await client.partitions.create('my-session', 'Session workspace');

// Create and write content
const doc = await client.documents.createAndWrite('Hello, World!', {
  filename: 'hello.txt',
  tags: ['greeting'],
});

// Read content
const content = await client.documents.read(doc.id);

// Create related document and link them
const relatedDoc = await client.documents.createAndWrite('Related content', {
  filename: 'related.txt',
});

await client.relations.create({
  fromDocumentId: doc.id,
  toDocumentId: relatedDoc.id,
  definition: 'related',
});

// List relations
const relations = await client.relations.list(doc.id);
console.log(relations.relations.related); // [{ document: relatedDoc, ... }]

// Cleanup
await client.partitions.delete('my-session');
```

### Using Individual APIs

```typescript
import { PartitionsApi, DocumentsApi, RelationsApi } from '@rawe/context-store-sdk';

const baseUrl = 'http://localhost:8766';

// Partitions API
const partitions = new PartitionsApi(baseUrl);
await partitions.create('my-partition', 'Optional description');

// Documents API (with default partition)
const docs = new DocumentsApi(baseUrl, 'my-partition');
const doc = await docs.createAndWrite('Content', { filename: 'file.txt' });

// Relations API (with default partition)
const relations = new RelationsApi(baseUrl, 'my-partition');
const definitions = await relations.getDefinitions();
```

## API Reference

### ContextStoreClient

```typescript
const client = new ContextStoreClient({
  baseUrl: string,
  partition?: string,
});

client.partitions  // PartitionsApi instance
client.documents   // DocumentsApi instance
client.relations   // RelationsApi instance
```

### PartitionsApi

```typescript
const api = new PartitionsApi(baseUrl: string);

api.create(name: string, description?: string): Promise<Partition>
api.list(): Promise<Partition[]>
api.delete(name: string): Promise<{ deletedDocumentCount: number }>
```

### DocumentsApi

```typescript
const api = new DocumentsApi(baseUrl: string, defaultPartition?: string);

// Create documents
api.create(options: { filename, tags?, description?, partition? }): Promise<Document>
api.upload(file: File | Blob, options?: { filename?, tags?, description?, partition? }): Promise<Document>

// Read/Write content
api.write(id: string, content: string, options?: { partition? }): Promise<Document>
api.read(id: string, options?: { offset?, limit?, partition? }): Promise<string>
api.download(id: string, options?: { responseType?, partition? }): Promise<Blob | ArrayBuffer>

// Edit content
api.edit(id: string, options: { oldString?, newString?, replaceAll?, offset?, length?, partition? }): Promise<Document>

// Convenience
api.createAndWrite(content: string, options: { filename, tags?, description?, partition? }): Promise<Document>

// Query
api.list(options?: { filename?, tags?, limit?, includeRelations?, partition? }): Promise<Document[]>
api.search(query: string, options?: { limit?, includeRelations?, partition? }): Promise<SearchResult[]>
api.getMetadata(id: string, options?: { partition? }): Promise<Document>

// Delete
api.delete(id: string, options?: { partition? }): Promise<void>
```

### RelationsApi

```typescript
const api = new RelationsApi(baseUrl: string, defaultPartition?: string);

// Get available relation types
api.getDefinitions(options?: { partition? }): Promise<RelationDefinition[]>
// Returns: [{ name: 'parent-child', fromType: 'parent', toType: 'child' }, ...]

// List relations for a document
api.list(documentId: string, options?: { partition? }): Promise<DocumentRelations>
// Returns: { documentId, relations: { parent?, child?, related?, predecessor?, successor? } }

// Create a relation
api.create(options: {
  fromDocumentId: string,
  toDocumentId: string,
  definition: string,       // e.g., 'parent-child', 'related', 'predecessor-successor'
  fromToNote?: string,
  toFromNote?: string,
  partition?: string,
}): Promise<Relation>

// Update a relation note
api.update(id: string, note: string, options?: { partition? }): Promise<Relation>

// Delete a relation
api.delete(id: string, options?: { partition? }): Promise<void>
```

**Relation Definitions:**

| Definition | fromType | toType | Description |
|------------|----------|--------|-------------|
| `parent-child` | parent | child | Hierarchical relationship |
| `related` | related | related | Bidirectional association |
| `predecessor-successor` | predecessor | successor | Temporal/sequential ordering |

### Partition Override

All DocumentsApi and RelationsApi methods accept an optional `partition` parameter that overrides the default:

```typescript
const docs = new DocumentsApi(baseUrl, 'default-partition');

// Uses default partition
await docs.list();

// Overrides to use 'other-partition'
await docs.list({ partition: 'other-partition' });
```

## Types

All types are exported:

```typescript
import type {
  ContextStoreClientConfig,
  Document,
  Partition,
  Relation,
  RelationDefinition,
  DocumentRelations,
  SearchResult,
  SearchSection,
} from '@rawe/context-store-sdk';
```

## Error Handling

All API methods throw `ContextStoreError` on failure:

```typescript
import { ContextStoreError } from '@rawe/context-store-sdk';

try {
  await docs.read('non-existent-id');
} catch (error) {
  if (error instanceof ContextStoreError) {
    console.error('API error:', error.message);
  }
}
```

## Development

### Building

```bash
npm run build -w @rawe/context-store-sdk
```

### Testing

Tests run against a live Context Store server.

```bash
# 1. Start the Context Store server
./scripts/start-context-store.sh

# 2. Run tests (default: http://localhost:8766)
npm test -w @rawe/context-store-sdk

# Or with custom server URL
CONTEXT_STORE_URL=http://localhost:9000 npm test -w @rawe/context-store-sdk

# Watch mode for development
npm run test:watch -w @rawe/context-store-sdk
```

### Test Coverage

- **PartitionsApi**: create, list, delete (7 tests)
- **DocumentsApi**: create, write, read, edit, list, upload, download, delete, getMetadata (17 tests)
- **RelationsApi**: getDefinitions, list, create, update, delete (11 tests)
- **Search**: Requires Elasticsearch (2 tests, skipped by default)

### Full API Surface

The SDK exposes 19 methods across 3 API classes:

**PartitionsApi (3 methods):**
- `create`, `list`, `delete`

**DocumentsApi (11 methods):**
- `create`, `upload`, `write`, `read`, `download`, `edit`, `createAndWrite`, `list`, `search`, `getMetadata`, `delete`

**RelationsApi (5 methods):**
- `getDefinitions`, `list`, `create`, `update`, `delete`
