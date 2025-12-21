/**
 * Application configuration loaded from environment variables
 */
export const config = {
  // API endpoints
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8765',
  sseUrl: import.meta.env.VITE_SSE_URL || 'http://localhost:8765/sse/sessions',

  // Agent configuration
  agentBlueprint: import.meta.env.VITE_AGENT_BLUEPRINT || 'default-agent',

  // App settings
  appTitle: import.meta.env.VITE_APP_TITLE || 'AI Assistant',
} as const;

export type Config = typeof config;
