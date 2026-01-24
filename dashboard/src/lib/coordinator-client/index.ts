/**
 * Coordinator Client SDK
 *
 * Programmatic interface for interacting with the Agent Coordinator.
 *
 * @example
 * ```typescript
 * import { CoordinatorClient } from '@/lib/coordinator-client';
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
