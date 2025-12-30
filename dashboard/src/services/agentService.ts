import { agentOrchestratorApi } from './api';
import type { Agent, AgentCreate, AgentUpdate, AgentStatus } from '@/types';

export const agentService = {
  /**
   * Get all agents, optionally filtered by tags
   * @param tags - Optional comma-separated tags filter:
   *   - undefined: Returns all agents (for management UI)
   *   - 'external': Returns agents with 'external' tag (for end users)
   *   - 'internal': Returns agents with 'internal' tag (for orchestrator)
   *   - 'foo,bar': Returns agents with BOTH 'foo' AND 'bar' tags
   */
  async getAgents(tags?: string): Promise<Agent[]> {
    const params = tags ? `?tags=${encodeURIComponent(tags)}` : '';
    const response = await agentOrchestratorApi.get<Agent[]>(`/agents${params}`);
    return response.data;
  },

  /**
   * Get a single agent by name (with capabilities resolved)
   */
  async getAgent(name: string): Promise<Agent> {
    const response = await agentOrchestratorApi.get<Agent>(`/agents/${name}`);
    return response.data;
  },

  /**
   * Get a single agent by name without capability resolution.
   * Use this for editing to get the raw agent data (unmerged system_prompt and mcp_servers).
   */
  async getAgentRaw(name: string): Promise<Agent> {
    const response = await agentOrchestratorApi.get<Agent>(`/agents/${name}?raw=true`);
    return response.data;
  },

  /**
   * Create a new agent
   */
  async createAgent(data: AgentCreate): Promise<Agent> {
    const response = await agentOrchestratorApi.post<Agent>('/agents', data);
    return response.data;
  },

  /**
   * Update an existing agent
   */
  async updateAgent(name: string, data: AgentUpdate): Promise<Agent> {
    const response = await agentOrchestratorApi.patch<Agent>(`/agents/${name}`, data);
    return response.data;
  },

  /**
   * Delete an agent
   */
  async deleteAgent(name: string): Promise<void> {
    await agentOrchestratorApi.delete(`/agents/${name}`);
  },

  /**
   * Update agent status (activate/deactivate)
   */
  async updateAgentStatus(name: string, status: AgentStatus): Promise<Agent> {
    const response = await agentOrchestratorApi.patch<Agent>(`/agents/${name}/status`, { status });
    return response.data;
  },

  /**
   * Check if agent name is available
   */
  async checkNameAvailable(name: string): Promise<boolean> {
    try {
      await agentOrchestratorApi.get(`/agents/${name}`);
      return false; // Agent exists
    } catch {
      return true; // 404 = name available
    }
  },
};
