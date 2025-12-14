import axios, { AxiosError } from 'axios';
import { config } from '../config';
import type { JobRequest, JobResponse } from '../types';

// Create axios instance
const api = axios.create({
  baseURL: config.apiUrl,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Error handler
function handleError(error: unknown): never {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string; message?: string }>;
    const message = axiosError.response?.data?.detail
      || axiosError.response?.data?.message
      || axiosError.message
      || 'An error occurred';
    throw new Error(message);
  }
  throw error;
}

// Generate unique session name
function generateSessionName(): string {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(2, 8);
  return `chat-${timestamp}-${random}`;
}

/**
 * Chat API Service
 * See: docs/agent-runtime/API.md
 */
export const chatService = {
  /**
   * Start a new chat session (POST /jobs)
   */
  async startSession(prompt: string): Promise<{ jobId: string; sessionName: string }> {
    const sessionName = generateSessionName();

    const request: JobRequest = {
      type: 'start_session',
      session_name: sessionName,
      prompt,
      agent_name: config.agentBlueprint,
    };

    try {
      const response = await api.post<JobResponse>('/jobs', request);
      return {
        jobId: response.data.job_id,
        sessionName,
      };
    } catch (error) {
      handleError(error);
    }
  },

  /**
   * Resume an existing session (POST /jobs)
   */
  async resumeSession(sessionName: string, prompt: string): Promise<{ jobId: string }> {
    const request: JobRequest = {
      type: 'resume_session',
      session_name: sessionName,
      prompt,
    };

    try {
      const response = await api.post<JobResponse>('/jobs', request);
      return {
        jobId: response.data.job_id,
      };
    } catch (error) {
      handleError(error);
    }
  },

  /**
   * Stop a running session (POST /sessions/{session_id}/stop)
   */
  async stopSession(sessionId: string): Promise<void> {
    try {
      await api.post(`/sessions/${sessionId}/stop`);
    } catch (error) {
      handleError(error);
    }
  },
};
