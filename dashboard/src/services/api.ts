import axios from 'axios';
import { AGENT_ORCHESTRATOR_API_URL, DOCUMENT_SERVER_URL } from '@/utils/constants';
import { fetchAccessToken, isOidcConfigured } from './auth';

// Axios instance for Agent Orchestrator API (sessions, events, agent blueprints, runs)
export const agentOrchestratorApi = axios.create({
  baseURL: AGENT_ORCHESTRATOR_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
agentOrchestratorApi.interceptors.request.use(async (config) => {
  // Add OIDC token if configured and available
  if (isOidcConfigured()) {
    const token = await fetchAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  // When OIDC is not configured, requests go without auth
  // (for local development with AUTH_ENABLED=false on coordinator)
  return config;
});

// Axios instance for context store server
export const documentApi = axios.create({
  baseURL: DOCUMENT_SERVER_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add response interceptors for error handling with auth-specific messages
const handleError = (error: unknown) => {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;

    // Auth-specific error messages
    if (status === 401) {
      const message = 'Authentication required. Please log in.';
      console.error('API Error:', message);
      throw new Error(message);
    }
    if (status === 403) {
      const message = 'Access denied. Invalid or expired token.';
      console.error('API Error:', message);
      throw new Error(message);
    }

    // Parameter validation error - preserve structured error for UI display
    // The error.response.data.detail contains the structured error info
    const detail = error.response?.data?.detail;
    if (detail && typeof detail === 'object' && detail.error === 'parameter_validation_failed') {
      console.error('Parameter validation error:', detail);
      // Throw the structured error object for components to handle
      throw detail;
    }

    const message = detail || error.response?.data?.message || error.message;
    console.error('API Error:', message);
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
  }
  throw error;
};

agentOrchestratorApi.interceptors.response.use((response) => response, handleError);
documentApi.interceptors.response.use((response) => response, handleError);
