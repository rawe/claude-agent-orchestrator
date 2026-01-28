/**
 * Application configuration loaded from environment variables
 */
const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8765';

// SSE endpoint - Token is added at runtime via auth service
// (EventSource doesn't support headers, so token is passed as query param)
const sseBaseUrl = `${apiUrl}/sse/sessions`;

export const config = {
  // API endpoints
  apiUrl,
  // SSE base endpoint derived from API URL (ADR-013)
  // Token appended at runtime when OIDC is configured
  sseBaseUrl,

  // Agent configuration
  agentBlueprint: import.meta.env.VITE_AGENT_BLUEPRINT || 'default-agent',

  // App settings
  appTitle: import.meta.env.VITE_APP_TITLE || 'AI Assistant',
} as const;

export type Config = typeof config;
