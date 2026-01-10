import { useState, useCallback } from 'react';
import { Button, ConfirmModal } from '@/components/common';
import { useNotification } from '@/contexts';
import { configService, ConfigImportResponse } from '@/services/configService';
import { Download, Upload, AlertTriangle, X, File, Check } from 'lucide-react';

export function Settings() {
  const { showSuccess, showError } = useNotification();

  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [importConfirm, setImportConfirm] = useState(false);
  const [lastImportResult, setLastImportResult] = useState<ConfigImportResponse | null>(null);

  const handleExport = async () => {
    setExporting(true);
    try {
      const blob = await configService.exportConfig();

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;

      // Extract filename from Content-Disposition or generate one
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
      link.download = `config-${timestamp}.tar.gz`;

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      showSuccess('Configuration exported successfully');
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to export configuration');
    } finally {
      setExporting(false);
    }
  };

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
      const file = e.dataTransfer.files[0];
      if (file.name.endsWith('.tar.gz') || file.name.endsWith('.tgz')) {
        setSelectedFile(file);
      } else {
        showError('Please select a .tar.gz or .tgz file');
      }
    }
  }, [showError]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      if (file.name.endsWith('.tar.gz') || file.name.endsWith('.tgz')) {
        setSelectedFile(file);
      } else {
        showError('Please select a .tar.gz or .tgz file');
      }
    }
  };

  const handleImportClick = () => {
    if (selectedFile) {
      setImportConfirm(true);
    }
  };

  const handleImportConfirm = async () => {
    if (!selectedFile) return;

    setImportConfirm(false);
    setImporting(true);
    try {
      const result = await configService.importConfig(selectedFile);
      setLastImportResult(result);
      setSelectedFile(null);
      showSuccess(
        `Imported ${result.agents_imported} agents and ${result.capabilities_imported} capabilities`
      );
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to import configuration');
    } finally {
      setImporting(false);
    }
  };

  const clearSelectedFile = () => {
    setSelectedFile(null);
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Settings</h2>
        <p className="text-sm text-gray-500">
          Manage your agent orchestrator configuration
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-2xl space-y-8">
          {/* Export Section */}
          <section className="bg-gray-50 rounded-lg p-6">
            <h3 className="text-base font-semibold text-gray-900 mb-2">
              Export Configuration
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              Download all agents and capabilities as a compressed archive.
              This includes agent blueprints, system prompts, MCP configurations, and capabilities.
            </p>
            <Button
              onClick={handleExport}
              loading={exporting}
              icon={<Download className="w-4 h-4" />}
            >
              Export Configuration
            </Button>
          </section>

          {/* Import Section */}
          <section className="bg-gray-50 rounded-lg p-6">
            <h3 className="text-base font-semibold text-gray-900 mb-2">
              Import Configuration
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              Upload a configuration archive to replace the current configuration.
            </p>

            {/* Warning Banner */}
            <div className="flex items-start gap-3 p-4 mb-4 bg-amber-50 border border-amber-200 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-amber-800">
                <p className="font-medium mb-1">Warning: Destructive Action</p>
                <p>
                  Importing a configuration will <strong>replace ALL existing agents and capabilities</strong>.
                  This action cannot be undone. Make sure to export your current configuration first if you want to keep it.
                </p>
              </div>
            </div>

            {/* Drop Zone */}
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                dragActive
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
              <p className="text-sm text-gray-600 mb-1">
                Drag and drop a configuration file here, or{' '}
                <label className="text-primary-600 hover:text-primary-700 cursor-pointer">
                  browse
                  <input
                    type="file"
                    accept=".tar.gz,.tgz"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                </label>
              </p>
              <p className="text-xs text-gray-400">
                Supported formats: .tar.gz, .tgz
              </p>
            </div>

            {/* Selected File */}
            {selectedFile && (
              <div className="flex items-center gap-3 p-3 mt-4 bg-white border border-gray-200 rounded-lg">
                <File className="w-5 h-5 text-gray-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-700 truncate">
                    {selectedFile.name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {(selectedFile.size / 1024).toFixed(1)} KB
                  </p>
                </div>
                <button
                  onClick={clearSelectedFile}
                  className="p-1 text-gray-400 hover:text-gray-600"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}

            {/* Import Button */}
            <div className="mt-4">
              <Button
                onClick={handleImportClick}
                disabled={!selectedFile}
                loading={importing}
                variant="danger"
                icon={<Upload className="w-4 h-4" />}
              >
                Import Configuration
              </Button>
            </div>

            {/* Last Import Result */}
            {lastImportResult && (
              <div className="flex items-start gap-3 p-4 mt-4 bg-green-50 border border-green-200 rounded-lg">
                <Check className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-green-800">
                  <p className="font-medium mb-1">Import Successful</p>
                  <ul className="list-disc list-inside space-y-1">
                    <li>{lastImportResult.agents_imported} agents imported (replaced {lastImportResult.agents_replaced})</li>
                    <li>{lastImportResult.capabilities_imported} capabilities imported (replaced {lastImportResult.capabilities_replaced})</li>
                  </ul>
                </div>
              </div>
            )}
          </section>
        </div>
      </div>

      {/* Import Confirmation Modal */}
      <ConfirmModal
        isOpen={importConfirm}
        title="Import Configuration"
        message={`Are you sure you want to import "${selectedFile?.name}"? This will replace ALL existing agents and capabilities. This action cannot be undone.`}
        variant="danger"
        confirmText="Import and Replace"
        onConfirm={handleImportConfirm}
        onClose={() => setImportConfirm(false)}
      />
    </div>
  );
}
