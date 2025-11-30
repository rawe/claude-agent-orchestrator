import { useState } from 'react';
import { useDocuments, useTags } from '@/hooks/useDocuments';
import { DocumentTable, DocumentPreview, UploadModal } from '@/components/features/documents';
import { Button, Badge, ConfirmModal } from '@/components/common';
import { useNotification } from '@/contexts';
import { Document } from '@/types';
import { Upload, X } from 'lucide-react';

export function Documents() {
  const { documents, loading, uploadDocument, deleteDocument, refetch } = useDocuments();
  const { tags } = useTags();
  const { showSuccess, showError } = useNotification();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; documentId: string | null }>({
    isOpen: false,
    documentId: null,
  });
  const [actionLoading, setActionLoading] = useState(false);

  const handleUpload = async (file: File, fileTags: string[], onProgress: (progress: number) => void) => {
    try {
      await uploadDocument(file, fileTags, onProgress);
      showSuccess(`Uploaded ${file.name}`);
    } catch (err) {
      showError(`Failed to upload ${file.name}`);
      throw err;
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm.documentId) return;
    setActionLoading(true);
    try {
      await deleteDocument(deleteConfirm.documentId);
      if (selectedDocument?.id === deleteConfirm.documentId) {
        setSelectedDocument(null);
      }
      showSuccess('Document deleted');
    } catch (err) {
      showError('Failed to delete document');
      console.error(err);
    } finally {
      setActionLoading(false);
      setDeleteConfirm({ isOpen: false, documentId: null });
    }
  };

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4 p-4 border-b border-gray-200">
        <div className="flex items-center gap-4 flex-1">
          <Button onClick={() => setShowUploadModal(true)} icon={<Upload className="w-4 h-4" />}>
            Upload Document
          </Button>

          {/* Tag filter */}
          <div className="flex items-center gap-2 flex-1 max-w-xl">
            <span className="text-sm text-gray-500">Tags:</span>
            <div className="flex flex-wrap gap-1">
              {tags.slice(0, 10).map((tag) => (
                <button
                  key={tag.name}
                  onClick={() => toggleTag(tag.name)}
                  className={`px-2 py-1 text-xs rounded-full transition-colors ${
                    selectedTags.includes(tag.name)
                      ? 'bg-primary-100 text-primary-700 font-medium'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {tag.name} ({tag.count})
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Active filters */}
        {selectedTags.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Filtering by:</span>
            {selectedTags.map((tag) => (
              <Badge key={tag} size="sm" variant="info">
                {tag}
                <button onClick={() => toggleTag(tag)} className="ml-1">
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            ))}
            <button
              onClick={() => setSelectedTags([])}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              Clear all
            </button>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="flex-1 overflow-hidden">
        <DocumentTable
          documents={documents}
          loading={loading}
          onSelectDocument={setSelectedDocument}
          onDeleteDocument={(id) => setDeleteConfirm({ isOpen: true, documentId: id })}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          selectedTags={selectedTags}
        />
      </div>

      {/* Preview Modal */}
      <DocumentPreview
        document={selectedDocument}
        isOpen={selectedDocument !== null}
        onClose={() => setSelectedDocument(null)}
        onDelete={() => {
          if (selectedDocument) {
            setDeleteConfirm({ isOpen: true, documentId: selectedDocument.id });
          }
        }}
      />

      {/* Upload Modal */}
      <UploadModal
        isOpen={showUploadModal}
        onClose={() => {
          setShowUploadModal(false);
          refetch();
        }}
        onUpload={handleUpload}
        existingTags={tags.map((t) => t.name)}
      />

      {/* Delete Confirm Modal */}
      <ConfirmModal
        isOpen={deleteConfirm.isOpen}
        onClose={() => setDeleteConfirm({ isOpen: false, documentId: null })}
        onConfirm={handleDelete}
        title="Delete Document"
        message="Delete this document? This cannot be undone."
        confirmText="Delete"
        variant="danger"
        loading={actionLoading}
      />
    </div>
  );
}
