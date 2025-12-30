import { agentOrchestratorApi } from './api';
import type { Capability, CapabilitySummary, CapabilityCreate, CapabilityUpdate } from '@/types/capability';

export const capabilityService = {
  /**
   * Get all capabilities
   */
  async getCapabilities(): Promise<CapabilitySummary[]> {
    const response = await agentOrchestratorApi.get<CapabilitySummary[]>('/capabilities');
    return response.data;
  },

  /**
   * Get a single capability by name
   */
  async getCapability(name: string): Promise<Capability> {
    const response = await agentOrchestratorApi.get<Capability>(`/capabilities/${name}`);
    return response.data;
  },

  /**
   * Create a new capability
   */
  async createCapability(data: CapabilityCreate): Promise<Capability> {
    const response = await agentOrchestratorApi.post<Capability>('/capabilities', data);
    return response.data;
  },

  /**
   * Update an existing capability
   */
  async updateCapability(name: string, data: CapabilityUpdate): Promise<Capability> {
    const response = await agentOrchestratorApi.patch<Capability>(`/capabilities/${name}`, data);
    return response.data;
  },

  /**
   * Delete a capability
   */
  async deleteCapability(name: string): Promise<void> {
    await agentOrchestratorApi.delete(`/capabilities/${name}`);
  },

  /**
   * Check if capability name is available
   */
  async checkNameAvailable(name: string): Promise<boolean> {
    try {
      await agentOrchestratorApi.get(`/capabilities/${name}`);
      return false; // Capability exists
    } catch {
      return true; // 404 = name available
    }
  },
};
