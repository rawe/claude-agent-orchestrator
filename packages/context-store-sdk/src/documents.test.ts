import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { DocumentsApi } from './documents.js';
import { PartitionsApi } from './partitions.js';
import { TEST_BASE_URL } from './test-config.js';

describe('DocumentsApi', () => {
  const partitionsApi = new PartitionsApi(TEST_BASE_URL);
  const testPartition = `test-docs-${Date.now()}`;
  let api: DocumentsApi;
  let createdDocIds: string[] = [];

  beforeAll(async () => {
    // Create test partition
    await partitionsApi.create(testPartition, 'Test partition for documents');
    api = new DocumentsApi(TEST_BASE_URL, testPartition);
  });

  afterAll(async () => {
    // Cleanup: delete test partition (will delete all documents too)
    try {
      await partitionsApi.delete(testPartition);
    } catch {
      // Ignore
    }
  });

  describe('create', () => {
    it('should create an empty document placeholder', async () => {
      const doc = await api.create({
        filename: 'test-doc.txt',
        tags: ['test', 'placeholder'],
        description: 'A test document',
      });

      expect(doc).toBeDefined();
      expect(doc.id).toBeDefined();
      expect(doc.filename).toBe('test-doc.txt');
      expect(doc.tags).toContain('test');
      createdDocIds.push(doc.id);
    });
  });

  describe('write', () => {
    it('should write content to a document', async () => {
      const doc = await api.create({ filename: 'write-test.txt' });
      createdDocIds.push(doc.id);

      const content = 'Hello, World!';
      const updated = await api.write(doc.id, content);

      expect(updated).toBeDefined();
      expect(updated.id).toBe(doc.id);
      expect(updated.sizeBytes).toBeGreaterThan(0);
    });
  });

  describe('createAndWrite', () => {
    it('should create document and write content in one call', async () => {
      const content = 'This is test content for createAndWrite';
      const doc = await api.createAndWrite(content, {
        filename: 'create-and-write.txt',
        tags: ['combined'],
      });

      expect(doc).toBeDefined();
      expect(doc.id).toBeDefined();
      expect(doc.filename).toBe('create-and-write.txt');
      expect(doc.sizeBytes).toBeGreaterThan(0);
      createdDocIds.push(doc.id);
    });
  });

  describe('read', () => {
    it('should read full document content', async () => {
      const originalContent = 'Content for reading test';
      const doc = await api.createAndWrite(originalContent, {
        filename: 'read-test.txt',
      });
      createdDocIds.push(doc.id);

      const content = await api.read(doc.id);

      expect(content).toBe(originalContent);
    });

    it('should support partial reads with offset and limit', async () => {
      const originalContent = 'ABCDEFGHIJ';
      const doc = await api.createAndWrite(originalContent, {
        filename: 'partial-read-test.txt',
      });
      createdDocIds.push(doc.id);

      const partial = await api.read(doc.id, { offset: 2, limit: 4 });

      expect(partial).toBe('CDEF');
    });
  });

  describe('edit', () => {
    it('should perform string replacement edit', async () => {
      const doc = await api.createAndWrite('Hello World', {
        filename: 'edit-test.txt',
      });
      createdDocIds.push(doc.id);

      await api.edit(doc.id, {
        oldString: 'World',
        newString: 'Universe',
      });

      const content = await api.read(doc.id);
      expect(content).toBe('Hello Universe');
    });

    it('should replace all occurrences when replaceAll is true', async () => {
      const doc = await api.createAndWrite('foo bar foo baz foo', {
        filename: 'replace-all-test.txt',
      });
      createdDocIds.push(doc.id);

      await api.edit(doc.id, {
        oldString: 'foo',
        newString: 'qux',
        replaceAll: true,
      });

      const content = await api.read(doc.id);
      expect(content).toBe('qux bar qux baz qux');
    });
  });

  describe('list', () => {
    it('should return array of documents', async () => {
      const docs = await api.list();

      expect(Array.isArray(docs)).toBe(true);
      expect(docs.length).toBeGreaterThan(0);
    });

    it('should filter by filename', async () => {
      const uniqueName = `unique-${Date.now()}.txt`;
      const doc = await api.create({ filename: uniqueName });
      createdDocIds.push(doc.id);

      const docs = await api.list({ filename: uniqueName });

      expect(docs.length).toBe(1);
      expect(docs[0].filename).toBe(uniqueName);
    });

    it('should filter by tags', async () => {
      const uniqueTag = `tag-${Date.now()}`;
      const doc = await api.create({
        filename: 'tagged-doc.txt',
        tags: [uniqueTag],
      });
      createdDocIds.push(doc.id);

      const docs = await api.list({ tags: [uniqueTag] });

      expect(docs.length).toBeGreaterThanOrEqual(1);
      expect(docs.some((d) => d.tags.includes(uniqueTag))).toBe(true);
    });

    it('should respect limit parameter', async () => {
      const docs = await api.list({ limit: 2 });

      expect(docs.length).toBeLessThanOrEqual(2);
    });
  });

  describe('getMetadata', () => {
    it('should return document metadata', async () => {
      const doc = await api.create({ filename: 'metadata-test.txt' });
      createdDocIds.push(doc.id);

      const metadata = await api.getMetadata(doc.id);

      expect(metadata).toBeDefined();
      expect(metadata.id).toBe(doc.id);
      expect(metadata.filename).toBe('metadata-test.txt');
      expect(metadata.createdAt).toBeDefined();
    });
  });

  describe('search', () => {
    // Note: These tests require semantic search to be enabled on the server
    it.skip('should return search results array', async () => {
      // Create a document with searchable content
      const doc = await api.createAndWrite(
        'The quick brown fox jumps over the lazy dog',
        { filename: 'searchable.txt' }
      );
      createdDocIds.push(doc.id);

      // Wait a bit for indexing
      await new Promise((resolve) => setTimeout(resolve, 500));

      const results = await api.search('quick fox');

      expect(Array.isArray(results)).toBe(true);
    });

    it.skip('should respect limit parameter', async () => {
      const results = await api.search('test', { limit: 1 });

      expect(results.length).toBeLessThanOrEqual(1);
    });
  });

  describe('upload', () => {
    it('should upload a blob as a document', async () => {
      const content = 'Uploaded blob content';
      const blob = new Blob([content], { type: 'text/plain' });

      const doc = await api.upload(blob, {
        filename: 'uploaded.txt',
        tags: ['upload-test'],
      });

      expect(doc).toBeDefined();
      expect(doc.id).toBeDefined();
      expect(doc.filename).toBe('uploaded.txt');
      createdDocIds.push(doc.id);
    });
  });

  describe('download', () => {
    it('should download document as blob', async () => {
      const content = 'Download test content';
      const doc = await api.createAndWrite(content, {
        filename: 'download-test.txt',
      });
      createdDocIds.push(doc.id);

      const blob = await api.download(doc.id);

      expect(blob).toBeInstanceOf(Blob);
    });

    it('should download document as arraybuffer', async () => {
      const content = 'ArrayBuffer download test';
      const doc = await api.createAndWrite(content, {
        filename: 'arraybuffer-test.txt',
      });
      createdDocIds.push(doc.id);

      const buffer = await api.download(doc.id, { responseType: 'arraybuffer' });

      expect(buffer).toBeInstanceOf(ArrayBuffer);
    });
  });

  describe('delete', () => {
    it('should delete a document', async () => {
      const doc = await api.create({ filename: 'to-delete.txt' });

      await api.delete(doc.id);

      // Verify deletion by trying to get metadata
      await expect(api.getMetadata(doc.id)).rejects.toThrow();
    });
  });

  describe('partition override', () => {
    it('should use explicit partition over default', async () => {
      // Create another partition
      const otherPartition = `other-${Date.now()}`;
      await partitionsApi.create(otherPartition);

      try {
        // Create doc in other partition explicitly
        const doc = await api.create({
          filename: 'explicit-partition.txt',
          partition: otherPartition,
        });

        // Should not appear in default partition list
        const defaultDocs = await api.list();
        const found = defaultDocs.find((d) => d.id === doc.id);
        expect(found).toBeUndefined();

        // Should appear in explicit partition list
        const otherDocs = await api.list({ partition: otherPartition });
        const foundInOther = otherDocs.find((d) => d.id === doc.id);
        expect(foundInOther).toBeDefined();
      } finally {
        await partitionsApi.delete(otherPartition);
      }
    });
  });
});
