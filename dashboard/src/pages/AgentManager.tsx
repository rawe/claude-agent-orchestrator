import { useState } from 'react';
import { useAgents } from '@/hooks/useAgents';
import { AgentTable, AgentEditor } from '@/components/features/agents';
import { Button, ConfirmModal } from '@/components/common';
import { useNotification } from '@/contexts';
import { Agent, AgentCreate } from '@/types';
import { Plus } from 'lucide-react';

export function AgentManager() {
  const {
    agents,
    loading,
    createAgent,
    updateAgent,
    deleteAgent,
    updateAgentStatus,
    checkNameAvailable,
  } = useAgents();
  const { showSuccess, showError } = useNotification();

  const [searchQuery, setSearchQuery] = useState('');
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<{
    isOpen: boolean;
    agentName: string | null;
  }>({
    isOpen: false,
    agentName: null,
  });
  const [actionLoading, setActionLoading] = useState(false);

  const handleCreateNew = () => {
    setEditingAgent(null);
    setShowEditor(true);
  };

  const handleEditAgent = (agent: Agent) => {
    setEditingAgent(agent);
    setShowEditor(true);
  };

  const handleSaveAgent = async (data: AgentCreate) => {
    try {
      if (editingAgent) {
        await updateAgent(editingAgent.name, {
          description: data.description,
          system_prompt: data.system_prompt,
          mcp_servers: data.mcp_servers,
          skills: data.skills,
        });
        showSuccess('Agent updated successfully');
      } else {
        await createAgent(data);
        showSuccess('Agent created successfully');
      }
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to save agent');
      throw err;
    }
  };

  const handleDeleteAgent = async () => {
    if (!deleteConfirm.agentName) return;
    setActionLoading(true);
    try {
      await deleteAgent(deleteConfirm.agentName);
      showSuccess('Agent deleted');
    } catch (err) {
      showError('Failed to delete agent');
      console.error(err);
    } finally {
      setActionLoading(false);
      setDeleteConfirm({ isOpen: false, agentName: null });
    }
  };

  const handleToggleStatus = async (name: string, currentStatus: 'active' | 'inactive') => {
    const newStatus = currentStatus === 'active' ? 'inactive' : 'active';
    try {
      await updateAgentStatus(name, newStatus);
      showSuccess(`Agent ${newStatus === 'active' ? 'activated' : 'deactivated'}`);
    } catch (err) {
      showError('Failed to update agent status');
      console.error(err);
    }
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4 p-4 border-b border-gray-200">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Agent Blueprints</h2>
          <p className="text-sm text-gray-500">
            Manage specialized agent configurations for different tasks
          </p>
        </div>
        <Button onClick={handleCreateNew} icon={<Plus className="w-4 h-4" />}>
          New Agent
        </Button>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-hidden">
        <AgentTable
          agents={agents}
          loading={loading}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onEditAgent={handleEditAgent}
          onDeleteAgent={(name) => setDeleteConfirm({ isOpen: true, agentName: name })}
          onToggleStatus={handleToggleStatus}
        />
      </div>

      {/* Editor Modal */}
      <AgentEditor
        isOpen={showEditor}
        onClose={() => {
          setShowEditor(false);
          setEditingAgent(null);
        }}
        onSave={handleSaveAgent}
        agent={editingAgent}
        checkNameAvailable={checkNameAvailable}
      />

      {/* Delete Confirm Modal */}
      <ConfirmModal
        isOpen={deleteConfirm.isOpen}
        onClose={() => setDeleteConfirm({ isOpen: false, agentName: null })}
        onConfirm={handleDeleteAgent}
        title="Delete Agent"
        message={`Delete agent "${deleteConfirm.agentName}"? This cannot be undone.`}
        confirmText="Delete"
        variant="danger"
        loading={actionLoading}
      />
    </div>
  );
}
