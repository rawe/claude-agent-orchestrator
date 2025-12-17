import { agentOrchestratorApi } from './api';
import type { Runner } from '@/types';

interface RunnersResponse {
  runners: Runner[];
}

interface DeregisterResponse {
  ok: boolean;
  message: string;
  initiated_by: 'self' | 'external';
}

export const runnerService = {
  /**
   * Get all registered runners
   */
  async getRunners(): Promise<Runner[]> {
    const response = await agentOrchestratorApi.get<RunnersResponse>('/runners');
    return response.data.runners;
  },

  /**
   * Deregister a runner (external request)
   * The runner will be signaled on its next poll and then shut down.
   */
  async deregisterRunner(runnerId: string): Promise<DeregisterResponse> {
    const response = await agentOrchestratorApi.delete<DeregisterResponse>(`/runners/${runnerId}`);
    return response.data;
  },
};
