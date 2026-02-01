import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { RelationsApi } from './relations.js';
import { DocumentsApi } from './documents.js';
import { PartitionsApi } from './partitions.js';
import { TEST_BASE_URL } from './test-config.js';

describe('RelationsApi', () => {
  const partitionsApi = new PartitionsApi(TEST_BASE_URL);
  const testPartition = `test-relations-${Date.now()}`;
  let relationsApi: RelationsApi;
  let documentsApi: DocumentsApi;
  let doc1Id: string;
  let doc2Id: string;

  beforeAll(async () => {
    // Create test partition
    await partitionsApi.create(testPartition, 'Test partition for relations');
    relationsApi = new RelationsApi(TEST_BASE_URL, testPartition);
    documentsApi = new DocumentsApi(TEST_BASE_URL, testPartition);

    // Create two test documents for relation tests
    const doc1 = await documentsApi.createAndWrite('Parent document content', {
      filename: 'parent.txt',
    });
    const doc2 = await documentsApi.createAndWrite('Child document content', {
      filename: 'child.txt',
    });
    doc1Id = doc1.id;
    doc2Id = doc2.id;
  });

  afterAll(async () => {
    // Cleanup: delete test partition (will delete all documents too)
    try {
      await partitionsApi.delete(testPartition);
    } catch {
      // Ignore
    }
  });

  describe('getDefinitions', () => {
    it('should return array of relation definitions', async () => {
      const definitions = await relationsApi.getDefinitions();

      expect(Array.isArray(definitions)).toBe(true);
      expect(definitions.length).toBeGreaterThan(0);

      // Check structure
      const def = definitions[0];
      expect(def).toHaveProperty('name');
      expect(def).toHaveProperty('fromType');
      expect(def).toHaveProperty('toType');
    });

    it('should include known definition types', async () => {
      const definitions = await relationsApi.getDefinitions();
      const names = definitions.map((d) => d.name);

      // Server provides these by default
      expect(names).toContain('parent-child');
      expect(names).toContain('related');
      expect(names).toContain('predecessor-successor');
    });
  });

  describe('list', () => {
    it('should return empty relations for new document', async () => {
      const relations = await relationsApi.list(doc1Id);

      expect(relations).toBeDefined();
      expect(relations.documentId).toBe(doc1Id);
      expect(relations.relations).toBeDefined();
      // Server returns {} when no relations, not { parent: [], child: [], ... }
      expect(relations.relations.parent).toBeUndefined();
      expect(relations.relations.child).toBeUndefined();
    });

    it('should throw for non-existent document', async () => {
      await expect(relationsApi.list('non-existent-id')).rejects.toThrow();
    });
  });

  describe('create', () => {
    it('should create a relation between two documents', async () => {
      const relation = await relationsApi.create({
        fromDocumentId: doc1Id,
        toDocumentId: doc2Id,
        definition: 'parent-child',
        fromToNote: 'parent note',
        toFromNote: 'child note',
      });

      expect(relation).toBeDefined();
      expect(relation.id).toBeDefined();
      expect(relation.documentId).toBe(doc1Id);
      expect(relation.relatedDocumentId).toBe(doc2Id);
      // From parent's perspective, the relation type is "child" (pointing to child)
      expect(relation.relationType).toBe('child');

      // Verify relation appears in list
      const relations = await relationsApi.list(doc1Id);
      expect(relations.relations.child).toBeDefined();
      expect(relations.relations.child!.length).toBe(1);
      expect(relations.relations.child![0].relatedDocumentId).toBe(doc2Id);
    });

    it('should throw for non-existent document', async () => {
      await expect(
        relationsApi.create({
          fromDocumentId: 'non-existent',
          toDocumentId: doc2Id,
          definition: 'parent-child',
        })
      ).rejects.toThrow();
    });

    it('should throw for duplicate relation', async () => {
      // First relation was created in previous test
      await expect(
        relationsApi.create({
          fromDocumentId: doc1Id,
          toDocumentId: doc2Id,
          definition: 'parent-child',
        })
      ).rejects.toThrow();
    });
  });

  describe('update', () => {
    it('should update relation note', async () => {
      // Get the relation ID from list
      const relations = await relationsApi.list(doc1Id);
      const relationId = relations.relations.child![0].id;

      const updated = await relationsApi.update(relationId, 'Updated note');

      expect(updated).toBeDefined();
      expect(updated.id).toBe(relationId);
      expect(updated.note).toBe('Updated note');
    });

    it('should throw for non-existent relation', async () => {
      await expect(relationsApi.update('999999', 'note')).rejects.toThrow();
    });
  });

  describe('delete', () => {
    it('should delete a relation', async () => {
      // Get the relation ID from list
      const relations = await relationsApi.list(doc1Id);
      const relationId = relations.relations.child![0].id;

      await relationsApi.delete(relationId);

      // Verify relation is gone
      const updatedRelations = await relationsApi.list(doc1Id);
      expect(updatedRelations.relations.child).toBeUndefined();
    });

    it('should throw for non-existent relation', async () => {
      await expect(relationsApi.delete('999999')).rejects.toThrow();
    });
  });

  describe('partition override', () => {
    it('should use explicit partition over default', async () => {
      // Create another partition
      const otherPartition = `other-rel-${Date.now()}`;
      await partitionsApi.create(otherPartition);
      const otherDocsApi = new DocumentsApi(TEST_BASE_URL, otherPartition);

      try {
        // Create documents in other partition
        const otherDoc1 = await otherDocsApi.createAndWrite('Other doc 1', {
          filename: 'other1.txt',
        });
        const otherDoc2 = await otherDocsApi.createAndWrite('Other doc 2', {
          filename: 'other2.txt',
        });

        // Create relation in other partition explicitly
        const relation = await relationsApi.create({
          fromDocumentId: otherDoc1.id,
          toDocumentId: otherDoc2.id,
          definition: 'related',
          partition: otherPartition,
        });

        expect(relation).toBeDefined();
        expect(relation.documentId).toBe(otherDoc1.id);

        // Should be visible in other partition
        const otherRelations = await relationsApi.list(otherDoc1.id, {
          partition: otherPartition,
        });
        expect(otherRelations.relations.related).toBeDefined();
        expect(otherRelations.relations.related!.length).toBe(1);
      } finally {
        await partitionsApi.delete(otherPartition);
      }
    });
  });
});
