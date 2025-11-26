import { useState, useEffect } from 'react';
import type { MCPServerConfig } from '@/types';

interface MCPJsonEditorProps {
  value: Record<string, MCPServerConfig> | null;
  onChange: (value: Record<string, MCPServerConfig> | null) => void;
  error?: string;
}

const PLACEHOLDER = `"server-name": { "command": "...", "args": [...], "env": {...} }`;

export function MCPJsonEditor({ value, onChange, error }: MCPJsonEditorProps) {
  const [text, setText] = useState('');
  const [parseError, setParseError] = useState<string | null>(null);

  // Sync text with value prop
  useEffect(() => {
    if (value) {
      setText(JSON.stringify(value, null, 2).slice(1, -1).trim());
    } else {
      setText('');
    }
  }, [value]);

  const handleChange = (newText: string) => {
    setText(newText);

    if (!newText.trim()) {
      onChange(null);
      setParseError(null);
      return;
    }

    try {
      // Wrap user input in braces to make valid JSON
      const parsed = JSON.parse(`{${newText}}`);

      // Basic validation: must be an object
      if (typeof parsed !== 'object' || Array.isArray(parsed)) {
        setParseError('Must be a JSON object');
        return;
      }

      // Validate each server config has required fields
      for (const [name, config] of Object.entries(parsed)) {
        const cfg = config as Record<string, unknown>;
        if (!cfg.command || typeof cfg.command !== 'string') {
          setParseError(`Server "${name}": missing or invalid "command" field`);
          return;
        }
        if (!cfg.args || !Array.isArray(cfg.args)) {
          setParseError(`Server "${name}": missing or invalid "args" field`);
          return;
        }
      }

      onChange(parsed as Record<string, MCPServerConfig>);
      setParseError(null);
    } catch (e) {
      setParseError('Invalid JSON syntax');
    }
  };

  const displayError = parseError || error;

  return (
    <div className="space-y-1">
      {/* Visual wrapper showing the mcpServers context */}
      <div className="font-mono text-xs text-gray-400 select-none">
        {'{ "mcpServers": {'}
      </div>
      <textarea
        value={text}
        onChange={(e) => handleChange(e.target.value)}
        placeholder={PLACEHOLDER}
        className={`w-full h-40 px-3 py-2 font-mono text-sm border rounded-md ml-4
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
          ${displayError ? 'border-red-500' : 'border-gray-300'}
          dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100`}
        spellCheck={false}
      />
      <div className="font-mono text-xs text-gray-400 select-none">
        {'}}'}
      </div>
      {displayError && (
        <p className="text-sm text-red-500">{displayError}</p>
      )}
      <p className="text-xs text-gray-500">
        Define MCP servers. Each needs "command" (string) and "args" (array). Optional: "env" object.
      </p>
    </div>
  );
}
