/**
 * System Agents
 *
 * Central management for internal/system agents used by the dashboard.
 *
 * Usage:
 *
 * 1. Import agent types and keys:
 *    import {
 *      ScriptAssistantInput,
 *      ScriptAssistantOutput,
 *      ScriptAssistantOutputKeys,
 *    } from '@/lib/system-agents';
 *
 * 2. Provision agents (from Settings):
 *    import { provisionAllAgents } from '@/lib/system-agents';
 *    const result = await provisionAllAgents();
 *
 * 3. Get agent definition:
 *    import { getAgentDefinition } from '@/lib/system-agents';
 *    const def = getAgentDefinition('script-assistant');
 */

// Agent definitions and types
export { scriptAssistantDefinition } from './agents/script-assistant';
export type { ScriptAssistantInput, ScriptAssistantOutput } from './agents/script-assistant';
export { ScriptAssistantInputKeys, ScriptAssistantOutputKeys } from './agents/script-assistant';

export { schemaAssistantDefinition } from './agents/schema-assistant';
export type { SchemaAssistantInput, SchemaAssistantOutput } from './agents/schema-assistant';
export { SchemaAssistantInputKeys, SchemaAssistantOutputKeys } from './agents/schema-assistant';

// Registry
export {
  systemAgentRegistry,
  getAgentDefinition,
  getAgentNames,
  type SystemAgentDefinition,
} from './registry';

// Manager
export {
  provisionAgent,
  provisionAllAgents,
  getSystemAgentNames,
  type ProvisionResult,
  type ProvisionAllResult,
} from './manager';
