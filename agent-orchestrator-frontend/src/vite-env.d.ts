/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_OBSERVABILITY_BACKEND_URL: string;
  readonly VITE_DOCUMENT_SERVER_URL: string;
  readonly VITE_AGENT_MANAGER_URL: string;
  readonly VITE_WEBSOCKET_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
