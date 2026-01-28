export interface Document {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
  updated_at: string;
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
  document_id: string;
  related_document_id: string;
  relation_type: string;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentRelationsResponse {
  document_id: string;
  relations: Record<string, DocumentRelation[]>;
}
