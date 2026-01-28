/**
 * System Agent Manager
 *
 * Handles provisioning of system agents via the Coordinator API.
 * Creates or updates agents based on definitions in the registry.
 */

import { agentService } from '@/services/agentService';
import { systemAgentRegistry, type SystemAgentDefinition } from './registry';

// =============================================================================
// Types
// =============================================================================

export interface ProvisionResult {
  name: string;
  action: 'created' | 'updated' | 'unchanged' | 'error';
  error?: string;
}

export interface ProvisionAllResult {
  results: ProvisionResult[];
  success: number;
  failed: number;
}

// =============================================================================
// Manager
// =============================================================================

/**
 * Check if an agent exists.
 */
async function agentExists(name: string): Promise<boolean> {
  try {
    await agentService.getAgent(name);
    return true;
  } catch {
    return false;
  }
}

/**
 * Convert SystemAgentDefinition to AgentCreate format.
 */
function toAgentCreate(def: SystemAgentDefinition) {
  return {
    name: def.name,
    type: 'autonomous' as const,
    description: def.description,
    system_prompt: def.systemPrompt,
    parameters_schema: def.inputSchema,
    output_schema: def.outputSchema,
    tags: [...def.tags],
  };
}

/**
 * Provision a single system agent (create or update).
 */
export async function provisionAgent(name: string): Promise<ProvisionResult> {
  const definition = systemAgentRegistry.find((d) => d.name === name);

  if (!definition) {
    return { name, action: 'error', error: `Agent '${name}' not found in registry` };
  }

  try {
    const exists = await agentExists(name);
    const agentData = toAgentCreate(definition);

    if (exists) {
      // Update existing agent
      await agentService.updateAgent(name, {
        description: agentData.description,
        system_prompt: agentData.system_prompt,
        parameters_schema: agentData.parameters_schema,
        output_schema: agentData.output_schema,
        tags: agentData.tags,
      });
      return { name, action: 'updated' };
    } else {
      // Create new agent
      await agentService.createAgent(agentData);
      return { name, action: 'created' };
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error';
    return { name, action: 'error', error: message };
  }
}

/**
 * Provision all system agents in the registry.
 */
export async function provisionAllAgents(): Promise<ProvisionAllResult> {
  const results: ProvisionResult[] = [];

  for (const definition of systemAgentRegistry) {
    const result = await provisionAgent(definition.name);
    results.push(result);
  }

  return {
    results,
    success: results.filter((r) => r.action !== 'error').length,
    failed: results.filter((r) => r.action === 'error').length,
  };
}

/**
 * Get list of system agent names from the registry.
 */
export function getSystemAgentNames(): string[] {
  return systemAgentRegistry.map((d) => d.name);
}
