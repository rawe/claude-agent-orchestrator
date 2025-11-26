import type { MCPServerConfig } from '@/types';

/**
 * MCP Server Templates
 *
 * Pre-defined configurations for common MCP servers.
 * These can be used as starting points when creating agents.
 *
 * To add a new template:
 * 1. Add an entry to MCP_TEMPLATES with a unique key
 * 2. Provide command, args, and optionally env fields
 * 3. The template will appear in the AgentEditor dropdown
 */
export const MCP_TEMPLATES: Record<string, MCPServerConfig> = {
  playwright: {
    command: 'npx',
    args: ['@playwright/mcp@latest'],
  },
  'brave-search': {
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/server-brave-search'],
    env: {
      BRAVE_API_KEY: '${BRAVE_API_KEY}',
    },
  },
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
