import { useState } from 'react';
import { useCapabilities } from '@/hooks/useCapabilities';
import { CapabilityTable, CapabilityEditor } from '@/components/features/capabilities';
import { Button, ConfirmModal } from '@/components/common';
import { useNotification } from '@/contexts';
import { Capability, CapabilitySummary, CapabilityCreate } from '@/types/capability';
import { Plus } from 'lucide-react';

export function Capabilities() {
  const {
    capabilities,
    loading,
    getCapability,
    createCapability,
    updateCapability,
    deleteCapability,
    checkNameAvailable,
  } = useCapabilities();
  const { showSuccess, showError } = useNotification();

  const [searchQuery, setSearchQuery] = useState('');
  const [editingCapability, setEditingCapability] = useState<Capability | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<{
    isOpen: boolean;
    capabilityName: string | null;
  }>({
    isOpen: false,
    capabilityName: null,
  });
  const [actionLoading, setActionLoading] = useState(false);

  const handleCreateNew = () => {
    setEditingCapability(null);
    setShowEditor(true);
  };

  const handleEditCapability = async (summary: CapabilitySummary) => {
    try {
      // Fetch full capability data for editing
      const full = await getCapability(summary.name);
      setEditingCapability(full);
      setShowEditor(true);
    } catch (err) {
      showError('Failed to load capability details');
      console.error(err);
    }
  };

  const handleSaveCapability = async (data: CapabilityCreate) => {
    try {
      if (editingCapability) {
        await updateCapability(editingCapability.name, {
          description: data.description,
          text: data.text,
          mcp_servers: data.mcp_servers,
        });
        showSuccess('Capability updated successfully');
      } else {
        await createCapability(data);
        showSuccess('Capability created successfully');
      }
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to save capability');
      throw err;
    }
  };

  const handleDeleteCapability = async () => {
    if (!deleteConfirm.capabilityName) return;
    setActionLoading(true);
    try {
      await deleteCapability(deleteConfirm.capabilityName);
      showSuccess('Capability deleted');
    } catch (err) {
      showError('Failed to delete capability');
      console.error(err);
    } finally {
      setActionLoading(false);
      setDeleteConfirm({ isOpen: false, capabilityName: null });
    }
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4 p-4 border-b border-gray-200">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Capabilities</h2>
          <p className="text-sm text-gray-500">
            Reusable capability definitions that can be shared across multiple agents
          </p>
        </div>
        <Button onClick={handleCreateNew} icon={<Plus className="w-4 h-4" />}>
          New Capability
        </Button>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-hidden">
        <CapabilityTable
          capabilities={capabilities}
          loading={loading}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onEditCapability={handleEditCapability}
          onDeleteCapability={(name) => setDeleteConfirm({ isOpen: true, capabilityName: name })}
        />
      </div>

      {/* Editor Modal */}
      <CapabilityEditor
        isOpen={showEditor}
        onClose={() => {
          setShowEditor(false);
          setEditingCapability(null);
        }}
        onSave={handleSaveCapability}
        capability={editingCapability}
        checkNameAvailable={checkNameAvailable}
      />

      {/* Delete Confirm Modal */}
      <ConfirmModal
        isOpen={deleteConfirm.isOpen}
        onClose={() => setDeleteConfirm({ isOpen: false, capabilityName: null })}
        onConfirm={handleDeleteCapability}
        title="Delete Capability"
        message={`Delete capability "${deleteConfirm.capabilityName}"? This cannot be undone. Agents using this capability may break.`}
        confirmText="Delete"
        variant="danger"
        loading={actionLoading}
      />
    </div>
  );
}
