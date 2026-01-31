import { useState } from 'react';
import { useMcpServers } from '@/hooks/useMcpServers';
import { McpServerTable, McpServerEditor } from '@/components/features/mcp-servers';
import { Button, ConfirmModal } from '@/components/common';
import { useNotification } from '@/contexts';
import type { MCPServerRegistryEntry, MCPServerRegistryCreate } from '@/types/mcpServer';
import { Plus } from 'lucide-react';

export function McpServers() {
  const {
    mcpServers,
    loading,
    getMcpServer,
    createMcpServer,
    updateMcpServer,
    deleteMcpServer,
    checkIdAvailable,
  } = useMcpServers();
  const { showSuccess, showError } = useNotification();

  const [searchQuery, setSearchQuery] = useState('');
  const [editingServer, setEditingServer] = useState<MCPServerRegistryEntry | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<{
    isOpen: boolean;
    serverId: string | null;
  }>({
    isOpen: false,
    serverId: null,
  });
  const [actionLoading, setActionLoading] = useState(false);

  const handleCreateNew = () => {
    setEditingServer(null);
    setShowEditor(true);
  };

  const handleEditServer = async (server: MCPServerRegistryEntry) => {
    try {
      // Fetch full server data for editing (in case summary differs)
      const full = await getMcpServer(server.id);
      setEditingServer(full);
      setShowEditor(true);
    } catch (err) {
      showError('Failed to load MCP server details');
      console.error(err);
    }
  };

  const handleSaveServer = async (data: MCPServerRegistryCreate) => {
    try {
      if (editingServer) {
        await updateMcpServer(editingServer.id, {
          name: data.name,
          description: data.description,
          url: data.url,
          config_schema: data.config_schema,
          default_config: data.default_config,
        });
        showSuccess('MCP server updated successfully');
      } else {
        await createMcpServer(data);
        showSuccess('MCP server created successfully');
      }
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to save MCP server');
      throw err;
    }
  };

  const handleDeleteServer = async () => {
    if (!deleteConfirm.serverId) return;
    setActionLoading(true);
    try {
      await deleteMcpServer(deleteConfirm.serverId);
      showSuccess('MCP server deleted');
    } catch (err) {
      showError('Failed to delete MCP server');
      console.error(err);
    } finally {
      setActionLoading(false);
      setDeleteConfirm({ isOpen: false, serverId: null });
    }
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4 p-4 border-b border-gray-200">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">MCP Servers</h2>
          <p className="text-sm text-gray-500">
            Centralized registry of MCP server configurations for agents and capabilities
          </p>
        </div>
        <Button onClick={handleCreateNew} icon={<Plus className="w-4 h-4" />}>
          New MCP Server
        </Button>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-hidden">
        <McpServerTable
          servers={mcpServers}
          loading={loading}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onEditServer={handleEditServer}
          onDeleteServer={(id) => setDeleteConfirm({ isOpen: true, serverId: id })}
        />
      </div>

      {/* Editor Modal */}
      <McpServerEditor
        isOpen={showEditor}
        onClose={() => {
          setShowEditor(false);
          setEditingServer(null);
        }}
        onSave={handleSaveServer}
        server={editingServer}
        checkIdAvailable={checkIdAvailable}
      />

      {/* Delete Confirm Modal */}
      <ConfirmModal
        isOpen={deleteConfirm.isOpen}
        onClose={() => setDeleteConfirm({ isOpen: false, serverId: null })}
        onConfirm={handleDeleteServer}
        title="Delete MCP Server"
        message={`Delete MCP server "${deleteConfirm.serverId}"? This cannot be undone. Agents and capabilities referencing this server will fail to resolve.`}
        confirmText="Delete"
        variant="danger"
        loading={actionLoading}
      />
    </div>
  );
}
