import { useState, useEffect, useCallback } from 'react';
import { useNotification } from '@/contexts';
import { documentService } from '@/services';
import type { Document, DocumentTag } from '@/types';

export function useDocuments(partition: string | null = null) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const { showError } = useNotification();

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const data = await documentService.getDocuments(undefined, partition);
      setDocuments(data);
    } catch (err) {
      showError('Failed to load documents');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [showError, partition]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const uploadDocument = useCallback(
    async (file: File, tags?: string[], onProgress?: (progress: number) => void) => {
      const newDoc = await documentService.uploadDocument(file, tags, undefined, onProgress, partition);
      setDocuments((prev) => [newDoc, ...prev]);
      return newDoc;
    },
    [partition]
  );

  const deleteDocument = useCallback(async (id: string) => {
    await documentService.deleteDocument(id, partition);
    setDocuments((prev) => prev.filter((d) => d.id !== id));
  }, [partition]);

  return {
    documents,
    loading,
    uploadDocument,
    deleteDocument,
    refetch: fetchDocuments,
  };
}

export function useTags(partition: string | null = null) {
  const [tags, setTags] = useState<DocumentTag[]>([]);
  const [loading, setLoading] = useState(true);
  const { showError } = useNotification();

  const fetchTags = useCallback(async () => {
    try {
      const data = await documentService.getTags(partition);
      setTags(data);
    } catch (err) {
      showError('Failed to load tags');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [showError, partition]);

  useEffect(() => {
    fetchTags();
  }, [fetchTags]);

  return { tags, loading, refetch: fetchTags };
}

export function useDocumentContent(documentId: string | null, partition: string | null = null) {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { showError } = useNotification();

  useEffect(() => {
    if (!documentId) {
      setContent(null);
      return;
    }

    const fetchContent = async () => {
      setLoading(true);
      try {
        const blob = await documentService.getDocumentContent(documentId, partition);
        const text = await blob.text();
        setContent(text);
      } catch (err) {
        showError('Failed to load document content');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchContent();
  }, [documentId, partition, showError]);

  return { content, loading };
}
