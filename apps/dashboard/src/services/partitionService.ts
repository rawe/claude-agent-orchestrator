import { documentApi } from './api';
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
  deleted_document_count: number;
}

export const partitionService = {
  /**
   * List all partitions
   */
  async listPartitions(): Promise<Partition[]> {
    const response = await documentApi.get<PartitionListResponse>('/partitions');
    return response.data.partitions;
  },

  /**
   * Create a new partition
   */
  async createPartition(name: string, description?: string): Promise<Partition> {
    const payload: CreatePartitionRequest = { name };
    if (description) {
      payload.description = description;
    }
    const response = await documentApi.post<Partition>('/partitions', payload);
    return response.data;
  },

  /**
   * Delete a partition and all its documents
   */
  async deletePartition(name: string): Promise<DeletePartitionResponse> {
    const response = await documentApi.delete<DeletePartitionResponse>(`/partitions/${name}`);
    return response.data;
  },
};
