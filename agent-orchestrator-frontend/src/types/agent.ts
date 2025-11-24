export type AgentStatus = 'active' | 'inactive';

export interface Agent {
  name: string;
  description: string;
  system_prompt: string;
  mcp_servers: string[];
  skills: string[];
  status: AgentStatus;
  created_at: string;
  updated_at: string;
}

export interface AgentCreate {
  name: string;
  description: string;
  system_prompt: string;
  mcp_servers: string[];
  skills: string[];
}

export interface AgentUpdate {
  description?: string;
  system_prompt?: string;
  mcp_servers?: string[];
  skills?: string[];
}

// Predefined MCP servers available for selection
export const MCP_SERVERS = [
  { name: 'github', label: 'GitHub' },
  { name: 'filesystem', label: 'Filesystem' },
  { name: 'postgres', label: 'PostgreSQL' },
  { name: 'sqlite', label: 'SQLite' },
  { name: 'slack', label: 'Slack' },
  { name: 'jira', label: 'Jira' },
  { name: 'confluence', label: 'Confluence' },
  { name: 'browser', label: 'Browser' },
] as const;

// Predefined skills available for selection
export const SKILLS = [
  { name: 'pdf', label: 'PDF Handler' },
  { name: 'xlsx', label: 'Excel Handler' },
  { name: 'csv', label: 'CSV Handler' },
  { name: 'image', label: 'Image Handler' },
  { name: 'document-sync', label: 'Document Sync' },
] as const;
