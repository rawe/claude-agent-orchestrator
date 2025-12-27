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
import { fetchAccessToken, isOidcConfigured, waitForTokenReady } from '@/services/auth';
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
    // Wait for Auth0 to set up the token getter (fixes race condition on mount)
    await waitForTokenReady();

    const token = await fetchAccessToken();
    if (token) {
      return `${baseUrl}?api_key=${encodeURIComponent(token)}`;
    }
    // Token getter is ready but token fetch failed - log warning
    console.warn('SSE: Token getter ready but fetchAccessToken returned null');
  }

  // When OIDC is not configured, connect without auth
  // (for local development with AUTH_ENABLED=false on coordinator)
  return baseUrl;
}

// Reconnection configuration
const RECONNECT_BASE_DELAY_MS = 1000;
const RECONNECT_MAX_DELAY_MS = 30000;
const RECONNECT_MAX_ATTEMPTS = 10;

export function SSEProvider({ children }: { children: React.ReactNode }) {
  const [connected, setConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const subscribersRef = useRef<Set<(message: StreamMessage) => void>>(new Set());
  const reconnectAttemptRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Ref to hold connect function for use in scheduleReconnect (avoids circular dependency)
  const connectRef = useRef<() => void>(() => {});

  const scheduleReconnect = useCallback(() => {
    // Clear any existing reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Check if we've exceeded max attempts
    if (reconnectAttemptRef.current >= RECONNECT_MAX_ATTEMPTS) {
      console.error(`SSE: Max reconnection attempts (${RECONNECT_MAX_ATTEMPTS}) reached. Manual reconnect required.`);
      return;
    }

    // Calculate delay with exponential backoff
    const delay = Math.min(
      RECONNECT_BASE_DELAY_MS * Math.pow(2, reconnectAttemptRef.current),
      RECONNECT_MAX_DELAY_MS
    );
    reconnectAttemptRef.current += 1;

    console.log(`SSE: Reconnecting in ${delay}ms (attempt ${reconnectAttemptRef.current}/${RECONNECT_MAX_ATTEMPTS})`);

    reconnectTimeoutRef.current = setTimeout(() => {
      connectRef.current();
    }, delay);
  }, []);

  const connect = useCallback(async () => {
    // Clear any pending reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

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
      // Reset reconnection attempts on successful connection
      reconnectAttemptRef.current = 0;
    };

    eventSource.onerror = () => {
      console.error('SSE: Connection error');
      setConnected(false);

      // Close the EventSource to prevent its built-in reconnect (which would use stale token)
      eventSource.close();
      eventSourceRef.current = null;

      // Schedule manual reconnect with fresh token
      scheduleReconnect();
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
  }, [scheduleReconnect]);

  // Keep connectRef in sync with connect function
  connectRef.current = connect;

  const reconnect = useCallback(() => {
    // Reset attempt counter for manual reconnect
    reconnectAttemptRef.current = 0;
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
      // Clear any pending reconnect timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      // Close the EventSource
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
