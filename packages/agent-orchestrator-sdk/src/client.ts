/**
 * Coordinator Client
 *
 * MVP SDK for programmatic interaction with the Agent Coordinator.
 * Provides a simple interface to start runs and wait for results.
 */

import type { CoordinatorClientConfig, StartRunOptions, StartRunResponse } from './types';
import { RunHandle } from './run-handle';

/**
 * Client for interacting with the Agent Coordinator API.
 *
 * @example
 * ```typescript
 * const client = new CoordinatorClient({
 *   baseUrl: 'http://localhost:8765',
 *   getToken: () => authContext.getAccessToken()
 * });
 *
 * const run = await client.startRun({
 *   parameters: { prompt: 'Help me write a script' }
 * });
 *
 * const result = await run.waitForResult();
 * console.log(result.resultText);
 * ```
 */
export class CoordinatorClient {
  private readonly baseUrl: string;
  private readonly getToken?: () => Promise<string | null>;

  constructor(config: CoordinatorClientConfig) {
    // Remove trailing slash if present
    this.baseUrl = config.baseUrl.replace(/\/$/, '');
    this.getToken = config.getToken;
  }

  /**
   * Start a new agent run.
   *
   * @param options - Run options including parameters and optional agent name
   * @returns A RunHandle to track and wait for the run
   */
  async startRun(options: StartRunOptions): Promise<RunHandle> {
    const response = await this.createRun(options);

    return new RunHandle({
      runId: response.runId,
      sessionId: response.sessionId,
      baseUrl: this.baseUrl,
      getToken: this.getToken,
    });
  }

  /**
   * Resume an existing session with new input.
   *
   * @param sessionId - The session to resume
   * @param parameters - New input parameters
   * @returns A RunHandle to track the resumed run
   */
  async resumeSession(
    sessionId: string,
    parameters: Record<string, unknown>
  ): Promise<RunHandle> {
    const headers = await this.getHeaders();

    const body = {
      type: 'resume_session',
      session_id: sessionId,
      parameters,
    };

    const response = await fetch(`${this.baseUrl}/runs`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const detail = errorData.detail;
      const message = typeof detail === 'string'
        ? detail
        : detail != null
          ? JSON.stringify(detail, null, 2)
          : `Failed to resume session: ${response.statusText}`;
      throw new Error(message);
    }

    const data = await response.json();

    return new RunHandle({
      runId: data.run_id,
      sessionId: data.session_id,
      baseUrl: this.baseUrl,
      getToken: this.getToken,
    });
  }

  private async createRun(options: StartRunOptions): Promise<StartRunResponse> {
    const headers = await this.getHeaders();

    const body: Record<string, unknown> = {
      type: 'start_session',
      parameters: options.parameters,
    };

    if (options.agentName) {
      body.agent_name = options.agentName;
    }

    if (options.projectDir) {
      body.project_dir = options.projectDir;
    }

    const response = await fetch(`${this.baseUrl}/runs`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const detail = errorData.detail;
      const message = typeof detail === 'string'
        ? detail
        : detail != null
          ? JSON.stringify(detail, null, 2)
          : `Failed to start run: ${response.statusText}`;
      throw new Error(message);
    }

    const data = await response.json();

    return {
      runId: data.run_id,
      sessionId: data.session_id,
      status: data.status,
    };
  }

  private async getHeaders(): Promise<Record<string, string>> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.getToken) {
      const token = await this.getToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    }

    return headers;
  }
}
