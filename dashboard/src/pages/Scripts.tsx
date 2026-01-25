import { useState } from 'react';
import { useScripts } from '@/hooks/useScripts';
import { ScriptTable, ScriptEditor } from '@/components/features/scripts';
import { Button, ConfirmModal } from '@/components/common';
import { useNotification } from '@/contexts';
import { Script, ScriptSummary, ScriptCreate } from '@/types/script';
import { Plus } from 'lucide-react';

export function Scripts() {
  const {
    scripts,
    loading,
    getScript,
    createScript,
    updateScript,
    deleteScript,
    checkNameAvailable,
  } = useScripts();
  const { showSuccess, showError } = useNotification();

  const [searchQuery, setSearchQuery] = useState('');
  const [editingScript, setEditingScript] = useState<Script | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<{
    isOpen: boolean;
    scriptName: string | null;
  }>({
    isOpen: false,
    scriptName: null,
  });
  const [actionLoading, setActionLoading] = useState(false);

  const handleCreateNew = () => {
    setEditingScript(null);
    setShowEditor(true);
  };

  const handleEditScript = async (summary: ScriptSummary) => {
    try {
      // Fetch full script data for editing
      const full = await getScript(summary.name);
      setEditingScript(full);
      setShowEditor(true);
    } catch (err) {
      showError('Failed to load script details');
      console.error(err);
    }
  };

  const handleSaveScript = async (data: ScriptCreate) => {
    try {
      if (editingScript) {
        await updateScript(editingScript.name, {
          description: data.description,
          script_file: data.script_file,
          script_content: data.script_content,
          parameters_schema: data.parameters_schema,
          demands: data.demands,
        });
        showSuccess('Script updated successfully');
      } else {
        await createScript(data);
        showSuccess('Script created successfully');
      }
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to save script');
      throw err;
    }
  };

  const handleDeleteScript = async () => {
    if (!deleteConfirm.scriptName) return;
    setActionLoading(true);
    try {
      await deleteScript(deleteConfirm.scriptName);
      showSuccess('Script deleted');
    } catch (err) {
      showError('Failed to delete script');
      console.error(err);
    } finally {
      setActionLoading(false);
      setDeleteConfirm({ isOpen: false, scriptName: null });
    }
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4 p-4 border-b border-gray-200">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Scripts</h2>
          <p className="text-sm text-gray-500">
            Reusable scripts that can be executed by procedural agents
          </p>
        </div>
        <Button onClick={handleCreateNew} icon={<Plus className="w-4 h-4" />}>
          New Script
        </Button>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-hidden">
        <ScriptTable
          scripts={scripts}
          loading={loading}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onEditScript={handleEditScript}
          onDeleteScript={(name) => setDeleteConfirm({ isOpen: true, scriptName: name })}
        />
      </div>

      {/* Editor Modal */}
      <ScriptEditor
        isOpen={showEditor}
        onClose={() => {
          setShowEditor(false);
          setEditingScript(null);
        }}
        onSave={handleSaveScript}
        script={editingScript}
        checkNameAvailable={checkNameAvailable}
      />

      {/* Delete Confirm Modal */}
      <ConfirmModal
        isOpen={deleteConfirm.isOpen}
        onClose={() => setDeleteConfirm({ isOpen: false, scriptName: null })}
        onConfirm={handleDeleteScript}
        title="Delete Script"
        message={`Delete script "${deleteConfirm.scriptName}"? This cannot be undone. Agents using this script may break.`}
        confirmText="Delete"
        variant="danger"
        loading={actionLoading}
      />
    </div>
  );
}
