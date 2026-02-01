import type { ContextStoreClientConfig } from './types.js';
import { PartitionsApi } from './partitions.js';
import { DocumentsApi } from './documents.js';
import { RelationsApi } from './relations.js';

/**
 * Context Store client providing access to all API surfaces.
 *
 * The client exposes three API namespaces:
 * - `partitions` - Create, list, and delete partitions
 * - `documents` - Full document lifecycle operations
 * - `relations` - Link documents with semantic relationships
 *
 * @example
 * ```typescript
 * const client = new ContextStoreClient({
 *   baseUrl: 'http://localhost:8766',
 *   partition: 'my-session',
 * });
 *
 * // Create a document
 * const doc = await client.documents.createAndWrite('Hello!', {
 *   filename: 'greeting.txt',
 * });
 *
 * // Read it back
 * const content = await client.documents.read(doc.id);
 * ```
 */
export class ContextStoreClient {
  /**
   * Partition management API.
   */
  readonly partitions: PartitionsApi;

  /**
   * Document operations API.
   */
  readonly documents: DocumentsApi;

  /**
   * Relation management API.
   */
  readonly relations: RelationsApi;

  /**
   * Create a new Context Store client.
   *
   * @param config - Client configuration
   * @param config.baseUrl - Base URL of the Context Store server
   * @param config.partition - Default partition for document and relation operations
   */
  constructor(config: ContextStoreClientConfig) {
    this.partitions = new PartitionsApi(config.baseUrl);
    this.documents = new DocumentsApi(config.baseUrl, config.partition);
    this.relations = new RelationsApi(config.baseUrl, config.partition);
  }
}
