/**
 * ScriptSelector
 *
 * Reusable component for selecting a script with details display.
 * Works as a controlled component compatible with react-hook-form Controller.
 */

import { Spinner, Badge } from '@/components/common';
import type { ScriptSummary } from '@/types/script';

interface ScriptSelectorProps {
  /** Currently selected script name */
  value: string;
  /** Called when selection changes */
  onChange: (value: string) => void;
  /** Available scripts to select from */
  scripts: ScriptSummary[];
  /** Whether scripts are currently loading */
  loading: boolean;
  /** Whether the selector is disabled */
  disabled?: boolean;
  /** Optional class name for the container */
  className?: string;
}

/**
 * Script selector dropdown with details panel.
 * Shows script metadata when a script is selected.
 */
export function ScriptSelector({
  value,
  onChange,
  scripts,
  loading,
  disabled = false,
  className = '',
}: ScriptSelectorProps) {
  const selectedScript = scripts.find((s) => s.name === value);

  return (
    <div className={className}>
      {/* Loading State */}
      {loading ? (
        <div className="flex items-center gap-2 text-gray-500 text-sm py-4">
          <Spinner size="sm" />
          <span>Loading scripts...</span>
        </div>
      ) : scripts.length === 0 ? (
        /* Empty State */
        <div className="text-sm text-gray-500 italic py-4 p-4 bg-yellow-50 rounded-md border border-yellow-200">
          <p className="font-medium text-yellow-800 mb-1">No scripts available</p>
          <p>Create scripts in the Scripts page first, then come back to select one.</p>
        </div>
      ) : (
        <>
          {/* Dropdown */}
          <select
            value={value}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            className={`input ${!value ? 'text-gray-400' : ''}`}
          >
            <option value="">Select a script...</option>
            {scripts.map((s) => (
              <option key={s.name} value={s.name}>
                {s.name}
              </option>
            ))}
          </select>

          {/* Details Panel */}
          {selectedScript && (
            <div className="mt-4 p-4 bg-gray-50 rounded-md border border-gray-200">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Script Details</h4>
              <div className="space-y-2 text-sm">
                <p>
                  <span className="text-gray-500">File:</span>{' '}
                  <code className="bg-gray-100 px-1.5 py-0.5 rounded text-gray-700">
                    {selectedScript.script_file}
                  </code>
                </p>
                <p>
                  <span className="text-gray-500">Description:</span>{' '}
                  <span className="text-gray-700">{selectedScript.description}</span>
                </p>
                <div className="flex items-center gap-2 mt-2">
                  {selectedScript.has_parameters_schema && (
                    <Badge size="sm" variant="default">
                      Has Schema
                    </Badge>
                  )}
                  {selectedScript.has_demands && (
                    <Badge size="sm" variant="info">
                      Has Demands
                    </Badge>
                  )}
                  {selectedScript.demand_tags.length > 0 && (
                    <span className="text-xs text-gray-500">
                      Tags: {selectedScript.demand_tags.join(', ')}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
