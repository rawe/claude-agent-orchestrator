import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useSSE } from './SSEContext';
import { useNotification } from './NotificationContext';
import { sessionService } from '@/services';
import type { Session, StreamMessage } from '@/types';

interface SessionsContextValue {
  sessions: Session[];
  loading: boolean;
  stopSession: (sessionId: string) => Promise<{ success: boolean; message: string; run_id?: string }>;
  stopAllSessions: () => Promise<{ stopped: number; failed: number }>;
  deleteSession: (sessionId: string) => Promise<void>;
  deleteAllSessions: () => Promise<{ deleted: number; skipped: number }>;
  refreshSessions: () => Promise<void>;
}

const SessionsContext = createContext<SessionsContextValue | null>(null);

export function SessionsProvider({ children }: { children: ReactNode }) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const { subscribe } = useSSE();
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

  // Subscribe to SSE updates - this runs at app level, always active
  useEffect(() => {
    const handleMessage = (message: StreamMessage) => {
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
        if (event.event_type === 'run_start') {
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
        } else if (event.event_type === 'run_completed') {
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

  const stopAllSessions = useCallback(async () => {
    const stoppable = sessions.filter((s) => s.status === 'running' || s.status === 'idle');
    let stopped = 0;
    let failed = 0;
    for (const session of stoppable) {
      const result = await sessionService.stopSession(session.session_id);
      if (result.success) stopped++;
      else failed++;
    }
    return { stopped, failed };
  }, [sessions]);

  const deleteAllSessions = useCallback(async () => {
    const deletable = sessions.filter(
      (s) => s.status !== 'running' && s.status !== 'idle' && s.status !== 'stopping'
    );
    let deleted = 0;
    let skipped = sessions.length - deletable.length;
    for (const session of deletable) {
      try {
        await sessionService.deleteSession(session.session_id);
        setSessions((prev) => prev.filter((s) => s.session_id !== session.session_id));
        deleted++;
      } catch {
        skipped++;
      }
    }
    return { deleted, skipped };
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
        stopAllSessions,
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
