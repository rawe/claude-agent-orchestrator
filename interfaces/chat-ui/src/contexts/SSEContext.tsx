/**
 * SSE Context for Chat UI
 *
 * Replaces WebSocketContext with Server-Sent Events (ADR-013).
 * Provides the same subscribe/connected API for seamless migration.
 */

import { createContext, useContext, useEffect, useState, useCallback, useRef, type ReactNode } from 'react';
import { config } from '../config';
import { fetchAccessToken, isOidcConfigured } from '../services/auth';
import type { StreamMessage } from '../types';

type MessageHandler = (message: StreamMessage) => void;

interface SSEContextValue {
  connected: boolean;
  subscribe: (handler: MessageHandler) => () => void;
  reconnect: () => void;
}

const SSEContext = createContext<SSEContextValue | null>(null);

/**
 * SSE Event Types from the server (ADR-013)
 */
const SSE_EVENT_TYPES = [
  'init',
  'session_created',
  'session_updated',
  'session_deleted',
  'event',
  'run_failed',
] as const;

/**
 * Build SSE URL with authentication token.
 * EventSource doesn't support custom headers, so token is passed as query param.
 */
async function buildSSEUrl(): Promise<string> {
  const baseUrl = `${config.apiUrl}/sse/sessions`;

  // Try OIDC token first
  if (isOidcConfigured()) {
    const token = await fetchAccessToken();
    if (token) {
      return `${baseUrl}?api_key=${encodeURIComponent(token)}`;
    }
  }

  // Fall back to static API key
  if (config.apiKey) {
    return `${baseUrl}?api_key=${encodeURIComponent(config.apiKey)}`;
  }

  return baseUrl;
}

export function SSEProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const subscribersRef = useRef<Set<MessageHandler>>(new Set());

  const connect = useCallback(async () => {
    // Close existing connection if any
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    // Build URL with current auth token
    const sseUrl = await buildSSEUrl();
    console.log('[SSE] Connecting to', sseUrl.replace(/api_key=[^&]+/, 'api_key=***'));

    const eventSource = new EventSource(sseUrl);

    eventSource.onopen = () => {
      console.log('[SSE] Connected');
      setConnected(true);
    };

    eventSource.onerror = (error) => {
      console.error('[SSE] Error', error);
      setConnected(false);
      // EventSource automatically reconnects
    };

    // Register handlers for each event type
    SSE_EVENT_TYPES.forEach((eventType) => {
      eventSource.addEventListener(eventType, (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);

          // Convert SSE event to StreamMessage format
          const message: StreamMessage = {
            type: eventType,
            ...data,
          };

          // Notify all subscribers
          subscribersRef.current.forEach((handler) => {
            try {
              handler(message);
            } catch (err) {
              console.error('[SSE] Handler error:', err);
            }
          });
        } catch (err) {
          console.error('[SSE] Failed to parse message:', err);
        }
      });
    });

    eventSourceRef.current = eventSource;
  }, []);

  const reconnect = useCallback(() => {
    connect();
  }, [connect]);

  const subscribe = useCallback((handler: MessageHandler) => {
    subscribersRef.current.add(handler);
    return () => {
      subscribersRef.current.delete(handler);
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [connect]);

  return (
    <SSEContext.Provider value={{ connected, subscribe, reconnect }}>
      {children}
    </SSEContext.Provider>
  );
}

export function useSSE() {
  const context = useContext(SSEContext);
  if (!context) {
    throw new Error('useSSE must be used within an SSEProvider');
  }
  return context;
}
