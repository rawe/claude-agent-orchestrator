/**
 * Test configuration for the Context Store SDK.
 *
 * The base URL can be configured via the CONTEXT_STORE_URL environment variable.
 * Defaults to http://localhost:8766 for local development.
 */
export const TEST_BASE_URL = process.env.CONTEXT_STORE_URL || 'http://localhost:8766';
