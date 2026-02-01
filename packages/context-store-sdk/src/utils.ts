/**
 * Build a partition-aware URL path.
 *
 * URL Routing:
 * - No partition (global): `GET /documents`
 * - With partition: `GET /partitions/{partition}/documents`
 *
 * @param basePath - The base path (e.g., '/documents', '/search', '/relations')
 * @param partition - Optional partition name
 * @returns The full URL path with partition prefix if provided
 */
export function buildPartitionPath(basePath: string, partition?: string): string {
  if (partition) {
    return `/partitions/${encodeURIComponent(partition)}${basePath}`;
  }
  return basePath;
}

/**
 * Resolve the effective partition from per-call option and client default.
 *
 * @param callPartition - Partition specified in the method call
 * @param defaultPartition - Default partition from client config
 * @returns The resolved partition (call takes precedence over default)
 */
export function resolvePartition(
  callPartition?: string,
  defaultPartition?: string
): string | undefined {
  return callPartition !== undefined ? callPartition : defaultPartition;
}

/**
 * Convert snake_case string to camelCase.
 */
function snakeToCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

/**
 * Convert object keys from snake_case to camelCase recursively.
 * Handles nested objects and arrays.
 */
export function toCamelCase<T>(obj: unknown): T {
  if (obj === null || obj === undefined) {
    return obj as T;
  }

  if (Array.isArray(obj)) {
    return obj.map((item) => toCamelCase(item)) as T;
  }

  if (typeof obj === 'object') {
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
      const camelKey = snakeToCamel(key);
      result[camelKey] = toCamelCase(value);
    }
    return result as T;
  }

  return obj as T;
}
