/**
 * Popup Script for Bug Spotter Browser Extension
 * Handles UI interactions, element selection, and data upload
 */

// Use browser API for cross-browser compatibility
const browserAPI = typeof browser !== 'undefined' ? browser : chrome;

// DOM Elements
const elements = {
  serverStatus: document.getElementById('server-status'),
  pageDomain: document.getElementById('page-domain'),
  noElementSelected: document.getElementById('no-element-selected'),
  elementSelected: document.getElementById('element-selected'),
  selectElementBtn: document.getElementById('select-element-btn'),
  reselectBtn: document.getElementById('reselect-btn'),
  clearElementBtn: document.getElementById('clear-element-btn'),
  elementSelector: document.getElementById('element-selector'),
  elementTag: document.getElementById('element-tag'),
  selectorValid: document.getElementById('selector-valid'),
  selectorInvalid: document.getElementById('selector-invalid'),
  copySelectorBtn: document.getElementById('copy-selector-btn'),
  includeScreenshot: document.getElementById('include-screenshot'),
  includeHtml: document.getElementById('include-html'),
  includeConsole: document.getElementById('include-console'),
  includeMetadata: document.getElementById('include-metadata'),
  consoleCountBadge: document.getElementById('console-count-badge'),
  tagsInput: document.getElementById('tags-input'),
  tagsList: document.getElementById('tags-list'),
  comment: document.getElementById('comment'),
  pushBtn: document.getElementById('push-btn'),
  result: document.getElementById('result'),
  settingsBtn: document.getElementById('settings-btn'),
  settingsPanel: document.getElementById('settings-panel'),
  serverUrl: document.getElementById('server-url'),
  connectionStatus: document.getElementById('connection-status'),
  saveSettings: document.getElementById('save-settings'),
  cancelSettings: document.getElementById('cancel-settings')
};

// State
let tags = [];
let currentTab = null;
let selectedElementData = null;
let serverConnected = false;

/**
 * Ensure content script is injected into the current tab
 */
async function ensureContentScriptInjected() {
  try {
    // Try to ping the content script
    await browserAPI.tabs.sendMessage(currentTab.id, { type: 'PING' });
    return true;
  } catch {
    // Content script not loaded, inject it
    try {
      await browserAPI.scripting.executeScript({
        target: { tabId: currentTab.id },
        files: ['content.js']
      });
      // Give it a moment to initialize
      await new Promise(resolve => setTimeout(resolve, 100));
      return true;
    } catch (injectError) {
      console.error('Failed to inject content script:', injectError);
      return false;
    }
  }
}

/**
 * Initialize the popup
 */
async function init() {
  // Get current tab
  const tabs = await browserAPI.tabs.query({ active: true, currentWindow: true });
  currentTab = tabs[0];

  if (!currentTab) {
    showError('No active tab found');
    return;
  }

  // Update page domain in header
  try {
    const url = new URL(currentTab.url);
    elements.pageDomain.textContent = url.hostname;
    elements.pageDomain.title = currentTab.url;
  } catch {
    elements.pageDomain.textContent = '-';
  }

  // Check server status
  await checkServerStatus();

  // Get page info including console count and element status
  await refreshPageInfo();

  // Load settings
  loadSettings();

  // Set up event listeners
  setupEventListeners();

  // Add default tags
  addTag('bug-report');
  try {
    const url = new URL(currentTab.url);
    addTag(url.hostname);
  } catch {
    // Ignore invalid URLs
  }

  // Listen for element selection messages from content script
  browserAPI.runtime.onMessage.addListener((message) => {
    if (message.type === 'ELEMENT_SELECTED') {
      handleElementSelected(message.data);
    }
  });
}

/**
 * Refresh page info from content script
 */
async function refreshPageInfo() {
  try {
    // First check if content script is available
    const injected = await ensureContentScriptInjected();
    if (!injected) {
      elements.consoleCountBadge.textContent = '0';
      return;
    }

    const response = await browserAPI.tabs.sendMessage(currentTab.id, { type: 'GET_PAGE_INFO' });
    if (response.success) {
      elements.consoleCountBadge.textContent = response.data.consoleLogCount || 0;

      if (response.data.hasSelectedElement) {
        // Get the selected element data
        const elementResponse = await browserAPI.tabs.sendMessage(currentTab.id, { type: 'GET_SELECTED_ELEMENT' });
        if (elementResponse.data) {
          handleElementSelected(elementResponse.data);
        }
      }
    }
  } catch {
    // Content script might not be loaded yet
    elements.consoleCountBadge.textContent = '0';
  }
}

/**
 * Check if the Context Store server is reachable
 */
async function checkServerStatus() {
  elements.serverStatus.className = 'status-indicator checking';
  updateConnectionStatus('checking', 'Checking...');

  try {
    const response = await browserAPI.runtime.sendMessage({ type: 'CHECK_SERVER' });

    if (response.healthy) {
      elements.serverStatus.className = 'status-indicator connected';
      updateConnectionStatus('connected', 'Connected');
      serverConnected = true;
    } else {
      elements.serverStatus.className = 'status-indicator disconnected';
      updateConnectionStatus('disconnected', 'Disconnected');
      serverConnected = false;
    }
  } catch {
    elements.serverStatus.className = 'status-indicator disconnected';
    updateConnectionStatus('disconnected', 'Error');
    serverConnected = false;
  }

  updatePushButton();
}

/**
 * Update connection status in settings panel
 */
function updateConnectionStatus(status, label) {
  if (elements.connectionStatus) {
    elements.connectionStatus.className = `connection-status ${status}`;
    const labelEl = elements.connectionStatus.querySelector('.status-label');
    if (labelEl) {
      labelEl.textContent = label;
    }
  }
}

/**
 * Load settings from storage
 */
async function loadSettings() {
  try {
    const response = await browserAPI.runtime.sendMessage({ type: 'GET_CONFIG' });
    if (response.config) {
      elements.serverUrl.value = response.config.baseUrl || 'http://localhost:8766';
    }
  } catch {
    elements.serverUrl.value = 'http://localhost:8766';
  }
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
  // Element selection
  elements.selectElementBtn.addEventListener('click', startElementSelection);
  elements.reselectBtn.addEventListener('click', startElementSelection);
  elements.clearElementBtn.addEventListener('click', clearSelectedElement);
  elements.copySelectorBtn.addEventListener('click', copySelector);

  // Tags input
  elements.tagsInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const value = elements.tagsInput.value.trim().replace(/,/g, '');
      if (value) {
        addTag(value);
        elements.tagsInput.value = '';
      }
    }
  });

  elements.tagsInput.addEventListener('blur', () => {
    const value = elements.tagsInput.value.trim().replace(/,/g, '');
    if (value) {
      addTag(value);
      elements.tagsInput.value = '';
    }
  });

  // Push button
  elements.pushBtn.addEventListener('click', pushToContextStore);

  // Settings
  elements.settingsBtn.addEventListener('click', () => {
    elements.settingsPanel.classList.remove('hidden');
  });

  elements.cancelSettings.addEventListener('click', () => {
    elements.settingsPanel.classList.add('hidden');
    loadSettings();
  });

  elements.saveSettings.addEventListener('click', async () => {
    const config = {
      baseUrl: elements.serverUrl.value.trim() || 'http://localhost:8766'
    };

    try {
      await browserAPI.runtime.sendMessage({ type: 'SAVE_CONFIG', config });
      elements.settingsPanel.classList.add('hidden');
      checkServerStatus();
    } catch (error) {
      showError('Failed to save settings: ' + error.message);
    }
  });
}

/**
 * Start element selection mode
 */
async function startElementSelection() {
  try {
    // Ensure content script is available
    const injected = await ensureContentScriptInjected();
    if (!injected) {
      showError('Cannot run on this page. Try a regular webpage.');
      return;
    }

    // Start selection mode
    await browserAPI.tabs.sendMessage(currentTab.id, { type: 'START_ELEMENT_SELECTION' });

    // Close popup to allow user to interact with the page
    window.close();
  } catch (error) {
    showError('Failed to start element selection: ' + error.message);
  }
}

/**
 * Handle element selection result
 */
function handleElementSelected(data) {
  if (!data) {
    // Selection was cancelled
    return;
  }

  selectedElementData = data;

  // Update UI
  elements.noElementSelected.classList.add('hidden');
  elements.elementSelected.classList.remove('hidden');

  elements.elementSelector.textContent = data.selector;
  elements.elementTag.textContent = `<${data.tagName}>`;

  // Show selector validity
  if (data.selectorValid) {
    elements.selectorValid.classList.remove('hidden');
    elements.selectorInvalid.classList.add('hidden');
  } else {
    elements.selectorValid.classList.add('hidden');
    elements.selectorInvalid.classList.remove('hidden');
  }

  updatePushButton();
}

/**
 * Clear selected element
 */
async function clearSelectedElement() {
  try {
    await browserAPI.tabs.sendMessage(currentTab.id, { type: 'CLEAR_SELECTED_ELEMENT' });
  } catch {
    // Ignore errors
  }

  selectedElementData = null;

  elements.noElementSelected.classList.remove('hidden');
  elements.elementSelected.classList.add('hidden');

  updatePushButton();
}

/**
 * Copy selector to clipboard
 */
async function copySelector() {
  if (!selectedElementData?.selector) return;

  try {
    await navigator.clipboard.writeText(selectedElementData.selector);

    // Show feedback
    const originalTitle = elements.copySelectorBtn.title;
    elements.copySelectorBtn.title = 'Copied!';
    setTimeout(() => {
      elements.copySelectorBtn.title = originalTitle;
    }, 2000);
  } catch {
    showError('Failed to copy selector');
  }
}

/**
 * Update push button state
 */
function updatePushButton() {
  const canPush = serverConnected && selectedElementData !== null;
  elements.pushBtn.disabled = !canPush;
}

/**
 * Add a tag to the list
 */
function addTag(tag) {
  tag = tag.toLowerCase().trim();
  if (!tag || tags.includes(tag)) return;

  tags.push(tag);
  renderTags();
}

/**
 * Remove a tag from the list
 */
function removeTag(tag) {
  tags = tags.filter(t => t !== tag);
  renderTags();
}

/**
 * Render tags in the UI
 */
function renderTags() {
  elements.tagsList.innerHTML = tags.map(tag => `
    <span class="tag">
      ${escapeHtml(tag)}
      <span class="tag-remove" data-tag="${escapeHtml(tag)}">&times;</span>
    </span>
  `).join('');

  // Add remove listeners
  elements.tagsList.querySelectorAll('.tag-remove').forEach(el => {
    el.addEventListener('click', () => removeTag(el.dataset.tag));
  });
}

/**
 * Capture screenshot of the full visible tab
 * Full tab screenshot provides better context for bug reports
 * @returns {Promise<string>} Screenshot data URL
 */
async function captureFullTabScreenshot() {
  const screenshotResponse = await browserAPI.runtime.sendMessage({
    type: 'CAPTURE_SCREENSHOT',
    tabId: currentTab.id
  });

  if (!screenshotResponse.success) {
    throw new Error(screenshotResponse.error || 'Failed to capture screenshot');
  }

  return screenshotResponse.dataUrl;
}

/**
 * Push data to Context Store
 */
async function pushToContextStore() {
  if (!selectedElementData) {
    showError('No element selected');
    return;
  }

  elements.pushBtn.disabled = true;
  elements.pushBtn.classList.add('loading');
  hideResult();

  try {
    // Get capture data from content script
    const options = {
      includeHtml: elements.includeHtml.checked,
      includeConsole: elements.includeConsole.checked,
      includeMetadata: elements.includeMetadata.checked
    };

    const captureResponse = await browserAPI.tabs.sendMessage(currentTab.id, {
      type: 'CAPTURE_DATA',
      options: options
    });

    if (!captureResponse.success) {
      throw new Error(captureResponse.error || 'Failed to capture data');
    }

    const capturedData = captureResponse.data;

    // Build the document content
    const documentContent = buildDocumentContent(capturedData);

    // Generate filename based on selector
    const filename = generateFilename(selectedElementData.selector, capturedData.title);

    // Build metadata
    const metadata = {
      source_url: capturedData.url,
      source_domain: capturedData.domain,
      captured_at: capturedData.capturedAt,
      css_selector: selectedElementData.selector,
      element_tag: selectedElementData.tagName
    };

    if (elements.comment.value.trim()) {
      metadata.description = elements.comment.value.trim();
    }

    if (options.includeMetadata && capturedData.systemMetadata) {
      metadata.browser = capturedData.systemMetadata.browser;
      metadata.browser_version = capturedData.systemMetadata.browserVersion;
      metadata.os = capturedData.systemMetadata.os;
      metadata.viewport = `${capturedData.systemMetadata.viewportWidth}x${capturedData.systemMetadata.viewportHeight}`;
    }

    // Push main report to Context Store
    const pushResponse = await browserAPI.runtime.sendMessage({
      type: 'PUSH_DOCUMENT',
      data: {
        content: documentContent,
        filename: filename,
        tags: tags,
        metadata: metadata
      }
    });

    if (!pushResponse.success) {
      throw new Error(pushResponse.error || 'Failed to push document');
    }

    const reportId = pushResponse.data.id;
    let screenshotId = null;

    // Handle screenshot if enabled
    if (elements.includeScreenshot.checked) {
      try {
        // Capture full visible tab screenshot (provides better context for bug reports)
        const screenshotDataUrl = await captureFullTabScreenshot();

        // Generate screenshot filename
        const screenshotFilename = filename.replace('.md', '-screenshot.png');

        // Build screenshot metadata
        const screenshotMetadata = {
          source_url: capturedData.url,
          source_domain: capturedData.domain,
          captured_at: capturedData.capturedAt,
          css_selector: selectedElementData.selector,
          element_tag: selectedElementData.tagName,
          parent_report_id: reportId
        };

        // Push screenshot to Context Store
        const screenshotResponse = await browserAPI.runtime.sendMessage({
          type: 'PUSH_IMAGE_DOCUMENT',
          data: {
            imageDataUrl: screenshotDataUrl,
            filename: screenshotFilename,
            tags: [...tags, 'screenshot'],
            metadata: screenshotMetadata
          }
        });

        if (screenshotResponse.success) {
          screenshotId = screenshotResponse.data.id;

          // Create parent-child relation between report and screenshot
          const relationResponse = await browserAPI.runtime.sendMessage({
            type: 'CREATE_RELATION',
            data: {
              definition: 'parent-child',
              fromDocumentId: reportId,
              toDocumentId: screenshotId,
              fromNote: 'Bug report with screenshot attachment',
              toNote: 'Screenshot of selected element'
            }
          });

          if (!relationResponse.success) {
            console.warn('[Bug Spotter] Failed to create relation:', relationResponse.error);
          }
        } else {
          console.warn('[Bug Spotter] Failed to upload screenshot:', screenshotResponse.error);
        }
      } catch (screenshotError) {
        console.warn('[Bug Spotter] Screenshot capture failed:', screenshotError.message);
        // Continue without screenshot - main report was already uploaded
      }
    }

    // Show success message with both IDs
    if (screenshotId) {
      showSuccess(`Report submitted!<span class="doc-id">Report ID: ${reportId}</span><span class="doc-id">Screenshot ID: ${screenshotId}</span>`);
    } else {
      showSuccess(`Report submitted!<span class="doc-id">ID: ${reportId}</span>`);
    }

  } catch (error) {
    showError(error.message);
  } finally {
    elements.pushBtn.disabled = false;
    elements.pushBtn.classList.remove('loading');
    updatePushButton();
  }
}

/**
 * Build the document content as Markdown
 */
function buildDocumentContent(data) {
  const parts = [];

  // Title
  parts.push(`# Bug Report: ${data.title}`);
  parts.push('');

  // Basic info
  parts.push('## Page Information');
  parts.push(`- **URL:** ${data.url}`);
  parts.push(`- **Captured:** ${data.capturedAt}`);
  parts.push('');

  // Selected element
  if (data.selectedElement) {
    parts.push('## Selected Element');
    parts.push('');
    parts.push('### CSS Selector');
    parts.push('```css');
    parts.push(data.selectedElement.selector);
    parts.push('```');
    parts.push('');
    parts.push(`- **Tag:** \`<${data.selectedElement.tagName}>\``);
    parts.push(`- **Selector Valid:** ${data.selectedElement.selectorValid ? 'Yes' : 'No (may match multiple elements)'}`);
    parts.push('');

    // Include HTML if toggled
    if (data.selectedElement.outerHTML) {
      parts.push('### Element HTML');
      parts.push('```html');
      parts.push(data.selectedElement.outerHTML);
      parts.push('```');
      parts.push('');
    }
  }

  // Description/Comment
  if (elements.comment.value.trim()) {
    parts.push('## Description');
    parts.push(elements.comment.value.trim());
    parts.push('');
  }

  // Console logs
  if (data.consoleLogs && data.consoleLogs.length > 0) {
    parts.push('## Console Output');
    parts.push('');
    parts.push('```');
    data.consoleLogs.forEach(log => {
      const args = log.args.map(arg =>
        typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
      ).join(' ');
      parts.push(`[${log.level.toUpperCase()}] ${log.timestamp}`);
      parts.push(`  ${args}`);
    });
    parts.push('```');
    parts.push('');
  }

  // System metadata
  if (data.systemMetadata) {
    parts.push('## System Information');
    parts.push('');
    parts.push(`| Property | Value |`);
    parts.push(`|----------|-------|`);
    parts.push(`| Browser | ${data.systemMetadata.browser} ${data.systemMetadata.browserVersion} |`);
    parts.push(`| OS | ${data.systemMetadata.os} |`);
    parts.push(`| Screen | ${data.systemMetadata.screenWidth}x${data.systemMetadata.screenHeight} |`);
    parts.push(`| Viewport | ${data.systemMetadata.viewportWidth}x${data.systemMetadata.viewportHeight} |`);
    parts.push(`| DPR | ${data.systemMetadata.devicePixelRatio} |`);
    parts.push(`| Language | ${data.systemMetadata.language} |`);
    parts.push(`| Timezone | ${data.systemMetadata.timezone} |`);
    parts.push('');
  }

  return parts.join('\n');
}

/**
 * Generate a filename from selector and title
 */
function generateFilename(selector, title) {
  // Create a short identifier from the selector
  const selectorPart = selector
    .replace(/[^a-zA-Z0-9-_]/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .substring(0, 30);

  const titlePart = (title || 'report')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .substring(0, 20);

  const timestamp = new Date().toISOString().split('T')[0];

  return `${timestamp}-${titlePart}-${selectorPart}.md`;
}

/**
 * Show success message
 */
function showSuccess(message) {
  elements.result.className = 'result success';
  elements.result.innerHTML = message;
}

/**
 * Show error message
 */
function showError(message) {
  elements.result.className = 'result error';
  elements.result.textContent = message;
}

/**
 * Hide result message
 */
function hideResult() {
  elements.result.className = 'result hidden';
}

/**
 * Escape HTML special characters
 */
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);
