import axios from 'axios';
import { OBSERVABILITY_BACKEND_URL, DOCUMENT_SERVER_URL, AGENT_REGISTRY_URL } from '@/utils/constants';

// Axios instance for observability backend
export const observabilityApi = axios.create({
  baseURL: OBSERVABILITY_BACKEND_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Axios instance for context store server
export const documentApi = axios.create({
  baseURL: DOCUMENT_SERVER_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Axios instance for agent registry
export const agentRegistryApi = axios.create({
  baseURL: AGENT_REGISTRY_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add response interceptors for error handling
const handleError = (error: unknown) => {
  if (axios.isAxiosError(error)) {
    const message = error.response?.data?.detail || error.response?.data?.message || error.message;
    console.error('API Error:', message);
    throw new Error(message);
  }
  throw error;
};

observabilityApi.interceptors.response.use((response) => response, handleError);
documentApi.interceptors.response.use((response) => response, handleError);
agentRegistryApi.interceptors.response.use((response) => response, handleError);
