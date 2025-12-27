import { RouterProvider } from 'react-router-dom';
import { Auth0Provider } from '@auth0/auth0-react';
import { SSEProvider, NotificationProvider, ChatProvider, SessionsProvider } from '@/contexts';
import { Auth0TokenProvider } from '@/components/auth/Auth0TokenProvider';
import { AuthGuard } from '@/components/auth/AuthGuard';
import { router } from './router';

const auth0Domain = import.meta.env.VITE_AUTH0_DOMAIN;
const auth0ClientId = import.meta.env.VITE_AUTH0_CLIENT_ID;
const auth0Audience = import.meta.env.VITE_AUTH0_AUDIENCE;

// Auth0 is configured for login
const auth0Enabled = !!(auth0Domain && auth0ClientId);
// API requires authentication (audience set = API needs tokens)
const authRequired = !!(auth0Enabled && auth0Audience);

function App() {
  const content = (
    <NotificationProvider>
      <SSEProvider>
        <SessionsProvider>
          <ChatProvider>
            <RouterProvider router={router} />
          </ChatProvider>
        </SessionsProvider>
      </SSEProvider>
    </NotificationProvider>
  );

  // Only wrap with Auth0 if configured
  if (auth0Enabled) {
    // Wrap content with AuthGuard only if API auth is required
    const guardedContent = authRequired ? <AuthGuard>{content}</AuthGuard> : content;

    return (
      <Auth0Provider
        domain={auth0Domain}
        clientId={auth0ClientId}
        authorizationParams={{
          redirect_uri: window.location.origin,
          ...(auth0Audience && { audience: auth0Audience }),
        }}
      >
        <Auth0TokenProvider>
          {guardedContent}
        </Auth0TokenProvider>
      </Auth0Provider>
    );
  }

  return content;
}

export default App;
