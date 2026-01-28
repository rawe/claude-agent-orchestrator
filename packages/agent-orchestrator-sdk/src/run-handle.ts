/**
 * Run Handle
 *
 * Represents an active run and provides methods to wait for completion.
 */

import type {
  RunResult,
  SessionStatus,
  SessionStatusResponse,
  SessionResultResponse,
} from './types';

/** Polling interval in milliseconds */
const POLL_INTERVAL_MS = 1000;

/** Terminal statuses that indicate the run is done */
const TERMINAL_STATUSES: SessionStatus[] = ['finished', 'stopped', 'not_existent'];

export interface RunHandleConfig {
  runId: string;
  sessionId: string;
  baseUrl: string;
  getToken?: () => Promise<string | null>;
}

/**
 * Handle to an active run with methods to poll for completion.
 */
export class RunHandle {
  readonly runId: string;
  readonly sessionId: string;

  private readonly baseUrl: string;
  private readonly getToken?: () => Promise<string | null>;

  constructor(config: RunHandleConfig) {
    this.runId = config.runId;
    this.sessionId = config.sessionId;
    this.baseUrl = config.baseUrl;
    this.getToken = config.getToken;
  }

  /**
   * Wait for the run to complete and return the result.
   *
   * Polls the session status every second until terminal state.
   */
  async waitForResult(): Promise<RunResult> {
    // Poll until terminal status
    let status: SessionStatus = 'pending';

    while (!TERMINAL_STATUSES.includes(status)) {
      await this.sleep(POLL_INTERVAL_MS);
      status = await this.getSessionStatus();
    }

    // Handle terminal statuses
    if (status === 'not_existent') {
      return {
        status: 'failed',
        error: 'Session not found',
      };
    }

    if (status === 'stopped') {
      return {
        status: 'stopped',
      };
    }

    // status === 'finished' - fetch result
    return this.fetchResult();
  }

  /**
   * Stop the run.
   */
  async stop(): Promise<void> {
    const headers = await this.getHeaders();

    const response = await fetch(`${this.baseUrl}/sessions/${this.sessionId}/stop`, {
      method: 'POST',
      headers,
    });

    if (!response.ok) {
      throw new Error(`Failed to stop session: ${response.statusText}`);
    }
  }

  private async getSessionStatus(): Promise<SessionStatus> {
    const headers = await this.getHeaders();

    const response = await fetch(
      `${this.baseUrl}/sessions/${this.sessionId}/status`,
      { headers }
    );

    if (!response.ok) {
      throw new Error(`Failed to get session status: ${response.statusText}`);
    }

    const data: SessionStatusResponse = await response.json();
    return data.status;
  }

  private async fetchResult(): Promise<RunResult> {
    const headers = await this.getHeaders();

    const response = await fetch(
      `${this.baseUrl}/sessions/${this.sessionId}/result`,
      { headers }
    );

    if (!response.ok) {
      // Result endpoint may fail if no result event was emitted
      if (response.status === 404) {
        return {
          status: 'completed',
          resultText: undefined,
          resultData: undefined,
        };
      }
      throw new Error(`Failed to get session result: ${response.statusText}`);
    }

    const data: SessionResultResponse = await response.json();

    return {
      status: 'completed',
      resultText: data.result_text ?? undefined,
      resultData: data.result_data ?? undefined,
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

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
