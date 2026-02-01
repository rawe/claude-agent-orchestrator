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

export interface DocumentMetadata {
  description?: string;
  [key: string]: string | undefined;
}

export interface DocumentUpload {
  file: File;
  tags: string[];
  description?: string;
}

export interface DocumentTag {
  name: string;
  count: number;
}

export interface DocumentQuery {
  filename?: string;
  tags?: string[];
  limit?: number;
  offset?: number;
}

export interface DocumentRelation {
  id: string;
  documentId: string;
  relatedDocumentId: string;
  relationType: string;
  note: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface DocumentRelationsResponse {
  documentId: string;
  relations: Record<string, DocumentRelation[]>;
}
