export interface Partition {
  name: string;
  description?: string;
  created_at: string;
}

export const GLOBAL_PARTITION_NAME = '_global';
