import type { Relation, RelationDefinition, DocumentRelations } from './types.js';
import { ContextStoreError } from './errors.js';
import { buildPartitionPath, resolvePartition, toCamelCase } from './utils.js';

/**
 * API client for relation operations.
 *
 * Relations link documents together with semantic meaning (parent/child, related, predecessor/successor).
 */
export class RelationsApi {
  constructor(
    private baseUrl: string,
    private defaultPartition?: string
  ) {}

  /**
   * Get all available relation definitions.
   *
   * @param options - Options including partition
   * @returns Array of relation definitions
   */
  async getDefinitions(
    options: { partition?: string } = {}
  ): Promise<RelationDefinition[]> {
    const partition = resolvePartition(options.partition, this.defaultPartition);
    const path = buildPartitionPath('/relations/definitions', partition);

    const response = await fetch(`${this.baseUrl}${path}`, { method: 'GET' });

    if (!response.ok) {
      const text = await response.text();
      throw new ContextStoreError(`Failed to get relation definitions: ${response.status} ${text}`);
    }

    const data = await response.json();
    // Map server response to SDK types
    // Server: { name, description, from_document_is, to_document_is }
    // SDK: { name, fromType, toType }
    return data.map((def: Record<string, unknown>) => ({
      name: def.name,
      fromType: def.from_document_is,
      toType: def.to_document_is,
    }));
  }

  /**
   * List relations for a document.
   *
   * @param documentId - Document ID
   * @param options - Options including partition
   * @returns Document relations grouped by type
   */
  async list(
    documentId: string,
    options: { partition?: string } = {}
  ): Promise<DocumentRelations> {
    const partition = resolvePartition(options.partition, this.defaultPartition);
    const path = buildPartitionPath(`/documents/${encodeURIComponent(documentId)}/relations`, partition);

    const response = await fetch(`${this.baseUrl}${path}`, { method: 'GET' });

    if (!response.ok) {
      const text = await response.text();
      throw new ContextStoreError(`Failed to list document relations: ${response.status} ${text}`);
    }

    const data = await response.json();
    return toCamelCase<DocumentRelations>(data);
  }

  /**
   * Create a relation between two documents.
   *
   * @param options - Relation creation options
   * @returns The created relation (from the source document's perspective)
   */
  async create(options: {
    fromDocumentId: string;
    toDocumentId: string;
    definition: string;
    fromToNote?: string;
    toFromNote?: string;
    partition?: string;
  }): Promise<Relation> {
    const partition = resolvePartition(options.partition, this.defaultPartition);
    const path = buildPartitionPath('/relations', partition);

    const body: Record<string, unknown> = {
      from_document_id: options.fromDocumentId,
      to_document_id: options.toDocumentId,
      definition: options.definition,
    };
    if (options.fromToNote !== undefined) {
      body.from_to_note = options.fromToNote;
    }
    if (options.toFromNote !== undefined) {
      body.to_from_note = options.toFromNote;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new ContextStoreError(`Failed to create relation: ${response.status} ${text}`);
    }

    const data = await response.json();
    // Server returns { success, message, from_relation, to_relation }
    // We return the from_relation (source document's perspective)
    return toCamelCase<Relation>(data.from_relation);
  }

  /**
   * Update a relation note.
   *
   * @param id - Relation ID
   * @param note - New note text
   * @param options - Options including partition
   * @returns The updated relation
   */
  async update(
    id: string,
    note: string,
    options: { partition?: string } = {}
  ): Promise<Relation> {
    const partition = resolvePartition(options.partition, this.defaultPartition);
    const path = buildPartitionPath(`/relations/${encodeURIComponent(id)}`, partition);

    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note }),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new ContextStoreError(`Failed to update relation: ${response.status} ${text}`);
    }

    const data = await response.json();
    return toCamelCase<Relation>(data);
  }

  /**
   * Delete a relation.
   *
   * @param id - Relation ID
   * @param options - Options including partition
   */
  async delete(
    id: string,
    options: { partition?: string } = {}
  ): Promise<void> {
    const partition = resolvePartition(options.partition, this.defaultPartition);
    const path = buildPartitionPath(`/relations/${encodeURIComponent(id)}`, partition);

    const response = await fetch(`${this.baseUrl}${path}`, { method: 'DELETE' });

    if (!response.ok) {
      const text = await response.text();
      throw new ContextStoreError(`Failed to delete relation: ${response.status} ${text}`);
    }
  }
}
