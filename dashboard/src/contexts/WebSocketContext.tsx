import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { WEBSOCKET_URL, WS_RECONNECT_DELAYS } from '@/utils/constants';
import type { WebSocketMessage } from '@/types';

interface WebSocketContextValue {
  connected: boolean;
  subscribe: (callback: (message: WebSocketMessage) => void) => () => void;
  reconnect: () => void;
}

const WebSocketContext = createContext<WebSocketContextValue | null>(null);

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const subscribersRef = useRef<Set<(message: WebSocketMessage) => void>>(new Set());
  const reconnectAttemptRef = useRef(0);
  const reconnectTimeoutRef = useRef<number | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    console.log('WebSocket: Connecting to', WEBSOCKET_URL);
    const ws = new WebSocket(WEBSOCKET_URL);

    ws.onopen = () => {
      console.log('WebSocket: Connected');
      setConnected(true);
      reconnectAttemptRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        subscribersRef.current.forEach((callback) => callback(message));
      } catch (err) {
        console.error('WebSocket: Failed to parse message', err);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket: Disconnected');
      setConnected(false);
      wsRef.current = null;

      // Auto-reconnect with exponential backoff
      const delay = WS_RECONNECT_DELAYS[
        Math.min(reconnectAttemptRef.current, WS_RECONNECT_DELAYS.length - 1)
      ];
      console.log(`WebSocket: Reconnecting in ${delay}ms...`);
      reconnectTimeoutRef.current = window.setTimeout(() => {
        reconnectAttemptRef.current++;
        connect();
      }, delay);
    };

    ws.onerror = (error) => {
      console.error('WebSocket: Error', error);
    };

    wsRef.current = ws;
  }, []);

  const reconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    reconnectAttemptRef.current = 0;
    wsRef.current?.close();
    connect();
  }, [connect]);

  const subscribe = useCallback((callback: (message: WebSocketMessage) => void) => {
    subscribersRef.current.add(callback);
    return () => {
      subscribersRef.current.delete(callback);
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      wsRef.current?.close();
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
