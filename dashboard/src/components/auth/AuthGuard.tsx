import { useAuth0 } from '@auth0/auth0-react';
import { LogIn, AlertCircle } from 'lucide-react';

/**
 * Auth guard that blocks the app until user is authenticated.
 * Shows a login screen instead of the main app when not logged in.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, error, loginWithRedirect } = useAuth0();

  // Show loading state while Auth0 initializes
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-primary-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Show error if Auth0 had an issue
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full mx-4">
          <div className="text-center mb-6">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h1 className="text-xl font-bold text-gray-900 mb-2">
              Authentication Error
            </h1>
            <p className="text-gray-600 text-sm">
              {error.message}
            </p>
          </div>
          <button
            onClick={() => loginWithRedirect()}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
          >
            <LogIn className="w-5 h-5" />
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // Show login screen if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full mx-4">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-primary-600 rounded-xl flex items-center justify-center mx-auto mb-4">
              <span className="text-white font-bold text-2xl">AO</span>
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              Agent Orchestrator
            </h1>
            <p className="text-gray-600">
              Sign in to access the dashboard
            </p>
          </div>

          <button
            onClick={() => loginWithRedirect()}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
          >
            <LogIn className="w-5 h-5" />
            Sign in with Auth0
          </button>
        </div>
      </div>
    );
  }

  // User is authenticated, render children
  return <>{children}</>;
}
