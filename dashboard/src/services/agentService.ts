import { agentOrchestratorApi } from './api';
import type { Agent, AgentCreate, AgentUpdate, AgentStatus } from '@/types';

export type VisibilityContext = 'external' | 'internal';

export const agentService = {
  /**
   * Get all agents, optionally filtered by visibility context
   * @param context - Optional visibility context filter:
   *   - undefined: Returns all agents (for management UI)
   *   - 'external': Returns public + all visibility agents (for end users)
   *   - 'internal': Returns internal + all visibility agents (for orchestrator)
   */
  async getAgents(context?: VisibilityContext): Promise<Agent[]> {
    const params = context ? `?context=${context}` : '';
    const response = await agentOrchestratorApi.get<Agent[]>(`/agents${params}`);
    return response.data;
  },

  /**
   * Get a single agent by name
   */
  async getAgent(name: string): Promise<Agent> {
    const response = await agentOrchestratorApi.get<Agent>(`/agents/${name}`);
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
