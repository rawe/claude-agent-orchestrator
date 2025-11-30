import { agentRegistryApi } from './api';
import type { Agent, AgentCreate, AgentUpdate, AgentStatus } from '@/types';

export const agentService = {
  /**
   * Get all agents
   */
  async getAgents(): Promise<Agent[]> {
    const response = await agentRegistryApi.get<Agent[]>('/agents');
    return response.data;
  },

  /**
   * Get a single agent by name
   */
  async getAgent(name: string): Promise<Agent> {
    const response = await agentRegistryApi.get<Agent>(`/agents/${name}`);
    return response.data;
  },

  /**
   * Create a new agent
   */
  async createAgent(data: AgentCreate): Promise<Agent> {
    const response = await agentRegistryApi.post<Agent>('/agents', data);
    return response.data;
  },

  /**
   * Update an existing agent
   */
  async updateAgent(name: string, data: AgentUpdate): Promise<Agent> {
    const response = await agentRegistryApi.patch<Agent>(`/agents/${name}`, data);
    return response.data;
  },

  /**
   * Delete an agent
   */
  async deleteAgent(name: string): Promise<void> {
    await agentRegistryApi.delete(`/agents/${name}`);
  },

  /**
   * Update agent status (activate/deactivate)
   */
  async updateAgentStatus(name: string, status: AgentStatus): Promise<Agent> {
    const response = await agentRegistryApi.patch<Agent>(`/agents/${name}/status`, { status });
    return response.data;
  },

  /**
   * Check if agent name is available
   */
  async checkNameAvailable(name: string): Promise<boolean> {
    try {
      await agentRegistryApi.get(`/agents/${name}`);
      return false; // Agent exists
    } catch {
      return true; // 404 = name available
    }
  },
};
