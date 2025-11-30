import { Session } from '@/types';
import { StatusBadge, Badge, CopyButton } from '@/components/common';
import { formatRelativeTime, formatAbsoluteTime, getLastPathSegment } from '@/utils/formatters';
import { Folder, Trash2, Square } from 'lucide-react';

interface SessionCardProps {
  session: Session;
  isSelected: boolean;
  onSelect: () => void;
  onStop?: () => void;
  onDelete: () => void;
}

export function SessionCard({
  session,
  isSelected,
  onSelect,
  onStop,
  onDelete,
}: SessionCardProps) {
  const displayName = session.session_name || session.session_id;
  const projectFolder = session.project_dir ? getLastPathSegment(session.project_dir) : null;

  return (
    <div
      onClick={onSelect}
      className={`p-3 border rounded-lg cursor-pointer transition-all ${
        isSelected
          ? 'border-primary-500 bg-primary-50 ring-1 ring-primary-500'
          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
      }`}
    >
      {/* Header: Name and Status */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-gray-900 truncate" title={displayName}>
            {displayName}
          </h3>
          {session.session_name && (
            <div className="flex items-center gap-1 mt-0.5">
              <span className="text-xs text-gray-500 truncate" title={session.session_id}>
                {session.session_id.slice(0, 8)}...
              </span>
              <CopyButton text={session.session_id} />
            </div>
          )}
        </div>
        <StatusBadge status={session.status} />
      </div>

      {/* Agent badge */}
      {session.agent_name && (
        <div className="mb-2">
          <Badge variant="info" size="sm">
            {session.agent_name}
          </Badge>
        </div>
      )}

      {/* Project directory */}
      {projectFolder && (
        <div className="flex items-center gap-1.5 text-xs text-gray-500 mb-2">
          <Folder className="w-3.5 h-3.5" />
          <span className="truncate" title={session.project_dir}>
            {projectFolder}
          </span>
          <CopyButton text={session.project_dir!} />
        </div>
      )}

      {/* Timestamps */}
      <div className="text-xs text-gray-400 space-y-0.5">
        <div title={formatAbsoluteTime(session.created_at)}>
          Created: {formatRelativeTime(session.created_at)}
        </div>
        {session.modified_at && (
          <div title={formatAbsoluteTime(session.modified_at)}>
            Modified: {formatRelativeTime(session.modified_at)}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 mt-3 pt-2 border-t border-gray-100">
        {session.status === 'running' && onStop && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onStop();
            }}
            className="flex items-center gap-1 px-2 py-1 text-xs text-orange-600 hover:bg-orange-50 rounded transition-colors"
            title="Stop session"
          >
            <Square className="w-3 h-3" />
            Stop
          </button>
        )}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="flex items-center gap-1 px-2 py-1 text-xs text-red-600 hover:bg-red-50 rounded transition-colors"
          title="Delete session"
        >
          <Trash2 className="w-3 h-3" />
          Delete
        </button>
      </div>
    </div>
  );
}
