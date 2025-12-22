/**
 * Auth service for managing access tokens.
 *
 * This module bridges Auth0's React hooks with axios interceptors.
 * The token getter is set during app initialization when Auth0 is ready.
 */

type TokenGetter = () => Promise<string>;

let getAccessToken: TokenGetter | null = null;

/**
 * Set the token getter function (called from Auth0 context).
 */
export function setTokenGetter(getter: TokenGetter) {
  getAccessToken = getter;
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
