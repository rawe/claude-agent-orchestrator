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
 * Push an image document to the Context Store API
 * @param {Object} data - Image data to push
 * @param {Blob} data.imageBlob - Image blob data
 * @param {string} data.filename - Filename for the image
 * @param {string[]} data.tags - Tags for the document
 * @param {Object} data.metadata - Metadata object
 * @returns {Promise<Object>} API response
 */
async function pushImageDocument(data) {
  const config = await getConfig();

  // Create form data
  const formData = new FormData();
  formData.append('file', data.imageBlob, data.filename);

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
 * Create a relation between two documents
 * @param {Object} data - Relation data
 * @param {string} data.definition - Relation type: "parent-child" or "related"
 * @param {string} data.fromDocumentId - Parent/source document ID
 * @param {string} data.toDocumentId - Child/target document ID
 * @param {string} [data.fromNote] - Note for parent document
 * @param {string} [data.toNote] - Note for child document
 * @returns {Promise<Object>} API response
 */
async function createRelation(data) {
  const config = await getConfig();

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), config.timeout);

  try {
    const response = await fetch(`${config.baseUrl}/relations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        definition: data.definition,
        from_document_id: data.fromDocumentId,
        to_document_id: data.toDocumentId,
        from_note: data.fromNote || null,
        to_note: data.toNote || null
      }),
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
 * Capture a screenshot of the current tab
 * @param {number} tabId - The tab ID to capture
 * @returns {Promise<string>} Base64 data URL of the screenshot
 */
async function captureScreenshot(tabId) {
  try {
    // captureVisibleTab requires the activeTab permission, which is granted when popup opens
    const dataUrl = await chrome.tabs.captureVisibleTab(null, {
      format: 'png',
      quality: 100
    });
    return dataUrl;
  } catch (error) {
    console.error('[Bug Spotter] Screenshot capture failed:', error);
    throw new Error('Failed to capture screenshot: ' + error.message);
  }
}

/**
 * Convert a base64 data URL to a Blob
 * @param {string} dataUrl - The data URL to convert
 * @returns {Blob} The converted Blob
 */
function dataUrlToBlob(dataUrl) {
  const parts = dataUrl.split(',');
  const mime = parts[0].match(/:(.*?);/)[1];
  const bstr = atob(parts[1]);
  let n = bstr.length;
  const u8arr = new Uint8Array(n);
  while (n--) {
    u8arr[n] = bstr.charCodeAt(n);
  }
  return new Blob([u8arr], { type: mime });
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

  if (message.type === 'PUSH_IMAGE_DOCUMENT') {
    // Convert base64 data URL to Blob
    const imageBlob = dataUrlToBlob(message.data.imageDataUrl);
    pushImageDocument({
      imageBlob: imageBlob,
      filename: message.data.filename,
      tags: message.data.tags,
      metadata: message.data.metadata
    })
      .then(result => sendResponse({ success: true, data: result }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }

  if (message.type === 'CREATE_RELATION') {
    createRelation(message.data)
      .then(result => sendResponse({ success: true, data: result }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }

  if (message.type === 'CAPTURE_SCREENSHOT') {
    captureScreenshot(message.tabId)
      .then(dataUrl => sendResponse({ success: true, dataUrl: dataUrl }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
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
