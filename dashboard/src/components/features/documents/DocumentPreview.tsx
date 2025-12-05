import { useState, useRef, useEffect } from 'react';
import { Document, DocumentRelation } from '@/types';
import { Modal, Badge, CopyButton, Spinner, JsonViewer } from '@/components/common';
import { useDocumentContent } from '@/hooks/useDocuments';
import { documentService } from '@/services/documentService';
import { formatAbsoluteTime, formatFileSize } from '@/utils/formatters';
import { Download, Trash2, Eye, Code, Maximize2, Minimize2, X, Link2, ArrowUp, ArrowDown, ArrowLeftRight, ArrowLeft, ArrowRight } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface DocumentPreviewProps {
  document: Document | null;
  isOpen: boolean;
  onClose: () => void;
  onDelete: () => void;
  onNavigateToDocument?: (doc: Document) => void;
}

export function DocumentPreview({ document, isOpen, onClose, onDelete, onNavigateToDocument }: DocumentPreviewProps) {
  const { content, loading } = useDocumentContent(document?.id || null);
  const [viewMode, setViewMode] = useState<'rendered' | 'raw'>('rendered');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const scrollPositionRef = useRef(0);
  const [relations, setRelations] = useState<Record<string, DocumentRelation[]>>({});
  const [relationsLoading, setRelationsLoading] = useState(false);
  const [relatedDocs, setRelatedDocs] = useState<Record<string, Document>>({});

  // Fetch relations when document changes
  useEffect(() => {
    if (document?.id && isOpen) {
      setRelationsLoading(true);
      setRelatedDocs({});
      documentService.getDocumentRelations(document.id)
        .then(async (response) => {
          setRelations(response.relations);

          // Collect unique related document IDs
          const relatedIds = new Set<string>();
          Object.values(response.relations).forEach(items => {
            items.forEach(rel => relatedIds.add(rel.related_document_id));
          });

          // Fetch metadata for each related document
          const docsMap: Record<string, Document> = {};
          await Promise.all(
            Array.from(relatedIds).map(async (id) => {
              try {
                const doc = await documentService.getDocumentMetadata(id);
                docsMap[id] = doc;
              } catch (e) {
                console.error(`Failed to fetch metadata for ${id}:`, e);
              }
            })
          );
          setRelatedDocs(docsMap);
        })
        .catch((error) => {
          console.error('Failed to fetch relations:', error);
          setRelations({});
        })
        .finally(() => {
          setRelationsLoading(false);
        });
    } else {
      setRelations({});
      setRelatedDocs({});
    }
  }, [document?.id, isOpen]);

  // Handle fullscreen toggle
  const toggleFullscreen = () => {
    // Save scroll position before switching
    if (contentRef.current) {
      scrollPositionRef.current = contentRef.current.scrollTop;
    }
    setIsFullscreen(!isFullscreen);
  };

  // Restore scroll position after switching modes
  useEffect(() => {
    // Use requestAnimationFrame to ensure DOM is ready
    if (contentRef.current && scrollPositionRef.current > 0) {
      requestAnimationFrame(() => {
        if (contentRef.current) {
          contentRef.current.scrollTop = scrollPositionRef.current;
        }
      });
    }
  }, [isFullscreen, content]);

  // Handle ESC key to exit fullscreen
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullscreen) {
        setIsFullscreen(false);
      }
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [isFullscreen]);

  // Reset fullscreen when modal closes
  useEffect(() => {
    if (!isOpen) {
      setIsFullscreen(false);
    }
  }, [isOpen]);

  if (!document) return null;

  const hasRelations = Object.keys(relations).length > 0 &&
    Object.values(relations).some(arr => arr.length > 0);

  const getRelationIcon = (type: string) => {
    switch (type) {
      case 'parent': return <ArrowUp className="w-3.5 h-3.5 text-blue-500" />;
      case 'child': return <ArrowDown className="w-3.5 h-3.5 text-green-500" />;
      case 'related': return <ArrowLeftRight className="w-3.5 h-3.5 text-purple-500" />;
      case 'predecessor': return <ArrowLeft className="w-3.5 h-3.5 text-amber-500" />;
      case 'successor': return <ArrowRight className="w-3.5 h-3.5 text-amber-500" />;
      default: return <Link2 className="w-3.5 h-3.5 text-gray-500" />;
    }
  };

  const getRelationLabel = (type: string) => {
    switch (type) {
      case 'parent': return 'Parent of';
      case 'child': return 'Child of';
      case 'related': return 'Related to';
      case 'predecessor': return 'Precedes';
      case 'successor': return 'Follows';
      default: return type;
    }
  };

  const isMarkdown = document.content_type.includes('markdown') || document.filename.endsWith('.md');
  const isJson = document.content_type.includes('json') || document.filename.endsWith('.json');
  const isImage = document.content_type.startsWith('image/');
  const canPreview = isMarkdown || isJson || isImage || document.content_type.includes('text');

  const renderContent = () => {
    // Images don't need text content loading - render directly from URL
    if (isImage) {
      return (
        <div className="flex justify-center">
          <img
            src={document.url}
            alt={document.filename}
            className="max-w-full h-auto rounded-lg shadow-sm"
            style={{ maxHeight: isFullscreen ? 'calc(100vh - 200px)' : '500px' }}
          />
        </div>
      );
    }

    if (loading) {
      return (
        <div className="flex justify-center py-8">
          <Spinner size="lg" />
        </div>
      );
    }

    if (!content) {
      return (
        <div className="text-center py-8 text-gray-500">
          Failed to load content
        </div>
      );
    }

    if (!canPreview) {
      return (
        <div className="text-center py-8 text-gray-500">
          <p className="mb-4">Preview not available for this file type</p>
          <a
            href={document.url}
            download={document.filename}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
          >
            <Download className="w-4 h-4" />
            Download File
          </a>
        </div>
      );
    }

    if (isMarkdown) {
      if (viewMode === 'raw') {
        return (
          <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono bg-gray-50 p-4 rounded-md">
            {content}
          </pre>
        );
      }
      return (
        <div className={`markdown-content prose prose-sm max-w-none ${isFullscreen ? 'px-8' : ''}`}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
      );
    }

    if (isJson) {
      try {
        const parsed = JSON.parse(content);
        if (viewMode === 'raw') {
          return (
            <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono bg-gray-50 p-4 rounded-md">
              {content}
            </pre>
          );
        }
        return (
          <JsonViewer
            data={parsed}
            collapsed={false}
            className={isFullscreen ? 'max-h-none' : 'max-h-[500px]'}
          />
        );
      } catch {
        return (
          <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono bg-gray-50 p-4 rounded-md">
            {content}
          </pre>
        );
      }
    }

    // Plain text
    return (
      <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono bg-gray-50 p-4 rounded-md">
        {content}
      </pre>
    );
  };

  // Fullscreen mode
  if (isFullscreen) {
    return (
      <div className="fixed inset-0 z-50 bg-white flex flex-col">
        {/* Sticky Header */}
        <div className="flex-shrink-0 flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-white shadow-sm">
          <div className="flex items-center gap-4">
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-500 focus:outline-none"
              title="Close"
            >
              <X className="w-5 h-5" />
            </button>
            <h3 className="text-lg font-semibold text-gray-900">{document.filename}</h3>
          </div>

          <div className="flex items-center gap-2">
            {(isMarkdown || isJson) && (
              <div className="flex rounded-md border border-gray-300 overflow-hidden">
                <button
                  onClick={() => setViewMode('rendered')}
                  className={`flex items-center gap-1 px-3 py-1.5 text-xs ${
                    viewMode === 'rendered'
                      ? 'bg-primary-50 text-primary-700'
                      : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <Eye className="w-3.5 h-3.5" />
                  {isJson ? 'Pretty' : 'Rendered'}
                </button>
                <button
                  onClick={() => setViewMode('raw')}
                  className={`flex items-center gap-1 px-3 py-1.5 text-xs border-l ${
                    viewMode === 'raw'
                      ? 'bg-primary-50 text-primary-700'
                      : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <Code className="w-3.5 h-3.5" />
                  Raw
                </button>
              </div>
            )}
            <button
              onClick={toggleFullscreen}
              className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              title="Exit Fullscreen (ESC)"
            >
              <Minimize2 className="w-4 h-4" />
            </button>
            <a
              href={document.url}
              download={document.filename}
              className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              title="Download"
            >
              <Download className="w-4 h-4" />
            </a>
            <button
              onClick={onDelete}
              className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-700 bg-white border border-red-300 rounded-md hover:bg-red-50"
              title="Delete"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div ref={contentRef} className="flex-1 overflow-auto bg-white" style={{ scrollBehavior: 'auto' }}>
          <div className="max-w-5xl mx-auto py-8">
            {renderContent()}
          </div>
        </div>
      </div>
    );
  }

  // Modal mode
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={document.filename} size="2xl">
      <div className="p-6">
        {/* Actions */}
        <div className="flex items-center justify-end gap-2 mb-4">
          {(isMarkdown || isJson) && (
            <div className="flex rounded-md border border-gray-300 overflow-hidden mr-auto">
              <button
                onClick={() => setViewMode('rendered')}
                className={`flex items-center gap-1 px-3 py-1.5 text-xs ${
                  viewMode === 'rendered'
                    ? 'bg-primary-50 text-primary-700'
                    : 'bg-white text-gray-600 hover:bg-gray-50'
                }`}
              >
                <Eye className="w-3.5 h-3.5" />
                {isJson ? 'Pretty' : 'Rendered'}
              </button>
              <button
                onClick={() => setViewMode('raw')}
                className={`flex items-center gap-1 px-3 py-1.5 text-xs border-l ${
                  viewMode === 'raw'
                    ? 'bg-primary-50 text-primary-700'
                    : 'bg-white text-gray-600 hover:bg-gray-50'
                }`}
              >
                <Code className="w-3.5 h-3.5" />
                Raw
              </button>
            </div>
          )}
          <button
            onClick={toggleFullscreen}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            title="Fullscreen"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
          <a
            href={document.url}
            download={document.filename}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            title="Download"
          >
            <Download className="w-4 h-4" />
          </a>
          <button
            onClick={onDelete}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-700 bg-white border border-red-300 rounded-md hover:bg-red-50"
            title="Delete"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>

        {/* Metadata */}
        <div className="grid grid-cols-2 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
          <div>
            <p className="text-xs text-gray-500 mb-1">Document ID</p>
            <div className="flex items-center gap-1">
              <span className="font-mono text-sm">{document.id}</span>
              <CopyButton text={document.id} />
            </div>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">MIME Type</p>
            <span className="text-sm">{document.content_type}</span>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">Created At</p>
            <span className="text-sm">{formatAbsoluteTime(document.created_at)}</span>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">Size</p>
            <span className="text-sm">{formatFileSize(document.size_bytes)}</span>
          </div>
          <div className="col-span-2">
            <p className="text-xs text-gray-500 mb-1">Tags</p>
            {document.tags.length > 0 ? (
              <div className="flex flex-wrap gap-1">
                {document.tags.map((tag) => (
                  <Badge key={tag} size="md">
                    {tag}
                  </Badge>
                ))}
              </div>
            ) : (
              <span className="text-sm text-gray-400">No tags</span>
            )}
          </div>
          {document.metadata?.description && (
            <div className="col-span-2">
              <p className="text-xs text-gray-500 mb-1">Description</p>
              <p className="text-sm text-gray-700">{document.metadata.description}</p>
            </div>
          )}
          {document.checksum && (
            <div className="col-span-2">
              <p className="text-xs text-gray-500 mb-1">Checksum (SHA256)</p>
              <div className="flex items-center gap-1">
                <span className="font-mono text-xs text-gray-600 truncate">{document.checksum}</span>
                <CopyButton text={document.checksum} />
              </div>
            </div>
          )}
        </div>

        {/* Relations */}
        <div className="mb-6">
          <h4 className="text-sm font-medium text-gray-900 mb-2 flex items-center gap-2">
            <Link2 className="w-4 h-4" />
            Relations
          </h4>
          {relationsLoading ? (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Spinner size="sm" />
              Loading relations...
            </div>
          ) : hasRelations ? (
            <div className="space-y-3">
              {Object.entries(relations).map(([type, items]) => (
                items.length > 0 && (
                  <div key={type} className="border border-gray-200 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-2">
                      {getRelationIcon(type)}
                      <span className="text-xs font-medium text-gray-700 uppercase tracking-wide">
                        {getRelationLabel(type)}
                      </span>
                      <span className="text-xs text-gray-400">({items.length})</span>
                    </div>
                    <div className="space-y-2">
                      {items.map((rel) => {
                        const relatedDoc = relatedDocs[rel.related_document_id];
                        const description = relatedDoc?.metadata?.description;
                        const truncatedDesc = description && description.length > 80
                          ? description.slice(0, 80) + '...'
                          : description;
                        const canNavigate = relatedDoc && onNavigateToDocument;

                        return (
                          <div key={rel.id} className="bg-gray-50 rounded p-2 hover:bg-gray-100 transition-colors">
                            {/* Primary: Filename */}
                            <div className="flex items-center gap-2">
                              {canNavigate ? (
                                <button
                                  onClick={() => onNavigateToDocument(relatedDoc)}
                                  className="text-sm font-medium text-primary-600 hover:text-primary-800 hover:underline truncate flex-1 text-left"
                                  title={`Open ${relatedDoc.filename}`}
                                >
                                  {relatedDoc.filename}
                                </button>
                              ) : (
                                <span className="text-sm font-medium text-gray-900 truncate flex-1">
                                  {relatedDoc?.filename || 'Loading...'}
                                </span>
                              )}
                            </div>

                            {/* Secondary: Description with tooltip */}
                            {description && (
                              <p
                                className="text-xs text-gray-500 mt-1 truncate cursor-help"
                                title={description}
                              >
                                {truncatedDesc}
                              </p>
                            )}

                            {/* Relation note if different from description */}
                            {rel.note && rel.note !== description && (
                              <p className="text-xs text-blue-600 mt-1 italic">
                                Note: {rel.note}
                              </p>
                            )}

                            {/* Tertiary: Document ID */}
                            <div className="flex items-center gap-1 mt-1">
                              <span className="font-mono text-[10px] text-gray-400 truncate">
                                {rel.related_document_id}
                              </span>
                              <CopyButton text={rel.related_document_id} />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400">No relations</p>
          )}
        </div>

        {/* Content Preview */}
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-2">Content Preview</h4>
          <div ref={contentRef} className="overflow-auto max-h-[calc(100vh-32rem)]" style={{ scrollBehavior: 'auto' }}>
            {renderContent()}
          </div>
        </div>
      </div>
    </Modal>
  );
}
