import { useState, useEffect, useCallback } from 'react';
import { useNotification } from '@/contexts';
import { documentService } from '@/services';
import type { Document, DocumentTag } from '@/types';

export function useDocuments() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const { showError } = useNotification();

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const data = await documentService.getDocuments();
      setDocuments(data);
    } catch (err) {
      showError('Failed to load documents');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [showError]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const uploadDocument = useCallback(
    async (file: File, tags?: string[], onProgress?: (progress: number) => void) => {
      const newDoc = await documentService.uploadDocument(file, tags, undefined, onProgress);
      setDocuments((prev) => [newDoc, ...prev]);
      return newDoc;
    },
    []
  );

  const deleteDocument = useCallback(async (id: string) => {
    await documentService.deleteDocument(id);
    setDocuments((prev) => prev.filter((d) => d.id !== id));
  }, []);

  return {
    documents,
    loading,
    uploadDocument,
    deleteDocument,
    refetch: fetchDocuments,
  };
}

export function useTags() {
  const [tags, setTags] = useState<DocumentTag[]>([]);
  const [loading, setLoading] = useState(true);
  const { showError } = useNotification();

  useEffect(() => {
    const fetchTags = async () => {
      try {
        const data = await documentService.getTags();
        setTags(data);
      } catch (err) {
        showError('Failed to load tags');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchTags();
  }, [showError]);

  return { tags, loading };
}

export function useDocumentContent(documentId: string | null) {
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
        const blob = await documentService.getDocumentContent(documentId);
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
  }, [documentId, showError]);

  return { content, loading };
}
