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

import { useState, useCallback } from 'react';
import { CoordinatorClient } from '@/lib/coordinator-client';
import { AGENT_ORCHESTRATOR_API_URL } from '@/utils/constants';
import { fetchAccessToken } from '@/services/auth';

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

export interface UseAiAssistReturn<TOutput> {
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
  accept: () => void;
  reject: () => void;
  clearError: () => void;
}

export function useAiAssist<TInput, TOutput>(
  options: UseAiAssistOptions<TInput>
): UseAiAssistReturn<TOutput> {
  const { agentName, buildInput, defaultRequest = 'Check for issues' } = options;

  // State
  const [showInput, setShowInput] = useState(false);
  const [userRequest, setUserRequest] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<TOutput | null>(null);
  const [error, setError] = useState<string | null>(null);

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

    try {
      const input = buildInput(userRequest.trim() || defaultRequest);

      const run = await coordinatorClient.startRun({
        agentName,
        parameters: input as unknown as Record<string, unknown>,
      });

      const runResult = await run.waitForResult();

      if (runResult.status === 'completed' && runResult.resultData) {
        setResult(runResult.resultData as unknown as TOutput);
      } else if (runResult.status === 'failed') {
        setError(runResult.error || 'AI request failed');
      } else {
        setError('No result returned');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'AI request failed');
    } finally {
      setIsLoading(false);
      setUserRequest('');
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

  // Clear error
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    showInput,
    userRequest,
    isLoading,
    result,
    error,
    setUserRequest,
    toggle,
    submit,
    accept,
    reject,
    clearError,
  };
}
