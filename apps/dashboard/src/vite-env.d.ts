/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_AGENT_ORCHESTRATOR_API_URL: string;
  readonly VITE_DOCUMENT_SERVER_URL: string;
  readonly VITE_AGENT_ORCHESTRATOR_API_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
