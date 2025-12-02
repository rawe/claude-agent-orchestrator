import { documentApi } from './api';
import type { Document, DocumentTag, DocumentQuery } from '@/types';

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

export const documentService = {
  /**
   * Get all documents with optional filtering
   */
  async getDocuments(query?: DocumentQuery): Promise<Document[]> {
    const params = new URLSearchParams();
    if (query?.filename) params.append('filename', query.filename);
    if (query?.tags?.length) params.append('tags', query.tags.join(','));
    if (query?.limit) params.append('limit', query.limit.toString());
    if (query?.offset) params.append('offset', query.offset.toString());

    const response = await documentApi.get<Document[]>('/documents', { params });
    return response.data;
  },

  /**
   * Get a single document's metadata
   */
  async getDocumentMetadata(id: string): Promise<Document> {
    const response = await documentApi.get<Document>(`/documents/${id}/metadata`);
    return response.data;
  },

  /**
   * Get document content (download)
   */
  async getDocumentContent(id: string): Promise<Blob> {
    const response = await documentApi.get(`/documents/${id}`, {
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
    onProgress?: (progress: number) => void
  ): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);
    if (tags?.length) {
      formData.append('tags', tags.join(','));
    }
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata));
    }

    const response = await documentApi.post<Document>('/documents', formData, {
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
  async deleteDocument(id: string): Promise<void> {
    await documentApi.delete(`/documents/${id}`);
  },

  /**
   * Get all unique tags with counts
   * NOTE: This endpoint is not yet implemented in the backend
   * Will compute tags client-side for now
   */
  async getTags(): Promise<DocumentTag[]> {
    try {
      const response = await documentApi.get<{ tags: DocumentTag[] }>('/documents/tags');
      return response.data.tags;
    } catch {
      // Fallback: fetch all documents and compute tags client-side
      console.warn('Tags endpoint not implemented, computing client-side');
      const documents = await this.getDocuments();
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
    _update: { tags?: string[]; description?: string }
  ): Promise<Document> {
    // This will fail until backend implements it
    // For now, just return the existing document
    console.warn('Update document endpoint not implemented');
    return this.getDocumentMetadata(id);
  },

  /**
   * Semantic search - find documents by natural language query
   * Returns document IDs of matching documents
   */
  async semanticSearch(query: string, limit = 20): Promise<SemanticSearchResponse> {
    const params = new URLSearchParams();
    params.append('q', query);
    params.append('limit', limit.toString());

    const response = await documentApi.get<SemanticSearchResponse>('/search', { params });
    return response.data;
  },
};
