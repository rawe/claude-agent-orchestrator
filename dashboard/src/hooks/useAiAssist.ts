/**
 * useAiAssist Hook
 *
 * Reusable hook for AI-assisted field editing.
 * Manages state and interactions with AI agents via the Coordinator.
 *
 * @example
 * ```tsx
 * const ai = useAiAssist<MyInput, MyOutput>({
 *   agentName: 'my-assistant',
 *   buildInput: (userRequest) => ({
 *     content: getValues('field'),
 *     user_request: userRequest,
 *   }),
 *   defaultRequest: 'Check for issues',
 * });
 *
 * // In JSX:
 * <button onClick={ai.toggle}>{ai.showInput ? 'Cancel' : 'AI'}</button>
 * {ai.showInput && (
 *   <input value={ai.userRequest} onChange={e => ai.setUserRequest(e.target.value)} />
 *   <button onClick={ai.submit}>Send</button>
 * )}
 * {ai.result && (
 *   <div>
 *     <pre>{ai.result.content}</pre>
 *     <button onClick={() => { applyResult(ai.result); ai.accept(); }}>Accept</button>
 *     <button onClick={ai.reject}>Reject</button>
 *   </div>
 * )}
 * ```
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { CoordinatorClient, RunHandle } from '@/lib/coordinator-client';
import { AGENT_ORCHESTRATOR_API_URL } from '@/utils/constants';
import { fetchAccessToken } from '@/services/auth';
import { agentService } from '@/services/agentService';

// Shared coordinator client
const coordinatorClient = new CoordinatorClient({
  baseUrl: AGENT_ORCHESTRATOR_API_URL,
  getToken: fetchAccessToken,
});

export interface UseAiAssistOptions<TInput> {
  /** Agent name to call */
  agentName: string;

  /** Build input object from user request */
  buildInput: (userRequest: string) => TInput;

  /** Default request if user leaves input empty */
  defaultRequest?: string;
}

/** Message shown when agent is not available */
const AGENT_UNAVAILABLE_MESSAGE = 'AI agent not available. Go to Settings → System Agents to provision.';

/** Suffix added to error messages */
const ERROR_HELP_SUFFIX = '\n\nIf this persists, go to Settings → System Agents to re-provision.';

/**
 * Extracts a readable message from various error types.
 */
function extractErrorMessage(error: unknown): string {
  // String
  if (typeof error === 'string') {
    return error;
  }

  // Error instance
  if (error instanceof Error) {
    return error.message;
  }

  // Object with common error properties
  if (error && typeof error === 'object') {
    const obj = error as Record<string, unknown>;

    // API error format: { detail: "message" } or { detail: { message: "..." } }
    if (obj.detail) {
      if (typeof obj.detail === 'string') {
        return obj.detail;
      }
      if (typeof obj.detail === 'object' && obj.detail !== null) {
        const detail = obj.detail as Record<string, unknown>;
        if (typeof detail.message === 'string') {
          return detail.message;
        }
        if (typeof detail.error === 'string') {
          return detail.error;
        }
      }
    }

    // Common error properties
    if (typeof obj.message === 'string') {
      return obj.message;
    }
    if (typeof obj.error === 'string') {
      return obj.error;
    }

    // Try to stringify, but avoid [object Object]
    try {
      const json = JSON.stringify(error);
      if (json && json !== '{}') {
        return json;
      }
    } catch {
      // Ignore stringify errors
    }
  }

  return 'An unexpected error occurred';
}

/**
 * Wraps an error message with helpful context.
 */
function formatErrorMessage(error: unknown): string {
  const message = extractErrorMessage(error);

  // Check for common error patterns and provide clearer messages
  const lowerMessage = message.toLowerCase();

  if (lowerMessage.includes('not found') || lowerMessage.includes('404')) {
    return `Agent not found. Please ensure system agents are provisioned.${ERROR_HELP_SUFFIX}`;
  }

  if (lowerMessage.includes('validation') || lowerMessage.includes('schema')) {
    return `Input/output schema mismatch. The agent may need to be re-provisioned.${ERROR_HELP_SUFFIX}`;
  }

  if (lowerMessage.includes('timeout') || lowerMessage.includes('timed out')) {
    return `Request timed out. The agent may be unavailable.${ERROR_HELP_SUFFIX}`;
  }

  // Generic error with help suffix
  return `${message}${ERROR_HELP_SUFFIX}`;
}

export interface UseAiAssistReturn<TOutput> {
  // Availability
  available: boolean;
  checkingAvailability: boolean;
  unavailableReason: string | null;

  // State
  showInput: boolean;
  userRequest: string;
  isLoading: boolean;
  result: TOutput | null;
  error: string | null;

  // Setters
  setUserRequest: (value: string) => void;

  // Actions
  toggle: () => void;
  submit: () => Promise<void>;
  cancel: () => void;
  accept: () => void;
  reject: () => void;
  clearError: () => void;
}

export function useAiAssist<TInput, TOutput>(
  options: UseAiAssistOptions<TInput>
): UseAiAssistReturn<TOutput> {
  const { agentName, buildInput, defaultRequest = 'Check for issues' } = options;

  // Availability state
  const [available, setAvailable] = useState(false);
  const [checkingAvailability, setCheckingAvailability] = useState(true);

  // State
  const [showInput, setShowInput] = useState(false);
  const [userRequest, setUserRequest] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<TOutput | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Refs for cancellation
  const currentRunRef = useRef<RunHandle | null>(null);
  const cancelledRef = useRef(false);

  // Check agent availability on mount
  useEffect(() => {
    let cancelled = false;

    const checkAvailability = async () => {
      setCheckingAvailability(true);
      try {
        // checkNameAvailable returns true if name is FREE (agent doesn't exist)
        // We want the opposite - true if agent EXISTS
        const isFree = await agentService.checkNameAvailable(agentName);
        if (!cancelled) {
          setAvailable(!isFree);
        }
      } catch {
        // On error, assume not available
        if (!cancelled) {
          setAvailable(false);
        }
      } finally {
        if (!cancelled) {
          setCheckingAvailability(false);
        }
      }
    };

    checkAvailability();

    return () => {
      cancelled = true;
    };
  }, [agentName]);

  // Toggle input visibility
  const toggle = useCallback(() => {
    if (showInput) {
      setShowInput(false);
      setUserRequest('');
    } else {
      setShowInput(true);
    }
  }, [showInput]);

  // Submit request to AI
  const submit = useCallback(async () => {
    setShowInput(false);
    setIsLoading(true);
    setError(null);
    setResult(null);
    cancelledRef.current = false;

    try {
      const input = buildInput(userRequest.trim() || defaultRequest);

      // Start run - may fail if agent doesn't exist or validation fails
      let run: RunHandle;
      try {
        run = await coordinatorClient.startRun({
          agentName,
          parameters: input as unknown as Record<string, unknown>,
        });
        currentRunRef.current = run;
      } catch (startError) {
        if (!cancelledRef.current) {
          setError(formatErrorMessage(startError));
        }
        return;
      }

      // Check if cancelled during start
      if (cancelledRef.current) {
        return;
      }

      // Poll for result - may fail due to timeout or agent errors
      let runResult;
      try {
        runResult = await run.waitForResult();
      } catch (pollError) {
        if (!cancelledRef.current) {
          setError(formatErrorMessage(pollError));
        }
        return;
      }

      // Check if cancelled during polling
      if (cancelledRef.current) {
        return;
      }

      // Process result
      if (runResult.status === 'completed' && runResult.resultData) {
        setResult(runResult.resultData as unknown as TOutput);
      } else if (runResult.status === 'failed') {
        setError(formatErrorMessage(runResult.error || 'AI request failed'));
      } else if (runResult.status === 'stopped') {
        // Don't show error if we cancelled it ourselves
        if (!cancelledRef.current) {
          setError('Request was stopped.');
        }
      } else {
        setError(formatErrorMessage('No result returned from agent'));
      }
    } catch (err) {
      // Catch-all for unexpected errors
      if (!cancelledRef.current) {
        setError(formatErrorMessage(err));
      }
    } finally {
      setIsLoading(false);
      setUserRequest('');
      currentRunRef.current = null;
    }
  }, [agentName, buildInput, defaultRequest, userRequest]);

  // Accept result (consumer should apply changes before calling)
  const accept = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  // Reject result
  const reject = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  // Cancel ongoing AI request
  const cancel = useCallback(() => {
    cancelledRef.current = true;
    setIsLoading(false);
    setShowInput(false);
    setUserRequest('');
    setError(null);
    setResult(null);

    // TODO: Future enhancement - call the Coordinator SDK to stop the run
    // This would send a cancel/stop request to the API to terminate the agent run.
    // Implementation:
    //   if (currentRunRef.current) {
    //     currentRunRef.current.stop().catch(console.error);
    //   }
    currentRunRef.current = null;
  }, []);

  // Clear error
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    // Availability
    available,
    checkingAvailability,
    unavailableReason: available ? null : AGENT_UNAVAILABLE_MESSAGE,

    // State
    showInput,
    userRequest,
    isLoading,
    result,
    error,

    // Setters
    setUserRequest,

    // Actions
    toggle,
    submit,
    cancel,
    accept,
    reject,
    clearError,
  };
}
