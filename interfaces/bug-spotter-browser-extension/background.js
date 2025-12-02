/**
 * Background Service Worker for Bug Spotter Browser Extension
 * Handles communication with the Context Store API
 */

// Default API configuration
const DEFAULT_CONFIG = {
  baseUrl: 'http://localhost:8766',
  timeout: 30000
};

// Get configuration from storage or use defaults
async function getConfig() {
  const result = await chrome.storage.local.get(['contextStoreConfig']);
  return { ...DEFAULT_CONFIG, ...result.contextStoreConfig };
}

// Save configuration to storage
async function saveConfig(config) {
  await chrome.storage.local.set({ contextStoreConfig: config });
}

/**
 * Push a document to the Context Store API
 * @param {Object} data - Document data to push
 * @param {string} data.content - Document content (HTML string)
 * @param {string} data.filename - Filename for the document
 * @param {string[]} data.tags - Tags for the document
 * @param {Object} data.metadata - Metadata object
 * @returns {Promise<Object>} API response
 */
async function pushDocument(data) {
  const config = await getConfig();

  // Create form data
  const formData = new FormData();

  // Create a blob from the content
  // Detect content type from filename
  const contentType = data.filename.endsWith('.md') ? 'text/markdown' : 'text/html';
  const blob = new Blob([data.content], { type: contentType });
  formData.append('file', blob, data.filename);

  // Add tags if provided
  if (data.tags && data.tags.length > 0) {
    formData.append('tags', data.tags.join(','));
  }

  // Add metadata if provided
  if (data.metadata) {
    formData.append('metadata', JSON.stringify(data.metadata));
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), config.timeout);

  try {
    const response = await fetch(`${config.baseUrl}/documents`, {
      method: 'POST',
      body: formData,
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    return await response.json();
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new Error('Request timeout');
    }
    throw error;
  }
}

/**
 * Check if the Context Store server is reachable
 * @returns {Promise<boolean>}
 */
async function checkServerHealth() {
  const config = await getConfig();

  try {
    const response = await fetch(`${config.baseUrl}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000)
    });
    return response.ok;
  } catch {
    return false;
  }
}

// Message handler for communication with popup and content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'PUSH_DOCUMENT') {
    pushDocument(message.data)
      .then(result => sendResponse({ success: true, data: result }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; // Keep channel open for async response
  }

  if (message.type === 'CHECK_SERVER') {
    checkServerHealth()
      .then(healthy => sendResponse({ healthy }))
      .catch(() => sendResponse({ healthy: false }));
    return true;
  }

  if (message.type === 'GET_CONFIG') {
    getConfig()
      .then(config => sendResponse({ config }))
      .catch(error => sendResponse({ error: error.message }));
    return true;
  }

  if (message.type === 'SAVE_CONFIG') {
    saveConfig(message.config)
      .then(() => sendResponse({ success: true }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }
});

// Log when service worker starts
console.log('[Bug Spotter] Background service worker started');
