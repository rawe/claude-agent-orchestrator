import { useWebSocket } from '@/contexts';
import { Wifi, WifiOff, RefreshCw } from 'lucide-react';

export function Header() {
  const { connected, reconnect } = useWebSocket();

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 flex-shrink-0">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
          <span className="text-white font-bold text-sm">AO</span>
        </div>
        <h1 className="text-lg font-semibold text-gray-900">Agent Orchestrator Framework</h1>
      </div>

      <div className="flex items-center gap-4">
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
      </div>
    </header>
  );
}
