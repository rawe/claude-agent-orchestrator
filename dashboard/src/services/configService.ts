import { agentOrchestratorApi } from './api';

export interface ConfigImportResponse {
  message: string;
  agents_imported: number;
  capabilities_imported: number;
  agents_replaced: number;
  capabilities_replaced: number;
}

export const configService = {
  /**
   * Export current configuration as a tar.gz archive.
   * Returns a Blob that can be downloaded.
   */
  async exportConfig(): Promise<Blob> {
    const response = await agentOrchestratorApi.get('/config/export', {
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Import configuration from a tar.gz archive.
   * WARNING: This replaces all existing agents and capabilities.
   */
  async importConfig(file: File): Promise<ConfigImportResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await agentOrchestratorApi.post('/config/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  },
};
