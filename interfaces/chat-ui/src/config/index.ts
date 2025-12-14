/**
 * Application configuration loaded from environment variables
 */
export const config = {
  // API endpoints
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8765',
  wsUrl: import.meta.env.VITE_WS_URL || 'ws://localhost:8765/ws',

  // Agent configuration
  agentBlueprint: import.meta.env.VITE_AGENT_BLUEPRINT || 'default-agent',

  // App settings
  appTitle: import.meta.env.VITE_APP_TITLE || 'AI Assistant',

  // WebSocket reconnection delays (exponential backoff)
  wsReconnectDelays: [1000, 2000, 4000, 8000, 16000, 30000],
} as const;

export type Config = typeof config;
