import { useState, useEffect, useCallback } from 'react';
import { useNotification } from '@/contexts';
import { partitionService } from '@/services/partitionService';
import type { Partition } from '@/types';

export function usePartitions() {
  const [partitions, setPartitions] = useState<Partition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { showError, showSuccess } = useNotification();

  const fetchPartitions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await partitionService.listPartitions();
      setPartitions(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load partitions';
      setError(message);
      showError(message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [showError]);

  useEffect(() => {
    fetchPartitions();
  }, [fetchPartitions]);

  const createPartition = useCallback(
    async (name: string, description?: string) => {
      const newPartition = await partitionService.createPartition(name, description);
      setPartitions((prev) => [...prev, newPartition]);
      showSuccess(`Created partition "${name}"`);
      return newPartition;
    },
    [showSuccess]
  );

  const deletePartition = useCallback(
    async (name: string) => {
      const result = await partitionService.deletePartition(name);
      setPartitions((prev) => prev.filter((p) => p.name !== name));
      showSuccess(`Deleted partition "${name}" (${result.deleted_document_count} documents removed)`);
      return result;
    },
    [showSuccess]
  );

  return {
    partitions,
    loading,
    error,
    createPartition,
    deletePartition,
    refetch: fetchPartitions,
  };
}
