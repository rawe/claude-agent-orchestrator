/**
 * Application configuration loaded from environment variables
 */
const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8765';

export const config = {
  // API endpoints
  apiUrl,
  // SSE endpoint derived from API URL (ADR-013)
  sseUrl: `${apiUrl}/sse/sessions`,

  // Agent configuration
  agentBlueprint: import.meta.env.VITE_AGENT_BLUEPRINT || 'default-agent',

  // App settings
  appTitle: import.meta.env.VITE_APP_TITLE || 'AI Assistant',
} as const;

export type Config = typeof config;
