import { useState } from 'react';
import { Document } from '@/types';
import { Modal, Badge, CopyButton, Spinner } from '@/components/common';
import { useDocumentContent } from '@/hooks/useDocuments';
import { formatAbsoluteTime, formatFileSize } from '@/utils/formatters';
import { Download, Trash2, Eye, Code } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface DocumentPreviewProps {
  document: Document | null;
  isOpen: boolean;
  onClose: () => void;
  onDelete: () => void;
}

export function DocumentPreview({ document, isOpen, onClose, onDelete }: DocumentPreviewProps) {
  const { content, loading } = useDocumentContent(document?.id || null);
  const [viewMode, setViewMode] = useState<'rendered' | 'raw'>('rendered');

  if (!document) return null;

  const isMarkdown = document.content_type.includes('markdown') || document.filename.endsWith('.md');
  const isJson = document.content_type.includes('json') || document.filename.endsWith('.json');
  const canPreview = isMarkdown || isJson || document.content_type.includes('text');

  const renderContent = () => {
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
          <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono bg-gray-50 p-4 rounded-md overflow-auto max-h-[400px]">
            {content}
          </pre>
        );
      }
      return (
        <div className="markdown-content prose prose-sm max-w-none overflow-auto max-h-[400px]">
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
      );
    }

    if (isJson) {
      try {
        const parsed = JSON.parse(content);
        if (viewMode === 'raw') {
          return (
            <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono bg-gray-50 p-4 rounded-md overflow-auto max-h-[400px]">
              {content}
            </pre>
          );
        }
        return (
          <pre className="whitespace-pre-wrap text-sm font-mono bg-gray-900 text-gray-100 p-4 rounded-md overflow-auto max-h-[400px]">
            {JSON.stringify(parsed, null, 2)}
          </pre>
        );
      } catch {
        return (
          <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono bg-gray-50 p-4 rounded-md overflow-auto max-h-[400px]">
            {content}
          </pre>
        );
      }
    }

    // Plain text
    return (
      <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono bg-gray-50 p-4 rounded-md overflow-auto max-h-[400px]">
        {content}
      </pre>
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={document.filename} size="xl">
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
          <a
            href={document.url}
            download={document.filename}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            <Download className="w-4 h-4" />
            Download
          </a>
          <button
            onClick={onDelete}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-700 bg-white border border-red-300 rounded-md hover:bg-red-50"
          >
            <Trash2 className="w-4 h-4" />
            Delete
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

        {/* Content Preview */}
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-2">Content Preview</h4>
          {renderContent()}
        </div>
      </div>
    </Modal>
  );
}
