/**
 * Injected Script for Bug Spotter Browser Extension
 * Runs in the page's JavaScript context to intercept console output
 *
 * This script is injected into the page via a <script> tag to access
 * the page's console object directly.
 */

(function() {
  'use strict';

  // Store original console methods
  const originalConsole = {
    log: console.log.bind(console),
    warn: console.warn.bind(console),
    error: console.error.bind(console),
    info: console.info.bind(console),
    debug: console.debug.bind(console),
    trace: console.trace.bind(console)
  };

  /**
   * Serialize a value for transmission
   * Handles circular references and non-serializable objects
   */
  function serializeArg(arg, depth = 0) {
    if (depth > 3) return '[Max depth exceeded]';

    if (arg === null) return null;
    if (arg === undefined) return 'undefined';

    const type = typeof arg;

    if (type === 'string' || type === 'number' || type === 'boolean') {
      return arg;
    }

    if (type === 'function') {
      return `[Function: ${arg.name || 'anonymous'}]`;
    }

    if (type === 'symbol') {
      return arg.toString();
    }

    if (arg instanceof Error) {
      return {
        name: arg.name,
        message: arg.message,
        stack: arg.stack
      };
    }

    if (arg instanceof Date) {
      return arg.toISOString();
    }

    if (arg instanceof RegExp) {
      return arg.toString();
    }

    if (Array.isArray(arg)) {
      try {
        return arg.slice(0, 100).map(item => serializeArg(item, depth + 1));
      } catch {
        return '[Array]';
      }
    }

    if (arg instanceof HTMLElement) {
      return `[HTMLElement: ${arg.tagName.toLowerCase()}${arg.id ? '#' + arg.id : ''}${arg.className ? '.' + arg.className.split(' ').join('.') : ''}]`;
    }

    if (arg instanceof NodeList || arg instanceof HTMLCollection) {
      return `[NodeList: ${arg.length} items]`;
    }

    if (type === 'object') {
      try {
        // Check for circular reference by attempting JSON stringify
        const seen = new WeakSet();
        const safeObj = {};
        const keys = Object.keys(arg).slice(0, 50);

        for (const key of keys) {
          try {
            const val = arg[key];
            if (typeof val === 'object' && val !== null) {
              if (seen.has(val)) {
                safeObj[key] = '[Circular]';
              } else {
                seen.add(val);
                safeObj[key] = serializeArg(val, depth + 1);
              }
            } else {
              safeObj[key] = serializeArg(val, depth + 1);
            }
          } catch {
            safeObj[key] = '[Unable to serialize]';
          }
        }

        if (Object.keys(arg).length > 50) {
          safeObj['...'] = `[${Object.keys(arg).length - 50} more properties]`;
        }

        return safeObj;
      } catch {
        return '[Object]';
      }
    }

    return String(arg);
  }

  /**
   * Create an interceptor for a console method
   */
  function createInterceptor(level) {
    return function(...args) {
      // Call the original method
      originalConsole[level](...args);

      // Serialize arguments and send to content script
      try {
        const serializedArgs = args.map(arg => serializeArg(arg));

        window.postMessage({
          type: 'CONTEXT_STORE_CONSOLE',
          level: level,
          args: serializedArgs,
          timestamp: new Date().toISOString()
        }, '*');
      } catch (error) {
        // Don't let our code break the page's console
        originalConsole.error('[Bug Spotter] Error serializing console output:', error);
      }
    };
  }

  // Override console methods
  console.log = createInterceptor('log');
  console.warn = createInterceptor('warn');
  console.error = createInterceptor('error');
  console.info = createInterceptor('info');
  console.debug = createInterceptor('debug');
  console.trace = createInterceptor('trace');

  // Also capture unhandled errors
  window.addEventListener('error', (event) => {
    window.postMessage({
      type: 'CONTEXT_STORE_CONSOLE',
      level: 'error',
      args: [{
        name: 'UncaughtError',
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno
      }],
      timestamp: new Date().toISOString()
    }, '*');
  });

  // Capture unhandled promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    window.postMessage({
      type: 'CONTEXT_STORE_CONSOLE',
      level: 'error',
      args: [{
        name: 'UnhandledPromiseRejection',
        message: event.reason?.message || String(event.reason),
        stack: event.reason?.stack
      }],
      timestamp: new Date().toISOString()
    }, '*');
  });
})();
