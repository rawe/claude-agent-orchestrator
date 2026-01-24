/**
 * System Agents Registry
 *
 * Central registry of all internal/system agents used by the dashboard.
 * Add new agents here to make them available for automatic provisioning.
 */

import { scriptAssistantDefinition } from './agents/script-assistant';

// =============================================================================
// Agent Definition Type
// =============================================================================

export interface SystemAgentDefinition {
  name: string;
  description: string;
  tags: readonly string[];
  systemPrompt: string;
  inputSchema: Record<string, unknown>;
  outputSchema: Record<string, unknown>;
}

// =============================================================================
// Registry
// =============================================================================

/**
 * All system agents that the dashboard requires.
 * These can be automatically created via the SystemAgentManager.
 */
export const systemAgentRegistry: readonly SystemAgentDefinition[] = [
  scriptAssistantDefinition,
  // Add more agents here as needed:
  // agentEditorAssistantDefinition,
  // descriptionAssistantDefinition,
];

/**
 * Get agent definition by name.
 */
export function getAgentDefinition(name: string): SystemAgentDefinition | undefined {
  return systemAgentRegistry.find((def) => def.name === name);
}

/**
 * Get all agent names.
 */
export function getAgentNames(): string[] {
  return systemAgentRegistry.map((def) => def.name);
}
