import { useState, useEffect, useCallback } from 'react';
import { useNotification } from '@/contexts';
import { mcpServerService } from '@/services/mcpServerService';
import type {
  MCPServerRegistryEntry,
  MCPServerRegistryCreate,
  MCPServerRegistryUpdate,
} from '@/types/mcpServer';

export function useMcpServers() {
  const [mcpServers, setMcpServers] = useState<MCPServerRegistryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const { showError } = useNotification();

  const fetchMcpServers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await mcpServerService.getMcpServers();
      setMcpServers(data);
    } catch (err) {
      showError('Failed to load MCP servers');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [showError]);

  useEffect(() => {
    fetchMcpServers();
  }, [fetchMcpServers]);

  const getMcpServer = useCallback(async (id: string): Promise<MCPServerRegistryEntry> => {
    return mcpServerService.getMcpServer(id);
  }, []);

  const createMcpServer = useCallback(async (data: MCPServerRegistryCreate): Promise<MCPServerRegistryEntry> => {
    const newServer = await mcpServerService.createMcpServer(data);
    // Refetch to update the list
    await fetchMcpServers();
    return newServer;
  }, [fetchMcpServers]);

  const updateMcpServer = useCallback(async (id: string, data: MCPServerRegistryUpdate): Promise<MCPServerRegistryEntry> => {
    const updated = await mcpServerService.updateMcpServer(id, data);
    // Refetch to update the list
    await fetchMcpServers();
    return updated;
  }, [fetchMcpServers]);

  const deleteMcpServer = useCallback(async (id: string) => {
    await mcpServerService.deleteMcpServer(id);
    setMcpServers((prev) => prev.filter((s) => s.id !== id));
  }, []);

  const checkIdAvailable = useCallback(async (id: string) => {
    return mcpServerService.checkIdAvailable(id);
  }, []);

  return {
    mcpServers,
    loading,
    getMcpServer,
    createMcpServer,
    updateMcpServer,
    deleteMcpServer,
    checkIdAvailable,
    refetch: fetchMcpServers,
  };
}
