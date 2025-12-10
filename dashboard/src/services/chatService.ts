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
  job_id: string;
  status: string;
}

export interface SessionResumeRequest {
  prompt: string;
  async_mode: boolean;
}

// Job API request types
interface CreateJobRequest {
  type: 'start_session' | 'resume_session';
  session_name: string;
  agent_name?: string;
  prompt: string;
  project_dir?: string;
}

interface CreateJobResponse {
  job_id: string;
  status: string;
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
   * Start a new agent session via Job API
   *
   * Creates a job that the Agent Launcher will pick up and execute.
   * Session updates come through WebSocket.
   */
  async startSession(request: SessionStartRequest): Promise<SessionStartResponse> {
    const jobRequest: CreateJobRequest = {
      type: 'start_session',
      session_name: request.session_name,
      prompt: request.prompt,
      ...(request.agent_blueprint_name && { agent_name: request.agent_blueprint_name }),
      ...(request.project_dir && { project_dir: request.project_dir }),
    };

    const response = await agentOrchestratorApi.post<CreateJobResponse>('/jobs', jobRequest);
    return {
      job_id: response.data.job_id,
      status: response.data.status,
    };
  },

  /**
   * Resume an existing session with a new prompt via Job API
   *
   * Creates a resume job that the Agent Launcher will pick up and execute.
   * Session updates come through WebSocket.
   */
  async resumeSession(sessionName: string, request: SessionResumeRequest): Promise<SessionStartResponse> {
    const jobRequest: CreateJobRequest = {
      type: 'resume_session',
      session_name: sessionName,
      prompt: request.prompt,
    };

    const response = await agentOrchestratorApi.post<CreateJobResponse>('/jobs', jobRequest);
    return {
      job_id: response.data.job_id,
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
