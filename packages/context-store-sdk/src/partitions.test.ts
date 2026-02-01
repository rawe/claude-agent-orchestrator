import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { PartitionsApi } from './partitions.js';
import { TEST_BASE_URL } from './test-config.js';

describe('PartitionsApi', () => {
  const api = new PartitionsApi(TEST_BASE_URL);
  const testPartitionName = `test-partition-${Date.now()}`;

  afterAll(async () => {
    // Cleanup: try to delete the test partition
    try {
      await api.delete(testPartitionName);
    } catch {
      // Ignore if already deleted
    }
  });

  describe('create', () => {
    it('should create a partition with name only', async () => {
      const partition = await api.create(testPartitionName);

      expect(partition).toBeDefined();
      expect(partition.name).toBe(testPartitionName);
      expect(partition.createdAt).toBeDefined();
    });

    it('should create a partition with description', async () => {
      const name = `${testPartitionName}-with-desc`;
      const description = 'Test partition description';

      try {
        const partition = await api.create(name, description);

        expect(partition).toBeDefined();
        expect(partition.name).toBe(name);
        expect(partition.description).toBe(description);
      } finally {
        // Cleanup
        try {
          await api.delete(name);
        } catch {
          // Ignore
        }
      }
    });

    it('should throw error for duplicate partition name', async () => {
      await expect(api.create(testPartitionName)).rejects.toThrow();
    });
  });

  describe('list', () => {
    it('should return an array of partitions', async () => {
      const partitions = await api.list();

      expect(Array.isArray(partitions)).toBe(true);
    });

    it('should include the created test partition', async () => {
      const partitions = await api.list();
      const found = partitions.find((p) => p.name === testPartitionName);

      expect(found).toBeDefined();
      expect(found?.name).toBe(testPartitionName);
    });
  });

  describe('delete', () => {
    it('should delete a partition and return deleted document count', async () => {
      const name = `${testPartitionName}-to-delete`;
      await api.create(name);

      const result = await api.delete(name);

      expect(result).toBeDefined();
      expect(typeof result.deletedDocumentCount).toBe('number');
      expect(result.deletedDocumentCount).toBeGreaterThanOrEqual(0);
    });

    it('should throw error for non-existent partition', async () => {
      await expect(api.delete('non-existent-partition-xyz')).rejects.toThrow();
    });
  });
});
