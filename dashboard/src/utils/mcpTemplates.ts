import type { MCPServerConfig } from '@/types';

/**
 * MCP Server Templates
 *
 * Pre-defined configurations for common MCP servers.
 * These can be used as starting points when creating agents.
 *
 * To add a new template:
 * 1. Add an entry to MCP_TEMPLATES with a unique key
 * 2. For stdio servers: provide command, args, and optionally env
 * 3. For HTTP servers: provide type: 'http' and url
 * 4. The template will appear in the AgentEditor dropdown
 */
export const MCP_TEMPLATES: Record<string, MCPServerConfig> = {
  'mcp-atlassian-http': {
    type: 'http',
    url: 'http://localhost:9000/mcp',
  },
  'mcp-ado-http': {
    type: 'http',
    url: 'http://localhost:9001/mcp',
  },
  'agent-orchestrator-http': {
    type: 'http',
    url: 'http://localhost:9500/mcp',
    headers: {
      'X-Agent-Session-Name': '${AGENT_SESSION_NAME}',
    },
  },
  'context-store-http': {
    type: 'http',
    url: 'http://localhost:9501/mcp',
  }
};

export const TEMPLATE_NAMES = Object.keys(MCP_TEMPLATES);

export function getTemplate(name: string): MCPServerConfig | null {
  return MCP_TEMPLATES[name] || null;
}

export function addTemplate(
  existing: Record<string, MCPServerConfig> | null,
  templateName: string
): Record<string, MCPServerConfig> {
  const template = getTemplate(templateName);
  if (!template) return existing || {};

  return {
    ...(existing || {}),
    [templateName]: template,
  };
}
