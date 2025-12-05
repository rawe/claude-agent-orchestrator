import { agentOrchestratorApi, agentControlApi } from './api';
import type { Agent } from '@/types';

export interface BlueprintListResponse {
  total: number;
  blueprints: Agent[];
}

export interface SessionStartRequest {
  session_name: string;
  prompt: string;
  agent_blueprint_name?: string;
  project_dir?: string;
  async_mode: boolean;
}

export interface SessionStartResponse {
  session_name: string;
  status: string;
  message: string;
}

export interface SessionResumeRequest {
  prompt: string;
  async_mode: boolean;
}

export const chatService = {
  /**
   * List all available agent blueprints from agent-runtime
   */
  async listBlueprints(): Promise<BlueprintListResponse> {
    const response = await agentOrchestratorApi.get<Agent[]>('/agents');
    const agents = response.data;
    return {
      total: agents.length,
      blueprints: agents,
    };
  },

  /**
   * Start a new agent session via agent control API
   */
  async startSession(request: SessionStartRequest): Promise<SessionStartResponse> {
    const response = await agentControlApi.post<SessionStartResponse>('/api/sessions', request);
    return response.data;
  },

  /**
   * Resume an existing session with a new prompt via agent control API
   */
  async resumeSession(sessionName: string, request: SessionResumeRequest): Promise<SessionStartResponse> {
    const response = await agentControlApi.post<SessionStartResponse>(
      `/api/sessions/${sessionName}/resume`,
      request
    );
    return response.data;
  },

  /**
   * Generate a unique session name
   */
  generateSessionName(): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 8);
    return `chat-${timestamp}-${random}`;
  },
};
