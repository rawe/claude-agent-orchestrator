// Client configuration
export interface ContextStoreClientConfig {
  baseUrl: string;
  partition?: string;
  partitionAutoCreate?: boolean;
}

// Document
export interface Document {
  id: string;
  filename: string;
  contentType: string;
  sizeBytes: number;
  createdAt: string;
  updatedAt: string;
  tags: string[];
  metadata: Record<string, string>;
  url: string;
  checksum?: string;
}

// Partition
export interface Partition {
  name: string;
  description?: string;
  createdAt: string;
}

// Relation
export interface Relation {
  id: string;
  documentId: string;
  relatedDocumentId: string;
  relationType: string;
  note?: string;
  createdAt: string;
  updatedAt: string;
}

// Relation definition
export interface RelationDefinition {
  name: string;
  fromType: string;
  toType: string;
}

// Document relations grouped by type
// Server uses singular keys: parent, child, related, predecessor, successor
export interface DocumentRelations {
  documentId: string;
  relations: {
    parent?: Relation[];
    child?: Relation[];
    related?: Relation[];
    predecessor?: Relation[];
    successor?: Relation[];
  };
}

// Search result - matches server response structure
export interface SearchResult {
  documentId: string;
  filename: string;
  documentUrl: string;
  sections: SearchSection[];
}

export interface SearchSection {
  score: number;
  offset: number;
  limit: number;
}
