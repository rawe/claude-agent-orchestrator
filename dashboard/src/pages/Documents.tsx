import { useState, useMemo } from 'react';
import { useDocuments, useTags } from '@/hooks/useDocuments';
import { DocumentTable, DocumentPreview, UploadModal, TagOverflowDropdown } from '@/components/features/documents';
import { Button, Badge, ConfirmModal } from '@/components/common';
import { useNotification } from '@/contexts';
import { Document } from '@/types';
import { documentService } from '@/services/documentService';
import { Upload, X, Sparkles, RefreshCw, Tag } from 'lucide-react';

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

  // Semantic search state
  const [semanticQuery, setSemanticQuery] = useState('');
  const [semanticResultIds, setSemanticResultIds] = useState<string[] | null>(null);
  const [semanticSearching, setSemanticSearching] = useState(false);
  const [activeSemanticQuery, setActiveSemanticQuery] = useState<string | null>(null);

  // Compute visible documents and their tags (filtered by semantic search if active)
  const visibleTags = useMemo(() => {
    const visibleDocs = semanticResultIds !== null
      ? documents.filter((doc) => semanticResultIds.includes(doc.id))
      : documents;

    const tagCounts = new Map<string, number>();
    visibleDocs.forEach((doc) => {
      doc.tags.forEach((tag) => {
        tagCounts.set(tag, (tagCounts.get(tag) || 0) + 1);
      });
    });

    return Array.from(tagCounts.entries())
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);
  }, [documents, semanticResultIds]);

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

  const handleSemanticSearch = async () => {
    if (!semanticQuery.trim()) return;
    setSemanticSearching(true);
    try {
      const response = await documentService.semanticSearch(semanticQuery.trim());
      setSemanticResultIds(response.results.map((r) => r.document_id));
      setActiveSemanticQuery(semanticQuery.trim());
    } catch (err) {
      showError('Semantic search failed. Is the search service available?');
      console.error(err);
    } finally {
      setSemanticSearching(false);
    }
  };

  const clearSemanticSearch = () => {
    setSemanticResultIds(null);
    setActiveSemanticQuery(null);
    setSemanticQuery('');
  };

  const handleRefresh = async () => {
    // Always refetch documents list
    await refetch();
    // If semantic search is active, re-run it
    if (activeSemanticQuery) {
      setSemanticSearching(true);
      try {
        const response = await documentService.semanticSearch(activeSemanticQuery);
        setSemanticResultIds(response.results.map((r) => r.document_id));
      } catch (err) {
        showError('Failed to refresh semantic search');
        console.error(err);
      } finally {
        setSemanticSearching(false);
      }
    }
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header: Title + Actions */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">Context Store</h1>
          <p className="text-sm text-gray-500">Share documents between isolated agent sessions</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={() => setShowUploadModal(true)}
            icon={<Upload className="w-4 h-4" />}
          >
            Upload
          </Button>
          <Button
            onClick={handleRefresh}
            variant="secondary"
            icon={<RefreshCw className={`w-4 h-4 ${loading || semanticSearching ? 'animate-spin' : ''}`} />}
            disabled={loading || semanticSearching}
            title="Refresh"
          />
        </div>
      </div>

      {/* Filter Section */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50/50 space-y-3">
        {/* Semantic Search */}
        <div className="space-y-1.5">
          <label className="flex items-center gap-1.5 text-sm font-medium text-gray-700">
            <Sparkles className="w-4 h-4 text-purple-500" />
            Semantic Search
          </label>
          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Ask a question about your documents..."
              value={semanticQuery}
              onChange={(e) => setSemanticQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSemanticSearch()}
              disabled={semanticSearching}
              className="flex-1 max-w-xl px-3 py-2 text-sm border border-gray-300 rounded-md
                         focus:outline-none focus:ring-1 focus:ring-purple-500
                         focus:border-purple-500 disabled:opacity-50"
            />
            <Button
              onClick={handleSemanticSearch}
              disabled={!semanticQuery.trim() || semanticSearching}
              variant="secondary"
            >
              {semanticSearching ? 'Searching...' : 'Search'}
            </Button>
          </div>
        </div>

        {/* Tags */}
        <div className="space-y-1.5">
          <label className="flex items-center gap-1.5 text-sm font-medium text-gray-700">
            <Tag className="w-4 h-4 text-gray-500" />
            Tags
            {visibleTags.length > 8 && (
              <span className="text-xs text-gray-400 font-normal">
                ({visibleTags.length} total)
              </span>
            )}
          </label>
          <div className="flex flex-wrap items-center gap-1.5">
            {visibleTags.slice(0, 8).map((tag) => (
              <button
                key={tag.name}
                onClick={() => toggleTag(tag.name)}
                className={`px-2.5 py-1 text-xs rounded-full transition-colors ${
                  selectedTags.includes(tag.name)
                    ? 'bg-primary-100 text-primary-700 font-medium'
                    : 'bg-white border border-gray-200 text-gray-600 hover:border-gray-300'
                }`}
              >
                {tag.name} ({tag.count})
              </button>
            ))}

            {/* Overflow dropdown */}
            {visibleTags.length > 8 && (
              <TagOverflowDropdown
                tags={visibleTags.slice(8)}
                selectedTags={selectedTags}
                onToggle={toggleTag}
              />
            )}

            {visibleTags.length === 0 && (
              <span className="text-xs text-gray-400 italic">No tags available</span>
            )}
          </div>
        </div>

        {/* Active Filters */}
        {(selectedTags.length > 0 || activeSemanticQuery) && (
          <div className="flex items-center gap-2 pt-2 border-t border-gray-200">
            <span className="text-xs text-gray-500">Active:</span>

            {activeSemanticQuery && (
              <Badge size="sm" variant="info">
                <Sparkles className="w-3 h-3 mr-1" />
                {activeSemanticQuery.length > 30
                  ? activeSemanticQuery.slice(0, 30) + '...'
                  : activeSemanticQuery}
                <button onClick={clearSemanticSearch} className="ml-1.5 hover:text-gray-700">
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            )}

            {selectedTags.map((tag) => (
              <Badge key={tag} size="sm" variant="info">
                {tag}
                <button onClick={() => toggleTag(tag)} className="ml-1.5 hover:text-gray-700">
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            ))}

            <button
              onClick={() => {
                setSelectedTags([]);
                clearSemanticSearch();
              }}
              className="ml-auto text-xs text-gray-500 hover:text-gray-700"
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
          semanticResultIds={semanticResultIds}
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
        onNavigateToDocument={setSelectedDocument}
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
