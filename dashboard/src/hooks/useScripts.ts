import { useState, useEffect, useCallback } from 'react';
import { useNotification } from '@/contexts';
import { scriptService } from '@/services/scriptService';
import type { Script, ScriptSummary, ScriptCreate, ScriptUpdate } from '@/types/script';

export function useScripts() {
  const [scripts, setScripts] = useState<ScriptSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const { showError } = useNotification();

  const fetchScripts = useCallback(async () => {
    setLoading(true);
    try {
      const data = await scriptService.getScripts();
      setScripts(data);
    } catch (err) {
      showError('Failed to load scripts');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [showError]);

  useEffect(() => {
    fetchScripts();
  }, [fetchScripts]);

  const getScript = useCallback(async (name: string): Promise<Script> => {
    return scriptService.getScript(name);
  }, []);

  const createScript = useCallback(async (data: ScriptCreate): Promise<Script> => {
    const newScript = await scriptService.createScript(data);
    // Refetch to update the list with summary data
    await fetchScripts();
    return newScript;
  }, [fetchScripts]);

  const updateScript = useCallback(async (name: string, data: ScriptUpdate): Promise<Script> => {
    const updated = await scriptService.updateScript(name, data);
    // Refetch to update the list with summary data
    await fetchScripts();
    return updated;
  }, [fetchScripts]);

  const deleteScript = useCallback(async (name: string) => {
    await scriptService.deleteScript(name);
    setScripts((prev) => prev.filter((s) => s.name !== name));
  }, []);

  const checkNameAvailable = useCallback(async (name: string) => {
    return scriptService.checkNameAvailable(name);
  }, []);

  return {
    scripts,
    loading,
    getScript,
    createScript,
    updateScript,
    deleteScript,
    checkNameAvailable,
    refetch: fetchScripts,
  };
}
