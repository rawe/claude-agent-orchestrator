import { agentOrchestratorApi } from './api';
import type {
  MCPServerRegistryEntry,
  MCPServerRegistryCreate,
  MCPServerRegistryUpdate,
} from '@/types/mcpServer';

export const mcpServerService = {
  /**
   * Get all MCP servers from the registry
   */
  async getMcpServers(): Promise<MCPServerRegistryEntry[]> {
    const response = await agentOrchestratorApi.get<MCPServerRegistryEntry[]>('/mcp-servers');
    return response.data;
  },

  /**
   * Get a single MCP server by ID
   */
  async getMcpServer(id: string): Promise<MCPServerRegistryEntry> {
    const response = await agentOrchestratorApi.get<MCPServerRegistryEntry>(`/mcp-servers/${id}`);
    return response.data;
  },

  /**
   * Create a new MCP server registry entry
   */
  async createMcpServer(data: MCPServerRegistryCreate): Promise<MCPServerRegistryEntry> {
    const response = await agentOrchestratorApi.post<MCPServerRegistryEntry>('/mcp-servers', data);
    return response.data;
  },

  /**
   * Update an existing MCP server registry entry
   */
  async updateMcpServer(id: string, data: MCPServerRegistryUpdate): Promise<MCPServerRegistryEntry> {
    const response = await agentOrchestratorApi.put<MCPServerRegistryEntry>(`/mcp-servers/${id}`, data);
    return response.data;
  },

  /**
   * Delete an MCP server from the registry
   */
  async deleteMcpServer(id: string): Promise<void> {
    await agentOrchestratorApi.delete(`/mcp-servers/${id}`);
  },

  /**
   * Check if MCP server ID is available
   */
  async checkIdAvailable(id: string): Promise<boolean> {
    try {
      await agentOrchestratorApi.get(`/mcp-servers/${id}`);
      return false; // Server exists
    } catch {
      return true; // 404 = ID available
    }
  },
};
