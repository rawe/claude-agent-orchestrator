import { agentOrchestratorApi } from './api';
import type { Script, ScriptSummary, ScriptCreate, ScriptUpdate } from '@/types/script';

export const scriptService = {
  /**
   * Get all scripts
   */
  async getScripts(): Promise<ScriptSummary[]> {
    const response = await agentOrchestratorApi.get<ScriptSummary[]>('/scripts');
    return response.data;
  },

  /**
   * Get a single script by name
   */
  async getScript(name: string): Promise<Script> {
    const response = await agentOrchestratorApi.get<Script>(`/scripts/${name}`);
    return response.data;
  },

  /**
   * Create a new script
   */
  async createScript(data: ScriptCreate): Promise<Script> {
    const response = await agentOrchestratorApi.post<Script>('/scripts', data);
    return response.data;
  },

  /**
   * Update an existing script
   */
  async updateScript(name: string, data: ScriptUpdate): Promise<Script> {
    const response = await agentOrchestratorApi.patch<Script>(`/scripts/${name}`, data);
    return response.data;
  },

  /**
   * Delete a script
   */
  async deleteScript(name: string): Promise<void> {
    await agentOrchestratorApi.delete(`/scripts/${name}`);
  },

  /**
   * Check if script name is available
   */
  async checkNameAvailable(name: string): Promise<boolean> {
    try {
      await agentOrchestratorApi.get(`/scripts/${name}`);
      return false; // Script exists
    } catch {
      return true; // 404 = name available
    }
  },
};
