# Session 2 Report: Core APIs Implementation

**Date:** 2026-02-01
**Status:** Complete

## Summary

Implemented `PartitionsApi` (3 methods) and `DocumentsApi` (11 methods) per design doc Sections 3.1 and 3.3. Added comprehensive test suite with vitest that runs against the live Context Store server.

## Files Created

| File | Description |
|------|-------------|
| `packages/context-store-sdk/src/partitions.ts` | Partitions API (create, list, delete) |
| `packages/context-store-sdk/src/documents.ts` | Documents API (11 methods) |
| `packages/context-store-sdk/src/partitions.test.ts` | Tests for PartitionsApi |
| `packages/context-store-sdk/src/documents.test.ts` | Tests for DocumentsApi |
| `packages/context-store-sdk/src/test-config.ts` | Test configuration (base URL) |
| `packages/context-store-sdk/vitest.config.ts` | Vitest configuration |

## Files Modified

| File | Changes |
|------|---------|
| `packages/context-store-sdk/src/index.ts` | Added exports for `PartitionsApi`, `DocumentsApi`, `toCamelCase` |
| `packages/context-store-sdk/src/utils.ts` | Added `toCamelCase` utility for snake_case to camelCase conversion |
| `packages/context-store-sdk/package.json` | Added vitest, @types/node, test scripts |

## PartitionsApi Methods

| Method | HTTP | Description |
|--------|------|-------------|
| `create(name, description?)` | POST /partitions | Create a new partition |
| `list()` | GET /partitions | List all partitions |
| `delete(name)` | DELETE /partitions/{name} | Delete partition and its documents |

## DocumentsApi Methods

| Method | HTTP | Description |
|--------|------|-------------|
| `upload(file, options)` | POST /documents (multipart) | Upload file with content |
| `create(options)` | POST /documents (JSON) | Create empty placeholder |
| `write(id, content, options?)` | PUT /documents/{id}/content | Write/replace full content |
| `edit(id, options)` | PATCH /documents/{id}/content | Surgical edit (string or offset-based) |
| `createAndWrite(content, options)` | - | Convenience: create + write |
| `list(options?)` | GET /documents | Query/filter documents |
| `search(query, options?)` | GET /search | Semantic search |
| `getMetadata(id, options?)` | GET /documents/{id}/metadata | Get document metadata |
| `read(id, options?)` | GET /documents/{id} | Read text content |
| `download(id, options?)` | GET /documents/{id} | Download as Blob/ArrayBuffer |
| `delete(id, options?)` | DELETE /documents/{id} | Delete document |

## Implementation Details

### Partition Resolution

All DocumentsApi methods support partition override via options:
```typescript
const partition = resolvePartition(options.partition, this.defaultPartition);
const path = buildPartitionPath('/documents', partition);
```

### URL Path Building

Uses the utilities from `utils.ts`:
- No partition: `GET /documents`
- With partition: `GET /partitions/{partition}/documents`

### Response Mapping

Extracts arrays from server responses:
- `GET /partitions` → `{ partitions: [...] }` → `data.partitions`
- `GET /documents` → returns raw array directly
- `GET /search` → `{ results: [...] }` → `data.results`

### Error Handling

All methods throw `ContextStoreError` on HTTP failures with status code and response text.

---

## Testing Strategy

### Why Testing is Critical

**Testing must be part of every implementation plan.** During initial implementation, the API code was written based on the design doc assumptions. However, running tests against the live server revealed critical mismatches between the SDK and server that would have caused runtime failures for users.

### Test Infrastructure Setup

1. **Test Framework:** Added vitest as dev dependency (modern, fast, TypeScript-native)
2. **Configuration:** Created `vitest.config.ts` for test runner settings
3. **Base URL Config:** Created `test-config.ts` with configurable `CONTEXT_STORE_URL` environment variable (defaults to `http://localhost:8766`)

```typescript
// test-config.ts
export const TEST_BASE_URL = process.env.CONTEXT_STORE_URL || 'http://localhost:8766';
```

4. **Package.json Scripts:**
```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "vitest": "^2.0.0"
  }
}
```

### Running Tests

```bash
# Start the Context Store server first
./scripts/start-context-store.sh

# Run tests (default: http://localhost:8766)
npm test -w @rawe/context-store-sdk

# Custom server URL
CONTEXT_STORE_URL=http://localhost:9000 npm test -w @rawe/context-store-sdk

# Watch mode for development
npm run test:watch -w @rawe/context-store-sdk
```

### Test Coverage

| API | Tests | Notes |
|-----|-------|-------|
| PartitionsApi.create | 3 tests | Name only, with description, duplicate error |
| PartitionsApi.list | 2 tests | Returns array, includes created partition |
| PartitionsApi.delete | 2 tests | Returns count, non-existent error |
| DocumentsApi.create | 1 test | Empty placeholder |
| DocumentsApi.write | 1 test | Write content |
| DocumentsApi.createAndWrite | 1 test | Combined operation |
| DocumentsApi.read | 2 tests | Full read, partial read with offset/limit |
| DocumentsApi.edit | 2 tests | String replacement, replace all |
| DocumentsApi.list | 4 tests | Array, filter by filename, filter by tags, limit |
| DocumentsApi.getMetadata | 1 test | Metadata retrieval |
| DocumentsApi.search | 2 tests | **Skipped** - requires Elasticsearch |
| DocumentsApi.upload | 1 test | Blob upload |
| DocumentsApi.download | 2 tests | As Blob, as ArrayBuffer |
| DocumentsApi.delete | 1 test | Delete and verify |
| Partition override | 1 test | Explicit partition vs default |

**Total: 24 tests passed, 2 skipped**

---

## Snake_case to CamelCase Mapping

### The Problem: Runtime Failures

When running the initial tests, **12 out of 26 tests failed**. The failures revealed a critical mismatch:

- **Server responses:** Use Python convention (`snake_case`)
- **TypeScript SDK types:** Use JavaScript convention (`camelCase`)

Example server response:
```json
{
  "id": "doc_abc123",
  "filename": "test.txt",
  "content_type": "text/plain",
  "size_bytes": 0,
  "created_at": "2026-02-01T12:23:35.651145",
  "updated_at": "2026-02-01T12:23:35.651154"
}
```

Expected TypeScript type:
```typescript
interface Document {
  id: string;
  filename: string;
  contentType: string;   // NOT content_type
  sizeBytes: number;     // NOT size_bytes
  createdAt: string;     // NOT created_at
  updatedAt: string;     // NOT updated_at
}
```

### Discovery Process

1. **Initial test run:** 12 failures with errors like:
   - `expected undefined to be defined` (for `createdAt`)
   - `actual value must be number or bigint, received "undefined"` (for `sizeBytes`)

2. **Investigation via curl:**
```bash
curl -s http://localhost:8766/partitions
# {"partitions":[{"name":"test","description":null,"created_at":"2026-01-31T23:19:49"}]}

curl -s -X POST http://localhost:8766/partitions -d '{"name":"test"}' -H "Content-Type: application/json"
# {"name":"test","description":null,"created_at":"2026-02-01T12:23:30"}
```

3. **Root cause identified:** All server responses use `snake_case` field names

### The Solution: `toCamelCase` Utility

Added a recursive case conversion utility to `utils.ts`:

```typescript
/**
 * Convert snake_case string to camelCase.
 */
function snakeToCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

/**
 * Convert object keys from snake_case to camelCase recursively.
 * Handles nested objects and arrays.
 */
export function toCamelCase<T>(obj: unknown): T {
  if (obj === null || obj === undefined) {
    return obj as T;
  }

  if (Array.isArray(obj)) {
    return obj.map((item) => toCamelCase(item)) as T;
  }

  if (typeof obj === 'object') {
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
      const camelKey = snakeToCamel(key);
      result[camelKey] = toCamelCase(value);
    }
    return result as T;
  }

  return obj as T;
}
```

### How It's Used

Every API method that returns JSON now applies the conversion:

```typescript
// Before (broken):
async create(name: string): Promise<Partition> {
  const response = await fetch(...);
  return response.json();  // Returns {created_at: ...} - WRONG!
}

// After (fixed):
async create(name: string): Promise<Partition> {
  const response = await fetch(...);
  const data = await response.json();
  return toCamelCase<Partition>(data);  // Returns {createdAt: ...} - CORRECT!
}
```

### Fields Converted

| Server (snake_case) | SDK (camelCase) |
|---------------------|-----------------|
| `created_at` | `createdAt` |
| `updated_at` | `updatedAt` |
| `content_type` | `contentType` |
| `size_bytes` | `sizeBytes` |
| `deleted_document_count` | `deletedDocumentCount` |
| `include_relations` | `includeRelations` |
| `old_string` | `oldString` |
| `new_string` | `newString` |
| `replace_all` | `replaceAll` |

### Additional Discovery: Documents List Response

Tests also revealed that `GET /documents` returns a **raw array**, not `{documents: [...]}`:

```bash
curl -s http://localhost:8766/partitions/test/documents
# []   <-- raw array, not {documents: []}
```

Fixed in the `list()` method:
```typescript
// Before (broken):
const data = await response.json();
return data.documents;  // undefined!

// After (fixed):
const data = await response.json();
return toCamelCase<Document[]>(data);  // data IS the array
```

---

## Lessons Learned

1. **Always test against the real server** - Design docs may not capture all implementation details
2. **Case conversion is essential** - Python servers use snake_case, TypeScript uses camelCase
3. **Response structure varies** - Some endpoints wrap arrays, others return raw arrays
4. **Tests catch integration issues** - Type checking alone won't find runtime mismatches

---

## New Exports

```typescript
export { PartitionsApi } from './partitions.js';
export { DocumentsApi } from './documents.js';
export { toCamelCase } from './utils.js';
```

---

## Next Session

Session 3 should implement:
- `src/relations.ts` - `RelationsApi` implementation (Section 3.2)
- `src/client.ts` - `ContextStoreClient` class with namespace structure
- Wire up the full client to export via `index.ts`
- **Tests for RelationsApi** (must be included in the implementation plan)
