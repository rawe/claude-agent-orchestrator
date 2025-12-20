/**
 * Session Card Component
 *
 * Note: Uses session_id (coordinator-generated) per ADR-010.
 */

import { Session } from '@/types';
import { StatusBadge, CopyButton } from '@/components/common';
import { formatRelativeTime, formatAbsoluteTime, getLastPathSegment } from '@/utils/formatters';
import { Folder, Trash2, Square, Bot, CornerDownRight, Server } from 'lucide-react';

interface SessionCardProps {
  session: Session;
  isSelected: boolean;
  onSelect: () => void;
  onStop?: () => void;
  onDelete: () => void;
}

function getStatusAccentColor(status: Session['status']): string {
  switch (status) {
    case 'pending':
      return 'bg-yellow-400';
    case 'running':
      return 'bg-emerald-500';
    case 'stopping':
      return 'bg-amber-500';
    case 'finished':
      return 'bg-gray-300';
    case 'stopped':
      return 'bg-red-500';
    default:
      return 'bg-gray-300';
  }
}

export function SessionCard({
  session,
  isSelected,
  onSelect,
  onStop,
  onDelete,
}: SessionCardProps) {
  const displayName = session.session_id.slice(0, 16);
  const projectFolder = session.project_dir ? getLastPathSegment(session.project_dir) : null;
  const accentColor = getStatusAccentColor(session.status);

  return (
    <div
      onClick={onSelect}
      className={`group relative flex overflow-hidden rounded-lg cursor-pointer transition-all duration-200 ${
        isSelected
          ? 'bg-primary-50 ring-2 ring-primary-500 shadow-sm'
          : 'bg-white hover:bg-gray-50 border border-gray-200 hover:border-gray-300 hover:shadow-sm'
      }`}
    >
      {/* Status accent bar */}
      <div className={`w-1 ${accentColor} flex-shrink-0`} />

      {/* Main content */}
      <div className="flex-1 min-w-0 p-3">
        {/* Header: Session ID and Status */}
        <div className="flex items-start justify-between gap-2 mb-1.5">
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-medium text-gray-900 truncate" title={session.session_id}>
              {displayName}
            </h3>
          </div>
          <StatusBadge status={session.status} />
        </div>

        {/* Full Session ID with copy */}
        <div className="flex items-center gap-1 mb-1.5">
          <span className="text-xs text-gray-400 font-mono truncate" title={session.session_id}>
            {session.session_id}
          </span>
          <CopyButton text={session.session_id} />
        </div>

        {/* Agent, Parent, Hostname, and Project - stacked vertically */}
        <div className="space-y-1 mb-2">
          {session.agent_name && (
            <div className="flex items-center gap-1.5 text-xs text-gray-600">
              <Bot className="w-3 h-3 text-gray-400" />
              <span className="truncate font-medium">{session.agent_name}</span>
            </div>
          )}
          {session.parent_session_id && (
            <div className="flex items-center gap-1.5 text-xs text-gray-500">
              <CornerDownRight className="w-3 h-3 text-gray-400" />
              <span className="truncate" title={`Parent: ${session.parent_session_id}`}>
                {session.parent_session_id.slice(0, 12)}...
              </span>
            </div>
          )}
          {session.hostname && (
            <div className="flex items-center gap-1.5 text-xs text-gray-500">
              <Server className="w-3 h-3 text-gray-400" />
              <span className="truncate" title={`Host: ${session.hostname}`}>
                {session.hostname}
              </span>
            </div>
          )}
          {projectFolder && (
            <div className="flex items-center gap-1.5 text-xs text-gray-500">
              <Folder className="w-3 h-3 text-gray-400" />
              <span className="truncate" title={session.project_dir}>
                {projectFolder}
              </span>
            </div>
          )}
        </div>

        {/* Timestamp */}
        <div className="text-xs text-gray-400" title={formatAbsoluteTime(session.modified_at || session.created_at)}>
          {formatRelativeTime(session.modified_at || session.created_at)}
        </div>

        {/* Actions - visible on hover or when selected */}
        <div className={`flex items-center gap-1 mt-2 pt-2 border-t border-gray-100 transition-opacity duration-200 ${
          isSelected ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
        }`}>
          {session.status === 'running' && onStop && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onStop();
              }}
              className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-amber-600 hover:bg-amber-50 rounded transition-colors"
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
            className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50 rounded transition-colors"
            title="Delete session"
          >
            <Trash2 className="w-3 h-3" />
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
