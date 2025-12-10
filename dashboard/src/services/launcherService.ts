import { agentOrchestratorApi } from './api';
import type { Launcher } from '@/types';

interface LaunchersResponse {
  launchers: Launcher[];
}

export const launcherService = {
  /**
   * Get all registered launchers
   */
  async getLaunchers(): Promise<Launcher[]> {
    const response = await agentOrchestratorApi.get<LaunchersResponse>('/launchers');
    return response.data.launchers;
  },
};
