import { useSSE } from '@/contexts';
import { useAuth0 } from '@auth0/auth0-react';
import { Wifi, WifiOff, RefreshCw, LogIn, LogOut, User } from 'lucide-react';

const auth0Configured = !!(import.meta.env.VITE_AUTH0_DOMAIN && import.meta.env.VITE_AUTH0_CLIENT_ID);

export function Header() {
  const { connected, reconnect } = useSSE();

  // Only use Auth0 hook if configured (avoids error when not wrapped in provider)
  const auth0 = auth0Configured ? useAuth0() : null;
  const { isAuthenticated, isLoading, user, loginWithRedirect, logout } = auth0 || {};

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 flex-shrink-0">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
          <span className="text-white font-bold text-sm">AO</span>
        </div>
        <h1 className="text-lg font-semibold text-gray-900">Agent Orchestrator Framework</h1>
      </div>

      <div className="flex items-center gap-4">
        {/* Connection status */}
        <div
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm ${
            connected ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
          }`}
        >
          {connected ? (
            <>
              <Wifi className="w-4 h-4" />
              <span>Connected</span>
            </>
          ) : (
            <>
              <WifiOff className="w-4 h-4" />
              <span>Disconnected</span>
              <button
                onClick={reconnect}
                className="ml-1 p-1 hover:bg-red-100 rounded"
                title="Reconnect"
              >
                <RefreshCw className="w-3 h-3" />
              </button>
            </>
          )}
        </div>

        {/* Auth0 login/logout (only if configured) */}
        {auth0Configured && (
          <div className="flex items-center gap-2">
            {isLoading ? (
              <span className="text-sm text-gray-500">Loading...</span>
            ) : isAuthenticated && user ? (
              <>
                <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 rounded-full">
                  {user.picture ? (
                    <img src={user.picture} alt="" className="w-5 h-5 rounded-full" />
                  ) : (
                    <User className="w-4 h-4 text-gray-600" />
                  )}
                  <span className="text-sm text-gray-700">{user.name || user.email}</span>
                </div>
                <button
                  onClick={() => logout?.({ logoutParams: { returnTo: window.location.origin } })}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-full"
                  title="Logout"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </>
            ) : (
              <button
                onClick={() => loginWithRedirect?.()}
                className="flex items-center gap-2 px-3 py-1.5 text-sm bg-primary-600 text-white hover:bg-primary-700 rounded-full"
              >
                <LogIn className="w-4 h-4" />
                <span>Login</span>
              </button>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
