import { contextStoreClient } from './contextStoreClient';
import type { Partition } from '@/types';

export interface PartitionListResponse {
  partitions: Partition[];
}

export interface CreatePartitionRequest {
  name: string;
  description?: string;
}

export interface DeletePartitionResponse {
  success: boolean;
  message: string;
  deletedDocumentCount: number;
}

export const partitionService = {
  /**
   * List all partitions
   */
  async listPartitions(): Promise<Partition[]> {
    return contextStoreClient.partitions.list();
  },

  /**
   * Create a new partition
   */
  async createPartition(name: string, description?: string): Promise<Partition> {
    return contextStoreClient.partitions.create(name, description);
  },

  /**
   * Delete a partition and all its documents
   */
  async deletePartition(name: string): Promise<DeletePartitionResponse> {
    const result = await contextStoreClient.partitions.delete(name);
    return {
      success: true,
      message: `Deleted partition "${name}"`,
      deletedDocumentCount: result.deletedDocumentCount,
    };
  },
};
