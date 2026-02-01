import type { Partition } from './types.js';
import { ContextStoreError } from './errors.js';
import { toCamelCase } from './utils.js';

/**
 * API client for partition operations.
 *
 * Partitions provide isolated namespaces for documents within the Context Store.
 */
export class PartitionsApi {
  constructor(private baseUrl: string) {}

  /**
   * Create a new partition.
   *
   * @param name - Unique partition name
   * @param description - Optional description
   * @returns The created partition
   */
  async create(name: string, description?: string): Promise<Partition> {
    const body: Record<string, string> = { name };
    if (description !== undefined) {
      body.description = description;
    }

    const response = await fetch(`${this.baseUrl}/partitions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new ContextStoreError(`Failed to create partition: ${response.status} ${text}`);
    }

    const data = await response.json();
    return toCamelCase<Partition>(data);
  }

  /**
   * List all partitions.
   *
   * @returns Array of partitions
   */
  async list(): Promise<Partition[]> {
    const response = await fetch(`${this.baseUrl}/partitions`, {
      method: 'GET',
    });

    if (!response.ok) {
      const text = await response.text();
      throw new ContextStoreError(`Failed to list partitions: ${response.status} ${text}`);
    }

    const data = await response.json();
    return toCamelCase<Partition[]>(data.partitions);
  }

  /**
   * Delete a partition and all its documents.
   *
   * @param name - Partition name to delete
   * @returns Object with count of deleted documents
   */
  async delete(name: string): Promise<{ deletedDocumentCount: number }> {
    const response = await fetch(
      `${this.baseUrl}/partitions/${encodeURIComponent(name)}`,
      { method: 'DELETE' }
    );

    if (!response.ok) {
      const text = await response.text();
      throw new ContextStoreError(`Failed to delete partition: ${response.status} ${text}`);
    }

    const data = await response.json();
    return toCamelCase<{ deletedDocumentCount: number }>(data);
  }
}
