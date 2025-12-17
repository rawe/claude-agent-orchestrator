import { agentOrchestratorApi } from './api';
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
  run_id: string;
  status: string;
}

export interface SessionResumeRequest {
  prompt: string;
  async_mode: boolean;
}

// Run API request types
interface CreateRunRequest {
  type: 'start_session' | 'resume_session';
  session_name: string;
  agent_name?: string;
  prompt: string;
  project_dir?: string;
}

interface CreateRunResponse {
  run_id: string;
  status: string;
}

export const chatService = {
  /**
   * List available agent blueprints.
   * Returns all active agents without filtering.
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
   * Start a new agent session via Run API
   *
   * Creates a run that the Agent Runner will pick up and execute.
   * Session updates come through WebSocket.
   */
  async startSession(request: SessionStartRequest): Promise<SessionStartResponse> {
    const runRequest: CreateRunRequest = {
      type: 'start_session',
      session_name: request.session_name,
      prompt: request.prompt,
      ...(request.agent_blueprint_name && { agent_name: request.agent_blueprint_name }),
      ...(request.project_dir && { project_dir: request.project_dir }),
    };

    const response = await agentOrchestratorApi.post<CreateRunResponse>('/runs', runRequest);
    return {
      run_id: response.data.run_id,
      status: response.data.status,
    };
  },

  /**
   * Resume an existing session with a new prompt via Run API
   *
   * Creates a resume run that the Agent Runner will pick up and execute.
   * Session updates come through WebSocket.
   */
  async resumeSession(sessionName: string, request: SessionResumeRequest): Promise<SessionStartResponse> {
    const runRequest: CreateRunRequest = {
      type: 'resume_session',
      session_name: sessionName,
      prompt: request.prompt,
    };

    const response = await agentOrchestratorApi.post<CreateRunResponse>('/runs', runRequest);
    return {
      run_id: response.data.run_id,
      status: response.data.status,
    };
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
