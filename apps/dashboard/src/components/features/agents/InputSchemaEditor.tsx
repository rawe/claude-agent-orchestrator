import { useState, useEffect, useCallback } from 'react';
import { AlertCircle, Check, Code } from 'lucide-react';

interface InputSchemaEditorProps {
  value: Record<string, unknown> | null;
  onChange: (value: Record<string, unknown> | null) => void;
  className?: string;
}

// Default schema template for autonomous agents with custom inputs
const DEFAULT_SCHEMA_TEMPLATE = {
  type: 'object',
  properties: {
    topic: {
      type: 'string',
      description: 'The main topic or subject',
    },
  },
  additionalProperties: false,
};

export function InputSchemaEditor({ value, onChange, className = '' }: InputSchemaEditorProps) {
  const [jsonText, setJsonText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isValid, setIsValid] = useState(true);

  // Initialize JSON text from value
  useEffect(() => {
    if (value) {
      setJsonText(JSON.stringify(value, null, 2));
      setError(null);
      setIsValid(true);
    } else {
      // Initialize with default template when enabling for the first time
      const template = DEFAULT_SCHEMA_TEMPLATE;
      setJsonText(JSON.stringify(template, null, 2));
      // Trigger onChange with the template
      onChange(template);
      setError(null);
      setIsValid(true);
    }
  }, [value === null]); // Only react to null -> non-null transitions

  const validateAndUpdate = useCallback(
    (text: string) => {
      setJsonText(text);

      if (!text.trim()) {
        setError('Schema cannot be empty');
        setIsValid(false);
        return;
      }

      try {
        const parsed = JSON.parse(text);

        // Basic JSON Schema validation
        if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
          setError('Schema must be a JSON object');
          setIsValid(false);
          return;
        }

        // Check for required JSON Schema fields
        if (parsed.type && parsed.type !== 'object') {
          setError('Schema type must be "object"');
          setIsValid(false);
          return;
        }

        // Valid JSON Schema
        setError(null);
        setIsValid(true);
        onChange(parsed);
      } catch (e) {
        if (e instanceof SyntaxError) {
          setError(`Invalid JSON: ${e.message}`);
        } else {
          setError('Invalid JSON');
        }
        setIsValid(false);
      }
    },
    [onChange]
  );

  const handlePrettify = () => {
    try {
      const parsed = JSON.parse(jsonText);
      setJsonText(JSON.stringify(parsed, null, 2));
    } catch {
      // Ignore if invalid JSON
    }
  };

  return (
    <div className={`flex flex-col ${className}`}>
      <div className="flex items-center justify-between mb-2 flex-shrink-0">
        <div className="flex items-center gap-2">
          {isValid ? (
            <span className="flex items-center gap-1 text-xs text-green-600">
              <Check className="w-3 h-3" />
              Valid JSON Schema
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs text-red-500">
              <AlertCircle className="w-3 h-3" />
              Invalid
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={handlePrettify}
          className="flex items-center gap-1 px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded"
        >
          <Code className="w-3 h-3" />
          Prettify
        </button>
      </div>

      <textarea
        value={jsonText}
        onChange={(e) => validateAndUpdate(e.target.value)}
        placeholder={JSON.stringify(DEFAULT_SCHEMA_TEMPLATE, null, 2)}
        className={`input font-mono text-sm resize-none flex-1 min-h-[200px] ${
          !isValid ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : ''
        }`}
      />

      {error && (
        <p className="text-xs text-red-500 flex items-center gap-1 mt-2 flex-shrink-0">
          <AlertCircle className="w-3 h-3" />
          {error}
        </p>
      )}

      <div className="text-xs text-gray-500 mt-2 flex-shrink-0">
        <p>
          Define a JSON Schema for input parameters passed to the agent.
          Example: <code className="font-mono bg-gray-100 px-1 rounded">{`{"topic": "AI safety"}`}</code>
        </p>
      </div>
    </div>
  );
}
