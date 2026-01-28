/**
 * Agent Orchestrator SDK
 *
 * Programmatic interface for interacting with the Agent Orchestrator.
 *
 * @example
 * ```typescript
 * import { CoordinatorClient } from '@rawe/agent-orchestrator-sdk';
 *
 * const client = new CoordinatorClient({
 *   baseUrl: 'http://localhost:8765'
 * });
 *
 * const run = await client.startRun({
 *   parameters: { prompt: 'Hello!' }
 * });
 *
 * const result = await run.waitForResult();
 * ```
 */

export { CoordinatorClient } from './client';
export { RunHandle } from './run-handle';
export type {
  CoordinatorClientConfig,
  StartRunOptions,
  StartRunResponse,
  RunResult,
  SessionStatus,
} from './types';
