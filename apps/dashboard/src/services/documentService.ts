import { contextStoreClient } from './contextStoreClient';
import type { Document, DocumentTag, DocumentQuery, DocumentRelationsResponse } from '@/types';

export interface SemanticSearchResult {
  documentId: string;
  filename: string;
  documentUrl: string;
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
 * Convert dashboard partition string to SDK partition (undefined for global)
 * Dashboard uses '_global' string, SDK uses undefined for global partition
 */
const toSdkPartition = (partition: string | null): string | undefined => {
  if (!partition || partition === '_global') return undefined;
  return partition;
};

export const documentService = {
  /**
   * Get all documents with optional filtering
   */
  async getDocuments(query?: DocumentQuery, partition: string | null = null): Promise<Document[]> {
    return contextStoreClient.documents.list({
      filename: query?.filename,
      tags: query?.tags,
      limit: query?.limit,
      partition: toSdkPartition(partition),
    });
  },

  /**
   * Get a single document's metadata
   */
  async getDocumentMetadata(id: string, partition: string | null = null): Promise<Document> {
    return contextStoreClient.documents.getMetadata(id, {
      partition: toSdkPartition(partition),
    });
  },

  /**
   * Get document content (download)
   */
  async getDocumentContent(id: string, partition: string | null = null): Promise<Blob> {
    const result = await contextStoreClient.documents.download(id, {
      responseType: 'blob',
      partition: toSdkPartition(partition),
    });
    return result as Blob;
  },

  /**
   * Upload a new document
   * Note: SDK uses fetch which doesn't support progress callbacks, so onProgress is ignored
   */
  async uploadDocument(
    file: File,
    tags?: string[],
    metadata?: Record<string, string>,
    _onProgress?: (progress: number) => void,
    partition: string | null = null
  ): Promise<Document> {
    return contextStoreClient.documents.upload(file, {
      filename: file.name,
      tags,
      description: metadata?.description,
      partition: toSdkPartition(partition),
    });
  },

  /**
   * Delete a document
   */
  async deleteDocument(id: string, partition: string | null = null): Promise<void> {
    await contextStoreClient.documents.delete(id, {
      partition: toSdkPartition(partition),
    });
  },

  /**
   * Get all unique tags with counts
   * NOTE: This endpoint is not yet implemented in the backend
   * Will compute tags client-side for now
   */
  async getTags(partition: string | null = null): Promise<DocumentTag[]> {
    // Fallback: fetch all documents and compute tags client-side
    // SDK doesn't have a tags endpoint
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
    const results = await contextStoreClient.documents.search(query, {
      limit,
      partition: toSdkPartition(partition),
    });

    return {
      query,
      results: results.map((r) => ({
        documentId: r.documentId,
        filename: r.filename,
        documentUrl: r.documentUrl,
        sections: r.sections,
      })),
    };
  },

  /**
   * Get document relations
   * Returns all relations for a document grouped by relation type
   */
  async getDocumentRelations(id: string, partition: string | null = null): Promise<DocumentRelationsResponse> {
    const result = await contextStoreClient.relations.list(id, {
      partition: toSdkPartition(partition),
    });

    return {
      documentId: result.documentId,
      relations: result.relations as unknown as Record<string, DocumentRelationsResponse['relations'][string]>,
    };
  },
};
