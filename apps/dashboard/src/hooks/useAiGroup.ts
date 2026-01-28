/**
 * useAiGroup Hook
 *
 * Aggregates multiple useAiAssist instances for unified state management.
 * Use this when a component has multiple AI buttons and needs to protect
 * Save/Close actions when any AI is loading.
 *
 * @example
 * ```tsx
 * const scriptAi = useAiAssist({ agentName: 'script-assistant', ... });
 * const schemaAi = useAiAssist({ agentName: 'schema-assistant', ... });
 *
 * const ai = useAiGroup([scriptAi, schemaAi]);
 *
 * // Protect UI when any AI is loading
 * <Button disabled={ai.isAnyLoading}>Save</Button>
 * <Modal onClose={() => { if (!ai.isAnyLoading) onClose(); }}>
 *
 * // Individual AI buttons use their own instance
 * <button onClick={scriptAi.toggle}>Script AI</button>
 * <button onClick={schemaAi.toggle}>Schema AI</button>
 * ```
 */

import { useMemo, useCallback } from 'react';
import type { UseAiAssistReturn } from './useAiAssist';

export interface UseAiGroupReturn {
  /** True if any AI instance is currently loading */
  isAnyLoading: boolean;

  /** True if any AI instance has a pending result */
  hasAnyResult: boolean;

  /** True if any AI instance has an error */
  hasAnyError: boolean;

  /** Cancel all loading AI instances */
  cancelAll: () => void;

  /** Number of registered AI instances */
  count: number;
}

/**
 * Aggregates multiple useAiAssist instances for unified state.
 *
 * @param instances - Array of useAiAssist return values
 * @returns Aggregated state and actions
 */
export function useAiGroup<T>(
  instances: UseAiAssistReturn<T>[]
): UseAiGroupReturn {
  const isAnyLoading = useMemo(
    () => instances.some((ai) => ai.isLoading),
    [instances]
  );

  const hasAnyResult = useMemo(
    () => instances.some((ai) => ai.result !== null),
    [instances]
  );

  const hasAnyError = useMemo(
    () => instances.some((ai) => ai.error !== null),
    [instances]
  );

  const cancelAll = useCallback(() => {
    instances.forEach((ai) => {
      if (ai.isLoading) {
        ai.cancel();
      }
    });
  }, [instances]);

  return {
    isAnyLoading,
    hasAnyResult,
    hasAnyError,
    cancelAll,
    count: instances.length,
  };
}
