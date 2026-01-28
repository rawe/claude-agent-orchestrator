/**
 * Hook for unified session-run view data
 *
 * Provides unified data combining sessions, runs, and events
 * with computed fields and helper methods for all view approaches.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSSE, useNotification } from '@/contexts';
import {
  unifiedViewService,
  type UnifiedViewData,
  type SessionTreeNode,
  type UnifiedSession,
  type UnifiedRun,
  type UnifiedEvent,
  isRunActive,
} from '@/services';
import type { StreamMessage } from '@/types';

interface UseUnifiedViewResult {
  /** All sessions with computed fields */
  sessions: UnifiedSession[];
  /** All runs with computed fields */
  runs: UnifiedRun[];
  /** Map of sessionId -> runs for quick lookup */
  runsBySession: Map<string, UnifiedRun[]>;
  /** Map of sessionId -> session for quick lookup */
  sessionsById: Map<string, UnifiedSession>;
  /** Hierarchical tree of sessions with runs */
  sessionTree: SessionTreeNode[];
  /** Loading state */
  loading: boolean;
  /** Error message if any */
  error: string | null;
  /** Refresh data */
  refresh: () => Promise<void>;
  /** Get events for a session (fetches on demand) */
  getSessionEvents: (sessionId: string) => Promise<UnifiedEvent[]>;
  /** Computed statistics */
  stats: UnifiedViewStats;
}

interface UnifiedViewStats {
  totalSessions: number;
  totalRuns: number;
  activeSessions: number;
  activeRuns: number;
  rootSessions: number;
}

export function useUnifiedView(): UseUnifiedViewResult {
  const [data, setData] = useState<UnifiedViewData>({
    sessions: [],
    runs: [],
    runsBySession: new Map(),
    sessionsById: new Map(),
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { subscribe } = useSSE();
  const { showError } = useNotification();

  // Fetch initial data
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await unifiedViewService.getUnifiedData();
      setData(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load unified view data';
      setError(message);
      showError(message);
      console.error('useUnifiedView fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [showError]);

  // Initial fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Subscribe to SSE updates for real-time changes
  useEffect(() => {
    const handleMessage = (message: StreamMessage) => {
      // Refresh data on session changes
      if (
        message.type === 'session_created' ||
        message.type === 'session_updated' ||
        message.type === 'session_deleted'
      ) {
        // Re-fetch to get updated computed fields
        fetchData();
      }
    };

    const unsubscribe = subscribe(handleMessage);
    return unsubscribe;
  }, [subscribe, fetchData]);

  // Build session tree
  const sessionTree = useMemo(() => {
    return unifiedViewService.buildSessionTree(data.sessions, data.runsBySession);
  }, [data.sessions, data.runsBySession]);

  // Compute statistics
  const stats = useMemo((): UnifiedViewStats => {
    const activeSessions = data.sessions.filter(
      (s) => s.status === 'running' || s.status === 'stopping'
    ).length;

    const activeRuns = data.runs.filter((r) => isRunActive(r.status)).length;

    const rootSessions = data.sessions.filter((s) => s.parentSessionId === null).length;

    return {
      totalSessions: data.sessions.length,
      totalRuns: data.runs.length,
      activeSessions,
      activeRuns,
      rootSessions,
    };
  }, [data.sessions, data.runs]);

  // Get events for a session (on-demand fetch)
  const getSessionEvents = useCallback(
    async (sessionId: string): Promise<UnifiedEvent[]> => {
      try {
        return await unifiedViewService.getSessionEvents(sessionId);
      } catch (err) {
        console.error('Failed to fetch session events:', err);
        return [];
      }
    },
    []
  );

  return {
    sessions: data.sessions,
    runs: data.runs,
    runsBySession: data.runsBySession,
    sessionsById: data.sessionsById,
    sessionTree,
    loading,
    error,
    refresh: fetchData,
    getSessionEvents,
    stats,
  };
}

/**
 * Hook for a single session's events with real-time updates
 */
export function useUnifiedSessionEvents(sessionId: string | null) {
  const [events, setEvents] = useState<UnifiedEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const { subscribe } = useSSE();
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
        const data = await unifiedViewService.getSessionEvents(sessionId);
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

    const handleMessage = (message: StreamMessage) => {
      if (message.type === 'event' && message.data?.session_id === sessionId) {
        // Re-fetch to get properly adapted events
        unifiedViewService.getSessionEvents(sessionId).then(setEvents).catch(console.error);
      }
    };

    const unsubscribe = subscribe(handleMessage);
    return unsubscribe;
  }, [sessionId, subscribe]);

  return { events, loading };
}
