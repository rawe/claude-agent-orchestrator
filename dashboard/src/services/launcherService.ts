import { agentOrchestratorApi } from './api';
import type { Launcher } from '@/types';

interface LaunchersResponse {
  launchers: Launcher[];
}

interface DeregisterResponse {
  ok: boolean;
  message: string;
  initiated_by: 'self' | 'external';
}

export const launcherService = {
  /**
   * Get all registered launchers
   */
  async getLaunchers(): Promise<Launcher[]> {
    const response = await agentOrchestratorApi.get<LaunchersResponse>('/launchers');
    return response.data.launchers;
  },

  /**
   * Deregister a launcher (external request)
   * The launcher will be signaled on its next poll and then shut down.
   */
  async deregisterLauncher(launcherId: string): Promise<DeregisterResponse> {
    const response = await agentOrchestratorApi.delete<DeregisterResponse>(`/launchers/${launcherId}`);
    return response.data;
  },
};
