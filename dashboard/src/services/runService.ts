import { agentOrchestratorApi } from './api';
import type { Run, StopRunResponse } from '@/types';

interface RunsResponse {
  runs: Run[];
}

export const runService = {
  /**
   * Get all runs in the queue
   */
  async getRuns(): Promise<Run[]> {
    const response = await agentOrchestratorApi.get<RunsResponse>('/runs');
    return response.data.runs;
  },

  /**
   * Get a single run by ID
   */
  async getRun(runId: string): Promise<Run> {
    const response = await agentOrchestratorApi.get<Run>(`/runs/${runId}`);
    return response.data;
  },

  /**
   * Stop a running run
   */
  async stopRun(runId: string): Promise<StopRunResponse> {
    const response = await agentOrchestratorApi.post<StopRunResponse>(`/runs/${runId}/stop`);
    return response.data;
  },
};
