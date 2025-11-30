import { useState, useEffect, useCallback } from 'react';
import { useNotification } from '@/contexts';
import { agentService } from '@/services';
import type { Agent, AgentCreate, AgentUpdate, AgentStatus } from '@/types';

export function useAgents() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const { showError } = useNotification();

  const fetchAgents = useCallback(async () => {
    setLoading(true);
    try {
      const data = await agentService.getAgents();
      setAgents(data);
    } catch (err) {
      showError('Failed to load agents');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [showError]);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  const createAgent = useCallback(async (data: AgentCreate) => {
    const newAgent = await agentService.createAgent(data);
    setAgents((prev) => [...prev, newAgent]);
    return newAgent;
  }, []);

  const updateAgent = useCallback(async (name: string, data: AgentUpdate) => {
    const updated = await agentService.updateAgent(name, data);
    setAgents((prev) => prev.map((a) => (a.name === name ? updated : a)));
    return updated;
  }, []);

  const deleteAgent = useCallback(async (name: string) => {
    await agentService.deleteAgent(name);
    setAgents((prev) => prev.filter((a) => a.name !== name));
  }, []);

  const updateAgentStatus = useCallback(async (name: string, status: AgentStatus) => {
    const updated = await agentService.updateAgentStatus(name, status);
    setAgents((prev) => prev.map((a) => (a.name === name ? updated : a)));
    return updated;
  }, []);

  const checkNameAvailable = useCallback(async (name: string) => {
    return agentService.checkNameAvailable(name);
  }, []);

  return {
    agents,
    loading,
    createAgent,
    updateAgent,
    deleteAgent,
    updateAgentStatus,
    checkNameAvailable,
    refetch: fetchAgents,
  };
}
