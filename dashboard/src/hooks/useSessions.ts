import { useState, useEffect } from 'react';
import { useSSE, useNotification } from '@/contexts';
import { sessionService } from '@/services';
import { getEventKey } from '@/utils';
import type { SessionEvent, WebSocketMessage } from '@/types';

// Note: useSessions() is now a context - import from '@/contexts' instead
// This file only exports useSessionEvents which is session-specific

export function useSessionEvents(sessionId: string | null) {
  const [events, setEvents] = useState<SessionEvent[]>([]);
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
        const newEvent = message.data!;
        const newEventKey = getEventKey(newEvent);

        setEvents((prev) => {
          // Check if event already exists to prevent duplicates
          const exists = prev.some((e) => getEventKey(e) === newEventKey);
          if (exists) {
            return prev;
          }
          return [...prev, newEvent];
        });
      }
    };

    const unsubscribe = subscribe(handleMessage);
    return unsubscribe;
  }, [sessionId, subscribe]);

  return { events, loading };
}
