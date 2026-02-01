import type { Document, SearchResult } from './types.js';
import { ContextStoreError } from './errors.js';
import { buildPartitionPath, resolvePartition, toCamelCase } from './utils.js';

/**
 * API client for document operations.
 *
 * Provides methods for uploading, creating, reading, writing, editing,
 * searching, and deleting documents in the Context Store.
 */
export class DocumentsApi {
  constructor(
    private baseUrl: string,
    private defaultPartition?: string
  ) {}

  /**
   * Upload a file with content.
   *
   * @param file - File or Blob to upload
   * @param options - Upload options including filename, tags, description, and partition
   * @returns The created document metadata
   */
  async upload(
    file: File | Blob,
    options: {
      filename?: string;
      tags?: string[];
      description?: string;
      partition?: string;
    } = {}
  ): Promise<Document> {
    const partition = resolvePartition(options.partition, this.defaultPartition);
    const path = buildPartitionPath('/documents', partition);

    const formData = new FormData();
    const filename = options.filename || (file instanceof File ? file.name : 'file');
    formData.append('file', file, filename);

    if (options.tags && options.tags.length > 0) {
      formData.append('tags', options.tags.join(','));
    }
    if (options.description) {
      formData.append('description', options.description);
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const text = await response.text();
      throw new ContextStoreError(`Failed to upload document: ${response.status} ${text}`);
    }

    const data = await response.json();
    return toCamelCase<Document>(data);
  }

  /**
   * Create an empty document placeholder.
   *
   * @param options - Document options including required filename
   * @returns The created document metadata
   */
  async create(options: {
    filename: string;
    tags?: string[];
    description?: string;
    partition?: string;
  }): Promise<Document> {
    const partition = resolvePartition(options.partition, this.defaultPartition);
    const path = buildPartitionPath('/documents', partition);

    const body: Record<string, unknown> = { filename: options.filename };
    if (options.tags) {
      body.tags = options.tags;
    }
    if (options.description) {
      body.description = options.description;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new ContextStoreError(`Failed to create document: ${response.status} ${text}`);
    }

    const data = await response.json();
    return toCamelCase<Document>(data);
  }

  /**
   * Write or replace the full text content of a document.
   *
   * @param id - Document ID
   * @param content - Full text content to write
   * @param options - Options including partition
   * @returns Updated document metadata
   */
  async write(
    id: string,
    content: string,
    options: { partition?: string } = {}
  ): Promise<Document> {
    const partition = resolvePartition(options.partition, this.defaultPartition);
    const path = buildPartitionPath(`/documents/${encodeURIComponent(id)}/content`, partition);

    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'text/plain' },
      body: content,
    });

    if (!response.ok) {
      const text = await response.text();
      throw new ContextStoreError(`Failed to write document content: ${response.status} ${text}`);
    }

    const data = await response.json();
    return toCamelCase<Document>(data);
  }

  /**
   * Perform a surgical edit on document content.
   *
   * Supports two modes:
   * - String replacement: Replace oldString with newString
   * - Offset-based: Replace content at offset with length
   *
   * @param id - Document ID
   * @param options - Edit options
   * @returns Updated document metadata
   */
  async edit(
    id: string,
    options: {
      oldString?: string;
      newString?: string;
      replaceAll?: boolean;
      offset?: number;
      length?: number;
      partition?: string;
    }
  ): Promise<Document> {
    const partition = resolvePartition(options.partition, this.defaultPartition);
    const path = buildPartitionPath(`/documents/${encodeURIComponent(id)}/content`, partition);

    const body: Record<string, unknown> = {};
    if (options.oldString !== undefined) {
      body.old_string = options.oldString;
    }
    if (options.newString !== undefined) {
      body.new_string = options.newString;
    }
    if (options.replaceAll !== undefined) {
      body.replace_all = options.replaceAll;
    }
    if (options.offset !== undefined) {
      body.offset = options.offset;
    }
    if (options.length !== undefined) {
      body.length = options.length;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new ContextStoreError(`Failed to edit document: ${response.status} ${text}`);
    }

    const data = await response.json();
    return toCamelCase<Document>(data);
  }

  /**
   * Convenience method to create a document and write content in one call.
   *
   * @param content - Text content to write
   * @param options - Document options including required filename
   * @returns The created document metadata
   */
  async createAndWrite(
    content: string,
    options: {
      filename: string;
      tags?: string[];
      description?: string;
      partition?: string;
    }
  ): Promise<Document> {
    const doc = await this.create(options);
    return this.write(doc.id, content, { partition: options.partition });
  }

  /**
   * List and filter documents.
   *
   * @param options - Filter options
   * @returns Array of matching documents
   */
  async list(
    options: {
      filename?: string;
      tags?: string[];
      limit?: number;
      includeRelations?: boolean;
      partition?: string;
    } = {}
  ): Promise<Document[]> {
    const partition = resolvePartition(options.partition, this.defaultPartition);
    const path = buildPartitionPath('/documents', partition);

    const params = new URLSearchParams();
    if (options.filename) {
      params.append('filename', options.filename);
    }
    if (options.tags && options.tags.length > 0) {
      params.append('tags', options.tags.join(','));
    }
    if (options.limit !== undefined) {
      params.append('limit', options.limit.toString());
    }
    if (options.includeRelations) {
      params.append('include_relations', 'true');
    }

    const queryString = params.toString();
    const url = queryString ? `${this.baseUrl}${path}?${queryString}` : `${this.baseUrl}${path}`;

    const response = await fetch(url, { method: 'GET' });

    if (!response.ok) {
      const text = await response.text();
      throw new ContextStoreError(`Failed to list documents: ${response.status} ${text}`);
    }

    const data = await response.json();
    // Server returns raw array, not {documents: [...]}
    return toCamelCase<Document[]>(data);
  }

  /**
   * Search documents using semantic search.
   *
   * @param query - Search query text
   * @param options - Search options
   * @returns Array of search results with scores
   */
  async search(
    query: string,
    options: {
      limit?: number;
      includeRelations?: boolean;
      partition?: string;
    } = {}
  ): Promise<SearchResult[]> {
    const partition = resolvePartition(options.partition, this.defaultPartition);
    const path = buildPartitionPath('/search', partition);

    const params = new URLSearchParams();
    params.append('q', query);
    if (options.limit !== undefined) {
      params.append('limit', options.limit.toString());
    }
    if (options.includeRelations) {
      params.append('include_relations', 'true');
    }

    const response = await fetch(`${this.baseUrl}${path}?${params.toString()}`, {
      method: 'GET',
    });

    if (!response.ok) {
      const text = await response.text();
      throw new ContextStoreError(`Failed to search documents: ${response.status} ${text}`);
    }

    const data = await response.json();
    // Server returns {results: [...]}
    return toCamelCase<SearchResult[]>(data.results);
  }

  /**
   * Get document metadata without content.
   *
   * @param id - Document ID
   * @param options - Options including partition
   * @returns Document metadata
   */
  async getMetadata(
    id: string,
    options: { partition?: string } = {}
  ): Promise<Document> {
    const partition = resolvePartition(options.partition, this.defaultPartition);
    const path = buildPartitionPath(`/documents/${encodeURIComponent(id)}/metadata`, partition);

    const response = await fetch(`${this.baseUrl}${path}`, { method: 'GET' });

    if (!response.ok) {
      const text = await response.text();
      throw new ContextStoreError(`Failed to get document metadata: ${response.status} ${text}`);
    }

    const data = await response.json();
    return toCamelCase<Document>(data);
  }

  /**
   * Read document text content with optional partial read.
   *
   * @param id - Document ID
   * @param options - Read options including offset and limit for partial reads
   * @returns Document text content
   */
  async read(
    id: string,
    options: {
      offset?: number;
      limit?: number;
      partition?: string;
    } = {}
  ): Promise<string> {
    const partition = resolvePartition(options.partition, this.defaultPartition);
    const path = buildPartitionPath(`/documents/${encodeURIComponent(id)}`, partition);

    const params = new URLSearchParams();
    if (options.offset !== undefined) {
      params.append('offset', options.offset.toString());
    }
    if (options.limit !== undefined) {
      params.append('limit', options.limit.toString());
    }

    const queryString = params.toString();
    const url = queryString ? `${this.baseUrl}${path}?${queryString}` : `${this.baseUrl}${path}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: { Accept: 'text/plain' },
    });

    if (!response.ok) {
      const text = await response.text();
      throw new ContextStoreError(`Failed to read document: ${response.status} ${text}`);
    }

    return response.text();
  }

  /**
   * Download document as Blob or ArrayBuffer.
   *
   * @param id - Document ID
   * @param options - Download options including response type
   * @returns Document content as Blob or ArrayBuffer
   */
  async download(
    id: string,
    options: {
      responseType?: 'blob' | 'arraybuffer';
      partition?: string;
    } = {}
  ): Promise<Blob | ArrayBuffer> {
    const partition = resolvePartition(options.partition, this.defaultPartition);
    const path = buildPartitionPath(`/documents/${encodeURIComponent(id)}`, partition);

    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'GET',
      headers: { Accept: 'application/octet-stream' },
    });

    if (!response.ok) {
      const text = await response.text();
      throw new ContextStoreError(`Failed to download document: ${response.status} ${text}`);
    }

    if (options.responseType === 'arraybuffer') {
      return response.arrayBuffer();
    }
    return response.blob();
  }

  /**
   * Delete a document.
   *
   * @param id - Document ID
   * @param options - Options including partition
   */
  async delete(
    id: string,
    options: { partition?: string } = {}
  ): Promise<void> {
    const partition = resolvePartition(options.partition, this.defaultPartition);
    const path = buildPartitionPath(`/documents/${encodeURIComponent(id)}`, partition);

    const response = await fetch(`${this.baseUrl}${path}`, { method: 'DELETE' });

    if (!response.ok) {
      const text = await response.text();
      throw new ContextStoreError(`Failed to delete document: ${response.status} ${text}`);
    }
  }
}
