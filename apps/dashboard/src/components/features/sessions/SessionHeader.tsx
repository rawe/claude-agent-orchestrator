import { Session } from '@/types';
import { StatusBadge, CopyButton } from '@/components/common';
import { formatRelativeTime, formatDuration } from '@/utils/formatters';
import { Clock, Folder, Bot } from 'lucide-react';
import { useState, useEffect } from 'react';

interface SessionHeaderProps {
  session: Session;
}

export function SessionHeader({ session }: SessionHeaderProps) {
  const [duration, setDuration] = useState<string>('');

  // Update duration for running sessions
  useEffect(() => {
    if (session.status !== 'running') {
      const start = new Date(session.created_at).getTime();
      const end = session.modified_at
        ? new Date(session.modified_at).getTime()
        : new Date().getTime();
      setDuration(formatDuration(end - start));
      return;
    }

    const updateDuration = () => {
      const start = new Date(session.created_at).getTime();
      const now = new Date().getTime();
      setDuration(formatDuration(now - start));
    };

    updateDuration();
    const interval = setInterval(updateDuration, 1000);
    return () => clearInterval(interval);
  }, [session.created_at, session.modified_at, session.status]);

  const displayName = session.session_id.slice(0, 16);

  return (
    <div className="bg-white border-b border-gray-200 px-4 py-3">
      <div className="flex items-center justify-between">
        {/* Left: Session info */}
        <div className="flex items-center gap-4 min-w-0">
          {/* Session name and ID */}
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-gray-900 truncate">
                {displayName}
              </h2>
              <StatusBadge status={session.status} />
            </div>
            <div className="flex items-center gap-1 mt-0.5">
              <span className="text-xs text-gray-400 font-mono">
                {session.session_id.slice(0, 12)}...
              </span>
              <CopyButton text={session.session_id} />
            </div>
          </div>

          {/* Divider */}
          <div className="h-8 w-px bg-gray-200" />

          {/* Metadata badges */}
          <div className="flex items-center gap-3">
            {session.agent_name && (
              <div className="flex items-center gap-1.5 text-sm text-gray-600">
                <Bot className="w-4 h-4 text-gray-400" />
                <span>{session.agent_name}</span>
              </div>
            )}

            {session.project_dir && (
              <div className="flex items-center gap-1.5 text-sm text-gray-500">
                <Folder className="w-4 h-4 text-gray-400" />
                <span className="truncate max-w-[200px]" title={session.project_dir}>
                  {session.project_dir.split('/').pop()}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Right: Duration and time info */}
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-1.5 text-gray-500">
            <Clock className="w-4 h-4 text-gray-400" />
            <span>{duration}</span>
          </div>
          <div className="text-xs text-gray-400">
            Started {formatRelativeTime(session.created_at)}
          </div>
        </div>
      </div>
    </div>
  );
}
