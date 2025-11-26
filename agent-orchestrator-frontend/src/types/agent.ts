export type AgentStatus = 'active' | 'inactive';

export interface MCPServerConfig {
  command: string;
  args: string[];
  env?: Record<string, string>;
}

export interface Agent {
  name: string;
  description: string;
  system_prompt: string | null;
  mcp_servers: Record<string, MCPServerConfig> | null;
  skills: string[] | null;
  status: AgentStatus;
  created_at: string;
  modified_at: string;
}

export interface AgentCreate {
  name: string;
  description: string;
  system_prompt?: string;
  mcp_servers?: Record<string, MCPServerConfig> | null;
  skills?: string[];
}

export interface AgentUpdate {
  description?: string;
  system_prompt?: string;
  mcp_servers?: Record<string, MCPServerConfig> | null;
  skills?: string[];
}

// Predefined skills available for selection
export const SKILLS = [
  { name: 'pdf', label: 'PDF Handler' },
  { name: 'xlsx', label: 'Excel Handler' },
  { name: 'csv', label: 'CSV Handler' },
  { name: 'image', label: 'Image Handler' },
  { name: 'document-sync', label: 'Document Sync' },
] as const;
