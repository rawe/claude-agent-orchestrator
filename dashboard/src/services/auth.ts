/**
 * Auth service for managing access tokens.
 *
 * This module bridges Auth0's React hooks with axios interceptors.
 * The token getter is set during app initialization when Auth0 is ready.
 */

type TokenGetter = () => Promise<string>;
type TokenReadyCallback = () => void;

let getAccessToken: TokenGetter | null = null;
let tokenReadyCallbacks: TokenReadyCallback[] = [];

/**
 * Set the token getter function (called from Auth0 context).
 */
export function setTokenGetter(getter: TokenGetter) {
  getAccessToken = getter;
  // Notify all waiting subscribers that token is ready
  tokenReadyCallbacks.forEach(cb => cb());
  tokenReadyCallbacks = [];
}

/**
 * Check if token getter is ready.
 */
export function isTokenGetterReady(): boolean {
  return getAccessToken !== null;
}

/**
 * Wait for token getter to be set.
 * Resolves immediately if already set.
 */
export function waitForTokenReady(): Promise<void> {
  if (getAccessToken !== null) {
    return Promise.resolve();
  }
  return new Promise(resolve => {
    tokenReadyCallbacks.push(resolve);
  });
}

/**
 * Get the current access token, if available.
 * Returns null if Auth0 is not configured or user is not authenticated.
 */
export async function fetchAccessToken(): Promise<string | null> {
  if (!getAccessToken) {
    return null;
  }
  try {
    return await getAccessToken();
  } catch {
    // User not authenticated or token expired
    return null;
  }
}

/**
 * Check if OIDC auth is configured.
 */
export function isOidcConfigured(): boolean {
  return !!(
    import.meta.env.VITE_AUTH0_DOMAIN &&
    import.meta.env.VITE_AUTH0_CLIENT_ID &&
    import.meta.env.VITE_AUTH0_AUDIENCE
  );
}
