import { agentOrchestratorApi } from './api';
import type { Session, SessionMetadataUpdate, SessionEvent } from '@/types';

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
   * NOTE: This endpoint is not yet implemented in the backend
   * Will return a mock response for now
   */
  async stopSession(sessionId: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await agentOrchestratorApi.post(`/sessions/${sessionId}/stop`);
      return response.data;
    } catch {
      // Mock response until backend is implemented
      console.warn('Stop session endpoint not implemented, returning mock response');
      return {
        success: false,
        message: 'Stop session feature is not yet implemented in the backend',
      };
    }
  },
};
