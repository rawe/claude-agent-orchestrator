import { useState, useEffect } from 'react';
import type { MCPServerConfig } from '@/types';

interface MCPJsonEditorProps {
  value: Record<string, MCPServerConfig> | null;
  onChange: (value: Record<string, MCPServerConfig> | null) => void;
  error?: string;
  className?: string;
}

const PLACEHOLDER = `"my-server": { "command": "npx", "args": ["@example/mcp"] }
"http-server": { "type": "http", "url": "http://localhost:9000/mcp" }`;

export function MCPJsonEditor({ value, onChange, error, className = '' }: MCPJsonEditorProps) {
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

        // HTTP type: requires url
        if (cfg.type === 'http') {
          if (!cfg.url || typeof cfg.url !== 'string') {
            setParseError(`Server "${name}": HTTP type requires "url" field`);
            return;
          }
        } else {
          // Stdio type (default): requires command and args
          if (!cfg.command || typeof cfg.command !== 'string') {
            setParseError(`Server "${name}": missing or invalid "command" field`);
            return;
          }
          if (!cfg.args || !Array.isArray(cfg.args)) {
            setParseError(`Server "${name}": missing or invalid "args" field`);
            return;
          }
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
    <div className={`flex flex-col ${className}`}>
      {/* Visual wrapper showing the mcpServers context */}
      <div className="font-mono text-xs text-gray-400 select-none flex-shrink-0">
        {'{ "mcpServers": {'}
      </div>
      <textarea
        value={text}
        onChange={(e) => handleChange(e.target.value)}
        placeholder={PLACEHOLDER}
        className={`w-full flex-1 min-h-[280px] px-3 py-2 font-mono text-sm border rounded-md ml-4
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
          ${displayError ? 'border-red-500' : 'border-gray-300'}
          dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100 resize-none`}
        spellCheck={false}
      />
      <div className="font-mono text-xs text-gray-400 select-none flex-shrink-0">
        {'}}'}
      </div>
      {displayError && (
        <p className="text-sm text-red-500 flex-shrink-0">{displayError}</p>
      )}
      <p className="text-xs text-gray-500 flex-shrink-0 mt-1">
        Stdio: "command" + "args". HTTP: "type": "http" + "url".
      </p>
    </div>
  );
}
