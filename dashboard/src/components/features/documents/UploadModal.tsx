import { useState, useCallback } from 'react';
import { Modal, Button, Badge } from '@/components/common';
import { Upload, X, File, Check, AlertCircle } from 'lucide-react';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpload: (file: File, tags: string[], onProgress: (progress: number) => void) => Promise<void>;
  existingTags?: string[];
}

interface FileUploadState {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

export function UploadModal({ isOpen, onClose, onUpload, existingTags = [] }: UploadModalProps) {
  const [files, setFiles] = useState<FileUploadState[]>([]);
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [description, setDescription] = useState('');
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const newFiles = Array.from(e.dataTransfer.files).map((file) => ({
        file,
        progress: 0,
        status: 'pending' as const,
      }));
      setFiles((prev) => [...prev, ...newFiles]);
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files).map((file) => ({
        file,
        progress: 0,
        status: 'pending' as const,
      }));
      setFiles((prev) => [...prev, ...newFiles]);
    }
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const addTag = (tag: string) => {
    const trimmed = tag.trim().toLowerCase();
    if (trimmed && !tags.includes(trimmed)) {
      setTags((prev) => [...prev, trimmed]);
    }
    setTagInput('');
  };

  const removeTag = (tag: string) => {
    setTags((prev) => prev.filter((t) => t !== tag));
  };

  const handleTagInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addTag(tagInput);
    }
  };

  const handleUpload = async () => {
    for (let i = 0; i < files.length; i++) {
      if (files[i].status !== 'pending') continue;

      setFiles((prev) =>
        prev.map((f, idx) => (idx === i ? { ...f, status: 'uploading' } : f))
      );

      try {
        await onUpload(files[i].file, tags, (progress) => {
          setFiles((prev) =>
            prev.map((f, idx) => (idx === i ? { ...f, progress } : f))
          );
        });

        setFiles((prev) =>
          prev.map((f, idx) => (idx === i ? { ...f, status: 'success', progress: 100 } : f))
        );
      } catch (err) {
        setFiles((prev) =>
          prev.map((f, idx) =>
            idx === i
              ? { ...f, status: 'error', error: err instanceof Error ? err.message : 'Upload failed' }
              : f
          )
        );
      }
    }
  };

  const handleClose = () => {
    setFiles([]);
    setTags([]);
    setTagInput('');
    setDescription('');
    onClose();
  };

  const allUploaded = files.length > 0 && files.every((f) => f.status === 'success');
  const hasFiles = files.length > 0;
  const hasPendingFiles = files.some((f) => f.status === 'pending');
  const isUploading = files.some((f) => f.status === 'uploading');

  const filteredSuggestions = existingTags.filter(
    (t) => t.includes(tagInput.toLowerCase()) && !tags.includes(t)
  );

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Upload Document" size="lg">
      <div className="p-6 space-y-6">
        {/* Drop zone */}
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            dragActive
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-300 hover:border-gray-400'
          }`}
        >
          <Upload className="w-10 h-10 text-gray-400 mx-auto mb-3" />
          <p className="text-sm text-gray-600 mb-2">
            Drag and drop files here, or{' '}
            <label className="text-primary-600 hover:text-primary-700 cursor-pointer">
              browse
              <input
                type="file"
                multiple
                onChange={handleFileSelect}
                className="hidden"
              />
            </label>
          </p>
          <p className="text-xs text-gray-400">Max 50MB per file</p>
        </div>

        {/* File list */}
        {hasFiles && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-gray-700">Files</h4>
            {files.map((fileState, index) => (
              <div
                key={index}
                className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
              >
                <File className="w-5 h-5 text-gray-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-700 truncate">
                    {fileState.file.name}
                  </p>
                  {fileState.status === 'uploading' && (
                    <div className="mt-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary-500 transition-all"
                        style={{ width: `${fileState.progress}%` }}
                      />
                    </div>
                  )}
                  {fileState.status === 'error' && (
                    <p className="text-xs text-red-500 flex items-center gap-1 mt-1">
                      <AlertCircle className="w-3 h-3" />
                      {fileState.error}
                    </p>
                  )}
                </div>
                {fileState.status === 'success' && (
                  <Check className="w-5 h-5 text-green-500" />
                )}
                {fileState.status === 'pending' && (
                  <button
                    onClick={() => removeFile(index)}
                    className="p-1 text-gray-400 hover:text-gray-600"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Tags */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Tags (optional)
          </label>
          <div className="flex flex-wrap gap-2 mb-2">
            {tags.map((tag) => (
              <Badge key={tag} size="md">
                {tag}
                <button
                  onClick={() => removeTag(tag)}
                  className="ml-1 text-gray-500 hover:text-gray-700"
                >
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            ))}
          </div>
          <div className="relative">
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={handleTagInputKeyDown}
              placeholder="Add tags (press Enter)"
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
            {tagInput && filteredSuggestions.length > 0 && (
              <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-32 overflow-auto">
                {filteredSuggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => addTag(suggestion)}
                    className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Description (optional)
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe this document..."
            rows={3}
            maxLength={500}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 resize-none"
          />
          <p className="text-xs text-gray-400 text-right mt-1">{description.length}/500</p>
        </div>
      </div>

      {/* Footer */}
      <div className="flex justify-end gap-3 px-6 py-4 bg-gray-50 border-t">
        <Button variant="secondary" onClick={handleClose}>
          {allUploaded ? 'Done' : 'Cancel'}
        </Button>
        {!allUploaded && (
          <Button
            onClick={handleUpload}
            disabled={!hasPendingFiles || isUploading}
            loading={isUploading}
          >
            Upload {hasPendingFiles ? `(${files.filter((f) => f.status === 'pending').length})` : ''}
          </Button>
        )}
      </div>
    </Modal>
  );
}
