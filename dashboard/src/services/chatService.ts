import { agentOrchestratorApi } from './api';

export interface Blueprint {
  name: string;
  description: string;
}

export interface BlueprintListResponse {
  total: number;
  blueprints: Blueprint[];
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
   * List all available agent blueprints
   */
  async listBlueprints(): Promise<BlueprintListResponse> {
    const response = await agentOrchestratorApi.get<BlueprintListResponse>('/api/blueprints');
    return response.data;
  },

  /**
   * Start a new agent session
   */
  async startSession(request: SessionStartRequest): Promise<SessionStartResponse> {
    const response = await agentOrchestratorApi.post<SessionStartResponse>('/api/sessions', request);
    return response.data;
  },

  /**
   * Resume an existing session with a new prompt
   */
  async resumeSession(sessionName: string, request: SessionResumeRequest): Promise<SessionStartResponse> {
    const response = await agentOrchestratorApi.post<SessionStartResponse>(
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
