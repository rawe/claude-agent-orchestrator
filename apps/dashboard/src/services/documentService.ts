import { documentApi } from './api';
import type { Document, DocumentTag, DocumentQuery, DocumentRelationsResponse } from '@/types';

export interface SemanticSearchResult {
  document_id: string;
  filename: string;
  document_url: string;
  sections: Array<{
    score: number;
    offset: number;
    limit: number;
  }>;
}

export interface SemanticSearchResponse {
  query: string;
  results: SemanticSearchResult[];
}

/**
 * Build path with optional partition prefix
 * Global partition (_global) uses global endpoints without /partitions prefix
 * Other partitions use /partitions/{name} prefix
 */
const buildPath = (basePath: string, partition: string | null): string => {
  if (!partition || partition === '_global') {
    return basePath;
  }
  return `/partitions/${partition}${basePath}`;
};

export const documentService = {
  /**
   * Get all documents with optional filtering
   */
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

  /**
   * Get a single document's metadata
   */
  async getDocumentMetadata(id: string, partition: string | null = null): Promise<Document> {
    const path = buildPath(`/documents/${id}/metadata`, partition);
    const response = await documentApi.get<Document>(path);
    return response.data;
  },

  /**
   * Get document content (download)
   */
  async getDocumentContent(id: string, partition: string | null = null): Promise<Blob> {
    const path = buildPath(`/documents/${id}`, partition);
    const response = await documentApi.get(path, {
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Upload a new document
   */
  async uploadDocument(
    file: File,
    tags?: string[],
    metadata?: Record<string, string>,
    onProgress?: (progress: number) => void,
    partition: string | null = null
  ): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);
    if (tags?.length) {
      formData.append('tags', tags.join(','));
    }
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata));
    }

    const path = buildPath('/documents', partition);
    const response = await documentApi.post<Document>(path, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });
    return response.data;
  },

  /**
   * Delete a document
   */
  async deleteDocument(id: string, partition: string | null = null): Promise<void> {
    const path = buildPath(`/documents/${id}`, partition);
    await documentApi.delete(path);
  },

  /**
   * Get all unique tags with counts
   * NOTE: This endpoint is not yet implemented in the backend
   * Will compute tags client-side for now
   */
  async getTags(partition: string | null = null): Promise<DocumentTag[]> {
    try {
      const path = buildPath('/documents/tags', partition);
      const response = await documentApi.get<{ tags: DocumentTag[] }>(path);
      return response.data.tags;
    } catch {
      // Fallback: fetch all documents and compute tags client-side
      console.warn('Tags endpoint not implemented, computing client-side');
      const documents = await this.getDocuments(undefined, partition);
      const tagCounts = new Map<string, number>();

      documents.forEach((doc) => {
        doc.tags.forEach((tag) => {
          tagCounts.set(tag, (tagCounts.get(tag) || 0) + 1);
        });
      });

      return Array.from(tagCounts.entries())
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count);
    }
  },

  /**
   * Update document metadata (tags/description)
   * NOTE: This endpoint is not yet implemented in the backend
   */
  async updateDocument(
    id: string,
    _update: { tags?: string[]; description?: string },
    partition: string | null = null
  ): Promise<Document> {
    // This will fail until backend implements it
    // For now, just return the existing document
    console.warn('Update document endpoint not implemented');
    return this.getDocumentMetadata(id, partition);
  },

  /**
   * Semantic search - find documents by natural language query
   * Returns document IDs of matching documents
   */
  async semanticSearch(query: string, limit = 20, partition: string | null = null): Promise<SemanticSearchResponse> {
    const params = new URLSearchParams();
    params.append('q', query);
    params.append('limit', limit.toString());

    const path = buildPath('/search', partition);
    const response = await documentApi.get<SemanticSearchResponse>(path, { params });
    return response.data;
  },

  /**
   * Get document relations
   * Returns all relations for a document grouped by relation type
   */
  async getDocumentRelations(id: string, partition: string | null = null): Promise<DocumentRelationsResponse> {
    const path = buildPath(`/documents/${id}/relations`, partition);
    const response = await documentApi.get<DocumentRelationsResponse>(path);
    return response.data;
  },
};
