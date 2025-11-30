/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_AGENT_RUNTIME_URL: string;
  readonly VITE_DOCUMENT_SERVER_URL: string;
  readonly VITE_AGENT_REGISTRY_URL: string;
  readonly VITE_WEBSOCKET_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
