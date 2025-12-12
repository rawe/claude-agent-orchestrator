import axios from 'axios';
import { agentOrchestratorApi } from './api';
import type { Session, SessionMetadataUpdate, SessionEvent } from '@/types';

interface StopSessionResponse {
  ok: boolean;
  session_id: string;
  job_id: string;
  session_name: string;
  status: string;
}

export const sessionService = {
  /**
   * Get all sessions
   */
  async getSessions(): Promise<Session[]> {
    const response = await agentOrchestratorApi.get<{ sessions: Session[] }>('/sessions');
    return response.data.sessions;
  },

  /**
   * Get events for a specific session
   */
  async getSessionEvents(sessionId: string): Promise<SessionEvent[]> {
    const response = await agentOrchestratorApi.get<{ events: SessionEvent[] }>(`/events/${sessionId}`);
    return response.data.events;
  },

  /**
   * Update session metadata
   */
  async updateSessionMetadata(sessionId: string, metadata: SessionMetadataUpdate): Promise<Session> {
    const response = await agentOrchestratorApi.patch<Session>(
      `/sessions/${sessionId}/metadata`,
      metadata
    );
    return response.data;
  },

  /**
   * Delete a session
   */
  async deleteSession(sessionId: string): Promise<void> {
    await agentOrchestratorApi.delete(`/sessions/${sessionId}`);
  },


  /**
   * Stop a running session
   */
  async stopSession(sessionId: string): Promise<{ success: boolean; message: string; job_id?: string }> {
    try {
      const response = await agentOrchestratorApi.post<StopSessionResponse>(`/sessions/${sessionId}/stop`);
      return {
        success: response.data.ok,
        message: `Session stop initiated`,
        job_id: response.data.job_id,
      };
    } catch (error: unknown) {
      if (axios.isAxiosError(error) && error.response) {
        const detail = error.response.data?.detail || 'Failed to stop session';
        return {
          success: false,
          message: detail,
        };
      }
      return {
        success: false,
        message: 'Failed to stop session',
      };
    }
  },
};
