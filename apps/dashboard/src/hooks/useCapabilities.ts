import { useState, useEffect, useCallback } from 'react';
import { useNotification } from '@/contexts';
import { capabilityService } from '@/services/capabilityService';
import type { Capability, CapabilitySummary, CapabilityCreate, CapabilityUpdate } from '@/types/capability';

export function useCapabilities() {
  const [capabilities, setCapabilities] = useState<CapabilitySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const { showError } = useNotification();

  const fetchCapabilities = useCallback(async () => {
    setLoading(true);
    try {
      const data = await capabilityService.getCapabilities();
      setCapabilities(data);
    } catch (err) {
      showError('Failed to load capabilities');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [showError]);

  useEffect(() => {
    fetchCapabilities();
  }, [fetchCapabilities]);

  const getCapability = useCallback(async (name: string): Promise<Capability> => {
    return capabilityService.getCapability(name);
  }, []);

  const createCapability = useCallback(async (data: CapabilityCreate): Promise<Capability> => {
    const newCapability = await capabilityService.createCapability(data);
    // Refetch to update the list with summary data
    await fetchCapabilities();
    return newCapability;
  }, [fetchCapabilities]);

  const updateCapability = useCallback(async (name: string, data: CapabilityUpdate): Promise<Capability> => {
    const updated = await capabilityService.updateCapability(name, data);
    // Refetch to update the list with summary data
    await fetchCapabilities();
    return updated;
  }, [fetchCapabilities]);

  const deleteCapability = useCallback(async (name: string) => {
    await capabilityService.deleteCapability(name);
    setCapabilities((prev) => prev.filter((c) => c.name !== name));
  }, []);

  const checkNameAvailable = useCallback(async (name: string) => {
    return capabilityService.checkNameAvailable(name);
  }, []);

  return {
    capabilities,
    loading,
    getCapability,
    createCapability,
    updateCapability,
    deleteCapability,
    checkNameAvailable,
    refetch: fetchCapabilities,
  };
}
