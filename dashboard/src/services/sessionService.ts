import axios from 'axios';
import { agentOrchestratorApi } from './api';
import type { Session, SessionMetadataUpdate, SessionEvent, SessionResult } from '@/types';

interface StopSessionResponse {
  ok: boolean;
  session_id: string;
  run_id: string;
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
    const response = await agentOrchestratorApi.get<{ events: SessionEvent[] }>(`/sessions/${sessionId}/events`);
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
  async stopSession(sessionId: string): Promise<{ success: boolean; message: string; run_id?: string }> {
    try {
      const response = await agentOrchestratorApi.post<StopSessionResponse>(`/sessions/${sessionId}/stop`);
      return {
        success: response.data.ok,
        message: `Session stop initiated`,
        run_id: response.data.run_id,
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

  /**
   * Get structured result from a finished session
   */
  async getSessionResult(sessionId: string): Promise<SessionResult> {
    const response = await agentOrchestratorApi.get<SessionResult>(`/sessions/${sessionId}/result`);
    return response.data;
  },
};
