import { useState } from 'react';
import { useMcpServers } from '@/hooks/useMcpServers';
import type { MCPServerConfig, MCPServerRef } from '@/types/agent';
import type { MCPServerRegistryEntry, ConfigSchemaField } from '@/types/mcpServer';
import { isMCPServerRef } from '@/types/agent';
import { Badge, Button, Spinner } from '@/components/common';
import { Plus, Trash2, ChevronDown, Server, Eye, EyeOff, AlertTriangle, ExternalLink } from 'lucide-react';
import { PlaceholderInfo } from '../mcp-servers/PlaceholderInfo';
import { Link } from 'react-router-dom';

interface MCPServerSelectorProps {
  value: Record<string, MCPServerConfig> | null;
  onChange: (value: Record<string, MCPServerConfig> | null) => void;
  className?: string;
}

interface ServerCardProps {
  alias: string;
  config: MCPServerRef;
  registryEntry?: MCPServerRegistryEntry;
  onUpdate: (alias: string, config: MCPServerRef) => void;
  onDelete: (alias: string) => void;
  onRename: (oldAlias: string, newAlias: string) => void;
  existingAliases: string[];
}

function ServerCard({
  alias,
  config,
  registryEntry,
  onUpdate,
  onDelete,
  onRename,
  existingAliases,
}: ServerCardProps) {
  const [localAlias, setLocalAlias] = useState(alias);
  const [aliasError, setAliasError] = useState<string | null>(null);
  const [showSensitive, setShowSensitive] = useState<Record<string, boolean>>({});

  const handleAliasBlur = () => {
    if (localAlias === alias) return;
    if (!localAlias.trim()) {
      setLocalAlias(alias);
      setAliasError(null);
      return;
    }
    if (existingAliases.includes(localAlias.trim()) && localAlias.trim() !== alias) {
      setAliasError(`Alias "${localAlias}" already exists`);
      return;
    }
    setAliasError(null);
    onRename(alias, localAlias.trim());
  };

  // Render config fields based on schema
  const renderConfigFields = () => {
    if (!registryEntry?.config_schema) return null;

    const schema = registryEntry.config_schema;
    const currentConfig = config.config || {};
    const defaultConfig = registryEntry.default_config || {};

    return (
      <div className="space-y-3 mt-3 pt-3 border-t border-gray-200">
        <div className="flex items-center gap-1 text-xs text-gray-500">
          <span>Configuration</span>
          <PlaceholderInfo />
        </div>
        {Object.entries(schema).map(([fieldName, fieldDef]) => {
          const currentValue = currentConfig[fieldName];
          const defaultValue = defaultConfig[fieldName] ?? fieldDef.default;
          const isSensitive = fieldDef.sensitive;
          const isVisible = showSensitive[fieldName] ?? false;

          return (
            <div key={fieldName}>
              <div className="flex items-center gap-2 mb-1">
                <label className="text-sm font-medium text-gray-700">
                  {fieldName}
                  {fieldDef.required && <span className="text-red-500 ml-1">*</span>}
                </label>
                {isSensitive && (
                  <button
                    type="button"
                    onClick={() => setShowSensitive((prev) => ({ ...prev, [fieldName]: !prev[fieldName] }))}
                    className="p-0.5 text-gray-400 hover:text-gray-600"
                    title={isVisible ? 'Hide value' : 'Show value'}
                  >
                    {isVisible ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                )}
              </div>
              {fieldDef.description && (
                <p className="text-xs text-gray-500 mb-1">{fieldDef.description}</p>
              )}
              <ConfigFieldInput
                fieldName={fieldName}
                fieldDef={fieldDef}
                value={currentValue}
                defaultValue={defaultValue}
                isSensitive={isSensitive}
                isVisible={isVisible}
                onChange={(newValue) => {
                  const newConfig = { ...currentConfig };
                  if (newValue === undefined) {
                    delete newConfig[fieldName];
                  } else {
                    newConfig[fieldName] = newValue;
                  }
                  onUpdate(alias, {
                    ref: config.ref,
                    config: Object.keys(newConfig).length > 0 ? newConfig : undefined,
                  });
                }}
              />
              {defaultValue !== undefined && currentValue === undefined && (
                <p className="text-xs text-gray-400 mt-1">
                  Default: <code className="bg-gray-100 px-1 rounded">{String(defaultValue)}</code>
                </p>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-white">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Server className="w-4 h-4 text-blue-500 flex-shrink-0" />
            <input
              type="text"
              value={localAlias}
              onChange={(e) => setLocalAlias(e.target.value)}
              onBlur={handleAliasBlur}
              className="font-medium text-gray-900 bg-transparent border-b border-transparent hover:border-gray-300 focus:border-primary-500 focus:outline-none px-0.5"
              title="Server alias (editable)"
            />
            <Badge size="sm" variant="info">
              ref: {config.ref}
            </Badge>
          </div>
          {aliasError && <p className="text-xs text-red-500">{aliasError}</p>}
          {!registryEntry && (
            <div className="flex items-center gap-1 text-amber-600 text-xs mt-1">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Server "{config.ref}" not found in registry</span>
            </div>
          )}
          {registryEntry && (
            <p className="text-sm text-gray-600 truncate">{registryEntry.name}</p>
          )}
        </div>
        <button
          type="button"
          onClick={() => onDelete(alias)}
          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors flex-shrink-0"
          title="Remove server"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {/* Config fields */}
      {renderConfigFields()}
    </div>
  );
}

interface ConfigFieldInputProps {
  fieldName: string;
  fieldDef: ConfigSchemaField;
  value: unknown;
  defaultValue: unknown;
  isSensitive: boolean;
  isVisible: boolean;
  onChange: (value: unknown) => void;
}

function ConfigFieldInput({
  fieldDef,
  value,
  isSensitive,
  isVisible,
  onChange,
}: ConfigFieldInputProps) {
  if (fieldDef.type === 'boolean') {
    return (
      <select
        value={value === undefined ? '' : String(value)}
        onChange={(e) => {
          const val = e.target.value;
          onChange(val === '' ? undefined : val === 'true');
        }}
        className="input"
      >
        <option value="">Use default</option>
        <option value="true">true</option>
        <option value="false">false</option>
      </select>
    );
  }

  return (
    <input
      type={isSensitive && !isVisible ? 'password' : fieldDef.type === 'integer' ? 'number' : 'text'}
      value={value !== undefined ? String(value) : ''}
      onChange={(e) => {
        const val = e.target.value;
        if (!val) {
          onChange(undefined);
        } else if (fieldDef.type === 'integer') {
          onChange(parseInt(val, 10));
        } else {
          onChange(val);
        }
      }}
      className="input font-mono text-sm"
      placeholder="Use default"
    />
  );
}

export function MCPServerSelector({ value, onChange, className = '' }: MCPServerSelectorProps) {
  const { mcpServers, loading } = useMcpServers();
  const [showDropdown, setShowDropdown] = useState(false);

  const servers = value || {};

  // Filter to only show ref-based servers (ignore any legacy stdio configs)
  const serverEntries = Object.entries(servers).filter(([, config]) => isMCPServerRef(config)) as [string, MCPServerRef][];

  // Build a map of registry entries by ID for quick lookup
  const registryMap = new Map(mcpServers.map((s) => [s.id, s]));

  const handleAddFromRegistry = (entry: MCPServerRegistryEntry) => {
    // Generate unique alias
    let alias = entry.id;
    let counter = 1;
    while (servers[alias]) {
      alias = `${entry.id}-${counter}`;
      counter++;
    }

    const newServers = {
      ...servers,
      [alias]: { ref: entry.id } as MCPServerRef,
    };
    onChange(newServers);
    setShowDropdown(false);
  };

  const handleUpdateServer = (alias: string, config: MCPServerRef) => {
    onChange({ ...servers, [alias]: config });
  };

  const handleDeleteServer = (alias: string) => {
    const newServers = { ...servers };
    delete newServers[alias];
    onChange(Object.keys(newServers).length > 0 ? newServers : null);
  };

  const handleRenameServer = (oldAlias: string, newAlias: string) => {
    if (oldAlias === newAlias || servers[newAlias]) return;

    const newServers: Record<string, MCPServerConfig> = {};
    for (const [key, val] of Object.entries(servers)) {
      if (key === oldAlias) {
        newServers[newAlias] = val;
      } else {
        newServers[key] = val;
      }
    }
    onChange(newServers);
  };

  // Filter out already-added registry servers from dropdown
  const addedRefs = new Set(serverEntries.map(([, config]) => config.ref));
  const availableServers = mcpServers.filter((s) => !addedRefs.has(s.id));

  return (
    <div className={`flex flex-col ${className}`}>
      {/* Actions */}
      <div className="flex items-center gap-2 mb-4">
        {/* Registry Dropdown */}
        <div className="relative">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setShowDropdown(!showDropdown)}
            icon={<Plus className="w-4 h-4" />}
            disabled={loading}
          >
            Add from Registry
            <ChevronDown className="w-4 h-4 ml-1" />
          </Button>

          {showDropdown && (
            <div className="absolute z-10 mt-1 w-72 bg-white border border-gray-200 rounded-lg shadow-lg max-h-64 overflow-y-auto">
              {loading ? (
                <div className="p-4 text-center">
                  <Spinner size="sm" />
                </div>
              ) : availableServers.length === 0 ? (
                <div className="p-4 text-center text-gray-500 text-sm">
                  {mcpServers.length === 0 ? (
                    <>
                      No MCP servers in registry.{' '}
                      <Link to="/mcp-servers" className="text-primary-600 hover:underline">
                        Create one
                      </Link>
                    </>
                  ) : (
                    'All registry servers already added'
                  )}
                </div>
              ) : (
                <ul className="py-1">
                  {availableServers.map((server) => (
                    <li key={server.id}>
                      <button
                        type="button"
                        onClick={() => handleAddFromRegistry(server)}
                        className="w-full text-left px-4 py-2 hover:bg-gray-50 transition-colors"
                      >
                        <div className="font-medium text-gray-900">{server.name}</div>
                        <div className="text-xs text-gray-500 font-mono">{server.id}</div>
                        {server.description && (
                          <div className="text-xs text-gray-400 truncate mt-0.5">
                            {server.description}
                          </div>
                        )}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              {!loading && mcpServers.length > 0 && (
                <div className="border-t border-gray-100 p-2">
                  <Link
                    to="/mcp-servers"
                    className="flex items-center gap-1 text-xs text-primary-600 hover:text-primary-700"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    Manage MCP Server Registry
                  </Link>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Close dropdown on outside click */}
      {showDropdown && (
        <div
          className="fixed inset-0 z-0"
          onClick={() => setShowDropdown(false)}
        />
      )}

      {/* Server Cards */}
      {serverEntries.length === 0 ? (
        <div className="text-center py-8 text-gray-500 text-sm bg-gray-50 rounded-lg border-2 border-dashed border-gray-200">
          No MCP servers configured. Add servers from the registry.
        </div>
      ) : (
        <div className="space-y-3">
          {serverEntries.map(([alias, config]) => {
            const registryEntry = registryMap.get(config.ref);

            return (
              <ServerCard
                key={alias}
                alias={alias}
                config={config}
                registryEntry={registryEntry}
                onUpdate={handleUpdateServer}
                onDelete={handleDeleteServer}
                onRename={handleRenameServer}
                existingAliases={Object.keys(servers)}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
