import { useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { setTokenGetter } from '../../services/auth';

/**
 * Bridges Auth0 React SDK with our auth service.
 * Must be rendered inside Auth0Provider.
 */
export function Auth0TokenProvider({ children }: { children: React.ReactNode }) {
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();

  useEffect(() => {
    if (isAuthenticated) {
      // Register the token getter so axios interceptors can use it
      setTokenGetter(getAccessTokenSilently);
    }
  }, [isAuthenticated, getAccessTokenSilently]);

  return <>{children}</>;
}
