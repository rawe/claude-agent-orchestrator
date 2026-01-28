// Utility functions for Unified View

export function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${Math.floor(diffHours / 24)}d ago`;
}

export function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes === 0) return `${seconds}s`;
  return `${minutes}m ${remainingSeconds}s`;
}

export function getEventTypeStyles(type: string): string {
  switch (type) {
    case 'run_start':
    case 'session_resume':
      return 'bg-blue-100 text-blue-700 border-blue-200';
    case 'run_completed':
      return 'bg-gray-100 text-gray-700 border-gray-200';
    case 'tool_call':
      return 'bg-purple-100 text-purple-700 border-purple-200';
    case 'tool_result':
      return 'bg-indigo-100 text-indigo-700 border-indigo-200';
    case 'assistant':
      return 'bg-emerald-100 text-emerald-700 border-emerald-200';
    case 'user':
      return 'bg-amber-100 text-amber-700 border-amber-200';
    default:
      return 'bg-gray-100 text-gray-700 border-gray-200';
  }
}
