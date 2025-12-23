/**
 * SSE Context for Agent Orchestrator Dashboard
 *
 * Replaces WebSocketContext with Server-Sent Events (ADR-013).
 * Provides the same subscribe/connected API for seamless migration.
 *
 * Benefits over WebSocket:
 * - Standard HTTP authentication (cookies, headers)
 * - Automatic reconnection via EventSource
 * - Built-in resume support via Last-Event-ID
 */

import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { AGENT_ORCHESTRATOR_API_URL } from '@/utils/constants';
import { fetchAccessToken, isOidcConfigured } from '@/services/auth';
import type { StreamMessage } from '@/types';

interface SSEContextValue {
  connected: boolean;
  subscribe: (callback: (message: StreamMessage) => void) => () => void;
  reconnect: () => void;
}

const SSEContext = createContext<SSEContextValue | null>(null);

/**
 * SSE Event Types from the server (ADR-013)
 * These map to StreamMessage.type for backwards compatibility
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
  const baseUrl = `${AGENT_ORCHESTRATOR_API_URL}/sse/sessions`;

  // Add OIDC token if configured
  if (isOidcConfigured()) {
    const token = await fetchAccessToken();
    if (token) {
      return `${baseUrl}?api_key=${encodeURIComponent(token)}`;
    }
  }

  // When OIDC is not configured, connect without auth
  // (for local development with AUTH_ENABLED=false on coordinator)
  return baseUrl;
}

export function SSEProvider({ children }: { children: React.ReactNode }) {
  const [connected, setConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const subscribersRef = useRef<Set<(message: StreamMessage) => void>>(new Set());

  const connect = useCallback(async () => {
    // Close existing connection if any
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    // Build URL with current auth token
    const sseUrl = await buildSSEUrl();
    console.log('SSE: Connecting to', sseUrl.replace(/api_key=[^&]+/, 'api_key=***'));

    const eventSource = new EventSource(sseUrl);

    eventSource.onopen = () => {
      console.log('SSE: Connected');
      setConnected(true);
    };

    eventSource.onerror = (error) => {
      console.error('SSE: Error', error);
      setConnected(false);
      // EventSource automatically reconnects, no manual handling needed
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
          subscribersRef.current.forEach((callback) => callback(message));
        } catch (err) {
          console.error('SSE: Failed to parse message', err);
        }
      });
    });

    eventSourceRef.current = eventSource;
  }, []);

  const reconnect = useCallback(() => {
    // Force reconnection by closing and reopening
    connect();
  }, [connect]);

  const subscribe = useCallback((callback: (message: StreamMessage) => void) => {
    subscribersRef.current.add(callback);
    return () => {
      subscribersRef.current.delete(callback);
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

/**
 * Hook to access SSE context
 */
export function useSSE() {
  const context = useContext(SSEContext);
  if (!context) {
    throw new Error('useSSE must be used within an SSEProvider');
  }
  return context;
}
