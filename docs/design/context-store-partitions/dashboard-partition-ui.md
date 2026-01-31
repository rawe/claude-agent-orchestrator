# Dashboard Context Store Partition UI

**Status:** Draft
**Created:** 2026-01-31
**Author:** Claude

## Overview

Enhance the dashboard's Context Store tab to display all partitions (including the global/default partition) and allow users to browse, search, and manage documents within each partition.

## Current State

### Dashboard Implementation

The Context Store tab (`apps/dashboard/src/pages/Documents.tsx`) currently:
- Shows only global partition documents
- Uses `documentService.ts` with hardcoded paths to `/documents`
- Has no awareness of partitions

### Python HTTP Client Reference

The Python client (`mcps/context-store/lib/http_client.py`) provides partition support:
- `list_partitions()` → GET `/partitions`
- `create_partition(name, description)` → POST `/partitions`
- `delete_partition(name)` → DELETE `/partitions/{name}`
- All document operations accept optional `partition` parameter
- Uses `_build_url()` to construct `/partitions/{partition}/documents/...` paths

## UI Design: Sidebar Partition List

Add a collapsible partition list on the left side of the Context Store page.

```
┌─────────────────────────────────────────────────────────────────────┐
│  Context Store                                    [Upload] [Refresh] │
├────────────────┬────────────────────────────────────────────────────┤
│ PARTITIONS     │  Semantic Search: [________________________] [🔍]  │
│ ─────────────  │  Tags: [api] [docs] [config] ...                   │
│ 🌐 Global (12) │  ──────────────────────────────────────────────────│
│ 📁 session-a (5)│  │ ID     │ Filename      │ Tags    │ Created    ││
│ 📁 project-x (8)│  ├────────┼───────────────┼─────────┼────────────┤│
│ 📁 demo (2)    │  │ doc_... │ README.md     │ docs    │ 2 hrs ago  ││
│                │  │ doc_... │ config.yaml   │ config  │ 1 day ago  ││
│ [+ New]        │  └────────┴───────────────┴─────────┴────────────┘│
└────────────────┴────────────────────────────────────────────────────┘
```

**Benefits:**
- Clear visual hierarchy
- Easy to switch between partitions
- Shows document counts per partition
- Familiar file-explorer pattern
- Collapsible sidebar to maximize content area when needed

## UI Components

### 1. PartitionSidebar

Left sidebar showing all partitions with document counts.

```tsx
interface PartitionSidebarProps {
  partitions: Partition[];
  selectedPartition: string | null;  // null = global
  onSelect: (partition: string | null) => void;
  onCreateNew: () => void;
  onDelete: (partition: string) => void;
  loading?: boolean;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}
```

Features:
- Global partition always first (🌐 icon, non-deletable)
- Other partitions sorted alphabetically
- Document count badge
- Right-click or kebab menu for delete
- "New Partition" button at bottom
- Collapsible with toggle button

### 2. CreatePartitionModal

Modal for creating new partitions.

```tsx
interface CreatePartitionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (name: string, description?: string) => void;
  existingNames: string[];  // For validation
}
```

Fields:
- **Name** (required): Slug format, validated against existing names
- **Description** (optional): Free text

## Data Types

### Partition Type

```typescript
// apps/dashboard/src/types/partition.ts

export interface Partition {
  name: string;
  description?: string;
  created_at: string;
  document_count?: number;  // Computed client-side or from API
}

// Special constant for global partition
export const GLOBAL_PARTITION = null;
export const GLOBAL_PARTITION_DISPLAY_NAME = 'Global';
```

## HTTP Client Changes

### New Partition API Methods

```typescript
// apps/dashboard/src/services/partitionService.ts

export const partitionService = {
  /**
   * List all partitions
   */
  async listPartitions(): Promise<Partition[]> {
    const response = await documentApi.get<{ partitions: Partition[] }>('/partitions');
    return response.data.partitions;
  },

  /**
   * Create a new partition
   */
  async createPartition(name: string, description?: string): Promise<Partition> {
    const response = await documentApi.post<Partition>('/partitions', {
      name,
      description,
    });
    return response.data;
  },

  /**
   * Delete a partition (and all its documents)
   */
  async deletePartition(name: string): Promise<void> {
    await documentApi.delete(`/partitions/${name}`);
  },
};
```

### Updated Document Service

Extend all methods to accept optional partition parameter.

```typescript
// apps/dashboard/src/services/documentService.ts

const buildPath = (basePath: string, partition: string | null): string => {
  if (partition === null) {
    return basePath;  // Global: /documents, /search, etc.
  }
  return `/partitions/${partition}${basePath}`;  // /partitions/{name}/documents
};

export const documentService = {
  async getDocuments(query?: DocumentQuery, partition: string | null = null): Promise<Document[]> {
    const params = new URLSearchParams();
    if (query?.filename) params.append('filename', query.filename);
    if (query?.tags?.length) params.append('tags', query.tags.join(','));
    if (query?.limit) params.append('limit', query.limit.toString());
    if (query?.offset) params.append('offset', query.offset.toString());

    const path = buildPath('/documents', partition);
    const response = await documentApi.get<Document[]>(path, { params });
    return response.data;
  },

  async getDocumentMetadata(id: string, partition: string | null = null): Promise<Document> {
    const path = buildPath(`/documents/${id}/metadata`, partition);
    const response = await documentApi.get<Document>(path);
    return response.data;
  },

  async getDocumentContent(id: string, partition: string | null = null): Promise<Blob> {
    const path = buildPath(`/documents/${id}`, partition);
    const response = await documentApi.get(path, { responseType: 'blob' });
    return response.data;
  },

  async uploadDocument(
    file: File,
    tags?: string[],
    metadata?: Record<string, string>,
    onProgress?: (progress: number) => void,
    partition: string | null = null
  ): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);
    if (tags?.length) formData.append('tags', tags.join(','));
    if (metadata) formData.append('metadata', JSON.stringify(metadata));

    const path = buildPath('/documents', partition);
    const response = await documentApi.post<Document>(path, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => e.total && onProgress?.(Math.round((e.loaded * 100) / e.total)),
    });
    return response.data;
  },

  async deleteDocument(id: string, partition: string | null = null): Promise<void> {
    const path = buildPath(`/documents/${id}`, partition);
    await documentApi.delete(path);
  },

  async semanticSearch(
    query: string,
    limit = 20,
    partition: string | null = null
  ): Promise<SemanticSearchResponse> {
    const params = new URLSearchParams();
    params.append('q', query);
    params.append('limit', limit.toString());

    const path = buildPath('/search', partition);
    const response = await documentApi.get<SemanticSearchResponse>(path, { params });
    return response.data;
  },

  async getDocumentRelations(
    id: string,
    partition: string | null = null
  ): Promise<DocumentRelationsResponse> {
    const path = buildPath(`/documents/${id}/relations`, partition);
    const response = await documentApi.get<DocumentRelationsResponse>(path);
    return response.data;
  },
};
```

## State Management

### usePartitions Hook

```typescript
// apps/dashboard/src/hooks/usePartitions.ts

interface UsePartitionsResult {
  partitions: Partition[];
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
  createPartition: (name: string, description?: string) => Promise<Partition>;
  deletePartition: (name: string) => Promise<void>;
}

export function usePartitions(): UsePartitionsResult {
  // Implementation with React Query or useState + useEffect
}
```

### Updated useDocuments Hook

Accept partition parameter.

```typescript
// apps/dashboard/src/hooks/useDocuments.ts

export function useDocuments(partition: string | null = null): UseDocumentsResult {
  // Fetch documents for specific partition
  // Refetch when partition changes
}
```

### Page-Level State

```typescript
// In Documents.tsx
const [selectedPartition, setSelectedPartition] = useState<string | null>(null);
const { documents, loading, ... } = useDocuments(selectedPartition);
const { partitions, ... } = usePartitions();
```

## UI Flow

### Viewing Partitions

1. User opens Context Store tab
2. Partitions sidebar loads (fetches from `/partitions`)
3. Global partition selected by default
4. Documents list shows global partition documents
5. User clicks another partition → documents refresh for that partition

### Creating a Partition

1. User clicks "+ New" button in sidebar
2. CreatePartitionModal opens
3. User enters name (validated: alphanumeric + hyphens, unique)
4. User optionally enters description
5. Submit → POST `/partitions` → modal closes → sidebar refreshes
6. New partition auto-selected

### Deleting a Partition

1. User right-clicks or uses kebab menu on partition
2. Confirmation modal appears (warns about document deletion)
3. Confirm → DELETE `/partitions/{name}` → sidebar refreshes
4. If deleted partition was selected, switch to global

### Uploading to Partition

Upload modal works exactly as before, but documents go to currently selected partition.

## Visual Design

### Colors & Icons

| Partition Type | Icon | Color |
|----------------|------|-------|
| Global | 🌐 Globe | Blue-500 |
| User Partition | 📁 Folder | Gray-500 |
| Selected | — | Primary highlight |

### Partition Badge

```tsx
<div className="flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer
                hover:bg-gray-100 transition-colors
                ${selected ? 'bg-primary-50 text-primary-700' : ''}">
  <Globe className="w-4 h-4" /> {/* or Folder */}
  <span className="flex-1 truncate">{name}</span>
  <Badge size="sm" variant="secondary">{count}</Badge>
</div>
```

### Empty States

**No partitions (only global):**
```
📁 Only the global partition exists.
   Create a partition to organize documents by project or session.
   [+ Create Partition]
```

**Empty partition:**
```
📄 No documents in this partition.
   Upload files or drag & drop here.
   [Upload]
```

## Implementation Plan

### Phase 1: HTTP Client & Types

1. Add `Partition` type to `types/partition.ts`
2. Create `partitionService.ts` with partition CRUD methods
3. Update `documentService.ts` to accept `partition` parameter
4. Add `buildPath()` utility for URL construction

### Phase 2: Hooks

1. Create `usePartitions` hook
2. Update `useDocuments` hook to accept partition parameter
3. Update `useTags` hook to accept partition parameter

### Phase 3: UI Components

1. Create `PartitionSidebar` component
2. Create `CreatePartitionModal` component
3. Update `Documents.tsx` page layout with sidebar

### Phase 4: Integration

1. Wire up partition selection state
2. Connect upload to current partition
3. Add delete partition confirmation
4. Add sidebar collapse toggle

### Phase 5: Polish

1. Add keyboard navigation
2. Add loading skeletons
3. Add error handling UI

## API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/partitions` | List all partitions |
| POST | `/partitions` | Create partition |
| DELETE | `/partitions/{name}` | Delete partition |
| GET | `/documents` | List global documents |
| GET | `/partitions/{name}/documents` | List partition documents |
| GET | `/search` | Search global documents |
| GET | `/partitions/{name}/search` | Search partition documents |

## Open Questions

1. **Should we show aggregate stats?** (total documents across all partitions)
2. **Cross-partition search?** (search across all partitions at once)
3. **Partition metadata editing?** (update description after creation)
4. **Partition duplication?** (copy partition with all documents)

## References

- [Context Store Partitions Design](context-store-partitions.md)
- [MCP Server Partition Support](mcp-server-partition-support.md)
- Python HTTP Client: `mcps/context-store/lib/http_client.py`
- Current Dashboard: `apps/dashboard/src/pages/Documents.tsx`
