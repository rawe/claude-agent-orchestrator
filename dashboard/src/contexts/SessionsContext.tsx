import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useWebSocket } from './WebSocketContext';
import { useNotification } from './NotificationContext';
import { sessionService } from '@/services';
import type { Session, WebSocketMessage } from '@/types';

interface SessionsContextValue {
  sessions: Session[];
  loading: boolean;
  stopSession: (sessionId: string) => Promise<{ success: boolean; message: string; run_id?: string }>;
  deleteSession: (sessionId: string) => Promise<void>;
  deleteAllSessions: () => Promise<void>;
  refreshSessions: () => Promise<void>;
}

const SessionsContext = createContext<SessionsContextValue | null>(null);

export function SessionsProvider({ children }: { children: ReactNode }) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const { subscribe } = useWebSocket();
  const { showError } = useNotification();

  // Initial fetch
  const fetchSessions = useCallback(async () => {
    try {
      const data = await sessionService.getSessions();
      setSessions(data);
    } catch (err) {
      showError('Failed to load sessions');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [showError]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  // Subscribe to WebSocket updates - this runs at app level, always active
  useEffect(() => {
    const handleMessage = (message: WebSocketMessage) => {
      if (message.type === 'init' && message.sessions) {
        setSessions(message.sessions);
      } else if (message.type === 'session_created' && message.session) {
        // New session created via POST /sessions API
        setSessions((prev) => {
          const exists = prev.some((s) => s.session_id === message.session!.session_id);
          if (exists) return prev;
          return [message.session!, ...prev];
        });
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

  const deleteSession = useCallback(async (sessionId: string) => {
    await sessionService.deleteSession(sessionId);
    setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
  }, []);

  const deleteAllSessions = useCallback(async () => {
    const sessionIds = sessions.map((s) => s.session_id);
    for (const sessionId of sessionIds) {
      await sessionService.deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
    }
  }, [sessions]);

  const refreshSessions = useCallback(async () => {
    setLoading(true);
    await fetchSessions();
  }, [fetchSessions]);

  return (
    <SessionsContext.Provider
      value={{
        sessions,
        loading,
        stopSession,
        deleteSession,
        deleteAllSessions,
        refreshSessions,
      }}
    >
      {children}
    </SessionsContext.Provider>
  );
}

export function useSessions() {
  const context = useContext(SessionsContext);
  if (!context) {
    throw new Error('useSessions must be used within a SessionsProvider');
  }
  return context;
}
