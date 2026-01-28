/**
 * Content Script for Bug Spotter Browser Extension
 * Handles element selection, console capture, and communication with popup
 */

// Storage for captured console logs
let consoleLogs = [];
const MAX_CONSOLE_LOGS = 1000;

// Storage for selected element data
let selectedElementData = null;

// Flag to track if selector script is injected
let selectorScriptInjected = false;

/**
 * Inject the console interceptor script into the page context
 */
function injectConsoleInterceptor() {
  const script = document.createElement('script');
  script.src = chrome.runtime.getURL('injected.js');
  script.onload = function() {
    this.remove();
  };
  (document.head || document.documentElement).appendChild(script);
}

/**
 * Inject the selector script into the page context
 */
function injectSelectorScript() {
  if (selectorScriptInjected) return Promise.resolve();

  return new Promise((resolve) => {
    const script = document.createElement('script');
    script.src = chrome.runtime.getURL('selector.js');
    script.onload = function() {
      selectorScriptInjected = true;
      resolve();
    };
    (document.head || document.documentElement).appendChild(script);
  });
}

// Listen for console messages from the injected script
window.addEventListener('message', (event) => {
  if (event.source !== window) return;

  if (event.data && event.data.type === 'CONTEXT_STORE_CONSOLE') {
    const logEntry = {
      level: event.data.level,
      args: event.data.args,
      timestamp: event.data.timestamp
    };

    consoleLogs.push(logEntry);

    // Limit the number of stored logs
    if (consoleLogs.length > MAX_CONSOLE_LOGS) {
      consoleLogs = consoleLogs.slice(-MAX_CONSOLE_LOGS);
    }
  }

  // Handle selection results from selector.js
  if (event.data && event.data.type === 'CONTEXT_STORE_SELECTION_RESULT') {
    selectedElementData = event.data.result;
    // Notify popup that selection is complete
    chrome.runtime.sendMessage({
      type: 'ELEMENT_SELECTED',
      data: selectedElementData
    }).catch(() => {
      // Popup might be closed, that's okay
    });
  }
});

// Inject console interceptor when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', injectConsoleInterceptor);
} else {
  injectConsoleInterceptor();
}

/**
 * Get system metadata
 * @returns {Object} System information
 */
function getSystemMetadata() {
  const ua = navigator.userAgent;

  // Parse browser info
  let browserName = 'Unknown';
  let browserVersion = 'Unknown';

  if (ua.includes('Firefox/')) {
    browserName = 'Firefox';
    browserVersion = ua.match(/Firefox\/(\d+\.\d+)/)?.[1] || 'Unknown';
  } else if (ua.includes('Edg/')) {
    browserName = 'Edge';
    browserVersion = ua.match(/Edg\/(\d+\.\d+)/)?.[1] || 'Unknown';
  } else if (ua.includes('Chrome/')) {
    browserName = 'Chrome';
    browserVersion = ua.match(/Chrome\/(\d+\.\d+)/)?.[1] || 'Unknown';
  } else if (ua.includes('Safari/') && !ua.includes('Chrome')) {
    browserName = 'Safari';
    browserVersion = ua.match(/Version\/(\d+\.\d+)/)?.[1] || 'Unknown';
  }

  // Parse OS info
  let os = 'Unknown';
  if (ua.includes('Windows NT 10')) os = 'Windows 10/11';
  else if (ua.includes('Windows')) os = 'Windows';
  else if (ua.includes('Mac OS X')) {
    const version = ua.match(/Mac OS X (\d+[._]\d+)/)?.[1]?.replace('_', '.') || '';
    os = `macOS ${version}`.trim();
  }
  else if (ua.includes('Linux')) os = 'Linux';
  else if (ua.includes('Android')) os = 'Android';
  else if (ua.includes('iOS') || ua.includes('iPhone') || ua.includes('iPad')) os = 'iOS';

  return {
    browser: browserName,
    browserVersion: browserVersion,
    os: os,
    userAgent: ua,
    screenWidth: window.screen.width,
    screenHeight: window.screen.height,
    viewportWidth: window.innerWidth,
    viewportHeight: window.innerHeight,
    devicePixelRatio: window.devicePixelRatio,
    language: navigator.language,
    platform: navigator.platform,
    colorDepth: window.screen.colorDepth,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
  };
}

/**
 * Get basic page info (without full HTML)
 * @returns {Object} Basic page metadata
 */
function getPageInfo() {
  return {
    url: window.location.href,
    domain: window.location.hostname,
    title: document.title || 'Untitled',
    capturedAt: new Date().toISOString()
  };
}

/**
 * Clear captured console logs
 */
function clearConsoleLogs() {
  consoleLogs = [];
}

/**
 * Clear selected element
 */
function clearSelectedElement() {
  selectedElementData = null;
}

/**
 * Start element selection mode
 */
async function startElementSelection() {
  await injectSelectorScript();

  // Small delay to ensure script is initialized
  await new Promise(resolve => setTimeout(resolve, 50));

  // Trigger selection mode via window message
  window.postMessage({ type: 'CONTEXT_STORE_START_SELECTION' }, '*');
}

// Listen for messages from the popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // Simple ping to check if content script is loaded
  if (message.type === 'PING') {
    sendResponse({ pong: true });
    return true;
  }

  if (message.type === 'START_ELEMENT_SELECTION') {
    startElementSelection()
      .then(() => sendResponse({ success: true }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }

  if (message.type === 'GET_SELECTED_ELEMENT') {
    sendResponse({ data: selectedElementData });
    return true;
  }

  if (message.type === 'CLEAR_SELECTED_ELEMENT') {
    clearSelectedElement();
    sendResponse({ success: true });
    return true;
  }

  if (message.type === 'GET_PAGE_INFO') {
    try {
      const pageInfo = getPageInfo();
      pageInfo.systemMetadata = getSystemMetadata();
      pageInfo.consoleLogCount = consoleLogs.length;
      pageInfo.hasSelectedElement = selectedElementData !== null;
      sendResponse({ success: true, data: pageInfo });
    } catch (error) {
      sendResponse({ success: false, error: error.message });
    }
    return true;
  }

  if (message.type === 'CAPTURE_DATA') {
    // Build capture data based on options
    try {
      const options = message.options || {};
      const data = {
        url: window.location.href,
        domain: window.location.hostname,
        title: document.title || 'Untitled',
        capturedAt: new Date().toISOString()
      };

      // Include selected element data
      if (selectedElementData) {
        data.selectedElement = {
          selector: selectedElementData.selector,
          tagName: selectedElementData.tagName,
          selectorValid: selectedElementData.selectorValid
        };

        // Optionally include HTML
        if (options.includeHtml) {
          data.selectedElement.outerHTML = selectedElementData.outerHTML;
          data.selectedElement.innerHTML = selectedElementData.innerHTML;
        }
      }

      // Include console logs if requested
      if (options.includeConsole) {
        data.consoleLogs = [...consoleLogs];
      }

      // Include system metadata if requested
      if (options.includeMetadata) {
        data.systemMetadata = getSystemMetadata();
      }

      sendResponse({ success: true, data: data });
    } catch (error) {
      sendResponse({ success: false, error: error.message });
    }
    return true;
  }

  if (message.type === 'GET_CONSOLE_LOGS') {
    sendResponse({ logs: [...consoleLogs] });
    return true;
  }

  if (message.type === 'CLEAR_CONSOLE_LOGS') {
    clearConsoleLogs();
    sendResponse({ success: true });
    return true;
  }

  if (message.type === 'GET_CONSOLE_LOG_COUNT') {
    sendResponse({ count: consoleLogs.length });
    return true;
  }
});

console.log('[Bug Spotter] Content script loaded');
