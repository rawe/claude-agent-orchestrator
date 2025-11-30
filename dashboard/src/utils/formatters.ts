/**
 * Format a date string to a human-readable relative time
 */
export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;

  return date.toLocaleDateString();
}

/**
 * Format a date string to absolute time
 */
export function formatAbsoluteTime(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleString();
}

/**
 * Format a timestamp to time only (HH:MM:SS)
 */
export function formatTime(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleTimeString();
}

/**
 * Format bytes to human-readable size
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${units[i]}`;
}

/**
 * Truncate a string with ellipsis
 */
export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength - 3) + '...';
}

/**
 * Get the last part of a path
 */
export function getLastPathSegment(path: string): string {
  const segments = path.replace(/\/$/, '').split('/');
  return segments[segments.length - 1] || path;
}

/**
 * Format JSON with syntax highlighting classes
 */
export function formatJson(obj: unknown, indent: number = 2): string {
  return JSON.stringify(obj, null, indent);
}

/**
 * Get file icon based on MIME type or filename
 */
export function getFileIcon(contentType: string, filename?: string): string {
  const ext = filename?.split('.').pop()?.toLowerCase();

  if (contentType.includes('markdown') || ext === 'md') return '📝';
  if (contentType.includes('json') || ext === 'json') return '📊';
  if (contentType.includes('pdf') || ext === 'pdf') return '📕';
  if (contentType.includes('image')) return '🖼️';
  if (contentType.includes('csv') || ext === 'csv') return '📈';
  if (contentType.includes('text')) return '📄';

  return '📎';
}

/**
 * Capitalize first letter
 */
export function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Format duration in milliseconds to human-readable string
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  return `${minutes}m ${seconds}s`;
}

/**
 * Generate a unique key for a session event
 * Used for deduplication and React keys
 */
export function getEventKey(event: { id?: number; session_id: string; timestamp: string; event_type: string }): string {
  if (event.id !== undefined) {
    return `id-${event.id}`;
  }
  return `${event.session_id}-${event.timestamp}-${event.event_type}`;
}
