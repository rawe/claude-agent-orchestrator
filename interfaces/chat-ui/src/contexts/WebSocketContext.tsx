import { createContext, useContext, useEffect, useRef, useState, useCallback, type ReactNode } from 'react';
import { config } from '../config';
import type { WebSocketMessage } from '../types';

type MessageHandler = (message: WebSocketMessage) => void;

interface WebSocketContextValue {
  connected: boolean;
  subscribe: (handler: MessageHandler) => () => void;
  reconnect: () => void;
}

const WebSocketContext = createContext<WebSocketContextValue | null>(null);

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const subscribersRef = useRef<Set<MessageHandler>>(new Set());
  const reconnectAttemptRef = useRef(0);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    // Don't connect if unmounted
    if (!mountedRef.current) return;

    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    try {
      console.log('[WebSocket] Connecting to', config.wsUrl);
      const ws = new WebSocket(config.wsUrl);

      ws.onopen = () => {
        if (!mountedRef.current) {
          ws.close();
          return;
        }
        console.log('[WebSocket] Connected to', config.wsUrl);
        setConnected(true);
        reconnectAttemptRef.current = 0;
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          // Notify all subscribers
          subscribersRef.current.forEach((handler) => {
            try {
              handler(message);
            } catch (err) {
              console.error('[WebSocket] Handler error:', err);
            }
          });
        } catch (err) {
          console.error('[WebSocket] Failed to parse message:', err);
        }
      };

      ws.onclose = (event) => {
        console.log('[WebSocket] Disconnected:', event.code, event.reason);
        setConnected(false);
        wsRef.current = null;

        // Only reconnect if still mounted
        if (!mountedRef.current) return;

        // Schedule reconnection with exponential backoff
        const delay = config.wsReconnectDelays[
          Math.min(reconnectAttemptRef.current, config.wsReconnectDelays.length - 1)
        ];
        reconnectAttemptRef.current++;

        console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptRef.current})`);
        reconnectTimeoutRef.current = window.setTimeout(connect, delay);
      };

      ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('[WebSocket] Failed to connect:', err);
    }
  }, []);

  const reconnect = useCallback(() => {
    reconnectAttemptRef.current = 0;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    connect();
  }, [connect]);

  const subscribe = useCallback((handler: MessageHandler) => {
    subscribersRef.current.add(handler);
    return () => {
      subscribersRef.current.delete(handler);
    };
  }, []);

  // Connect on mount
  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return (
    <WebSocketContext.Provider value={{ connected, subscribe, reconnect }}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket() {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
}
