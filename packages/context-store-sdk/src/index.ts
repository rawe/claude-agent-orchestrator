// Client
export { ContextStoreClient } from './client.js';

// API Classes
export { PartitionsApi } from './partitions.js';
export { DocumentsApi } from './documents.js';
export { RelationsApi } from './relations.js';

// Types
export type {
  ContextStoreClientConfig,
  Document,
  Partition,
  Relation,
  RelationDefinition,
  DocumentRelations,
  SearchResult,
  SearchSection,
} from './types.js';

// Errors
export { ContextStoreError } from './errors.js';

// Utilities
export { buildPartitionPath, resolvePartition, toCamelCase } from './utils.js';
