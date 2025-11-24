import { useState, useEffect, useCallback } from 'react';
import { useWebSocket, useNotification } from '@/contexts';
import { sessionService } from '@/services';
import type { Session, SessionEvent, WebSocketMessage } from '@/types';

export function useSessions() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const { subscribe } = useWebSocket();
  const { showError } = useNotification();

  // Initial fetch
  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const data = await sessionService.getSessions();
        setSessions(data);
      } catch (err) {
        showError('Failed to load sessions');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchSessions();
  }, [showError]);

  // Subscribe to WebSocket updates
  useEffect(() => {
    const handleMessage = (message: WebSocketMessage) => {
      if (message.type === 'init' && message.sessions) {
        setSessions(message.sessions);
      } else if (message.type === 'session_updated' && message.session) {
        setSessions((prev) =>
          prev.map((s) => (s.session_id === message.session!.session_id ? message.session! : s))
        );
      } else if (message.type === 'session_deleted' && message.session_id) {
        setSessions((prev) => prev.filter((s) => s.session_id !== message.session_id));
      } else if (message.type === 'event' && message.data) {
        // Update session status based on events
        const event = message.data;
        if (event.event_type === 'session_start') {
          // Check if session already exists
          setSessions((prev) => {
            const exists = prev.some((s) => s.session_id === event.session_id);
            if (exists) {
              return prev.map((s) =>
                s.session_id === event.session_id ? { ...s, status: 'running' as const } : s
              );
            }
            // Add new session
            return [
              {
                session_id: event.session_id,
                status: 'running',
                created_at: event.timestamp,
              },
              ...prev,
            ];
          });
        } else if (event.event_type === 'session_stop') {
          setSessions((prev) =>
            prev.map((s) =>
              s.session_id === event.session_id
                ? { ...s, status: event.exit_code === 0 ? 'finished' : 'stopped' }
                : s
            )
          );
        }
      }
    };

    const unsubscribe = subscribe(handleMessage);
    return unsubscribe;
  }, [subscribe]);

  const stopSession = useCallback(async (sessionId: string) => {
    const result = await sessionService.stopSession(sessionId);
    return result;
  }, []);

  const deleteSession = useCallback(
    async (sessionId: string) => {
      await sessionService.deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
    },
    []
  );

  return {
    sessions,
    loading,
    stopSession,
    deleteSession,
  };
}

export function useSessionEvents(sessionId: string | null) {
  const [events, setEvents] = useState<SessionEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const { subscribe } = useWebSocket();
  const { showError } = useNotification();

  // Fetch events when session changes
  useEffect(() => {
    if (!sessionId) {
      setEvents([]);
      return;
    }

    const fetchEvents = async () => {
      setLoading(true);
      try {
        const data = await sessionService.getSessionEvents(sessionId);
        setEvents(data);
      } catch (err) {
        showError('Failed to load session events');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchEvents();
  }, [sessionId, showError]);

  // Subscribe to new events for this session
  useEffect(() => {
    if (!sessionId) return;

    const handleMessage = (message: WebSocketMessage) => {
      if (message.type === 'event' && message.data?.session_id === sessionId) {
        setEvents((prev) => [...prev, message.data!]);
      }
    };

    const unsubscribe = subscribe(handleMessage);
    return unsubscribe;
  }, [sessionId, subscribe]);

  return { events, loading };
}
