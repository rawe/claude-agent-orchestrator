import { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Modal, Button, Spinner } from '@/components/common';
import { ConfigSchemaEditor } from './ConfigSchemaEditor';
import type {
  MCPServerRegistryEntry,
  MCPServerRegistryCreate,
  MCPServerConfigSchema,
} from '@/types/mcpServer';
import { Settings, X, Sliders, Database } from 'lucide-react';
import { PlaceholderInfo } from './PlaceholderInfo';

// =============================================================================
// ZOD SCHEMA
// =============================================================================

const formSchema = z.object({
  id: z
    .string()
    .min(2, 'Minimum 2 characters')
    .max(60, 'Maximum 60 characters')
    .regex(
      /^[a-z][a-z0-9_-]*$/,
      'Must start with lowercase letter, then lowercase letters, numbers, hyphens, or underscores'
    ),
  name: z.string().min(1, 'Name is required').max(100, 'Maximum 100 characters'),
  description: z.string().optional(),
  url: z.string().min(1, 'URL is required').url('Must be a valid URL'),
  config_schema: z.record(z.unknown()).optional(),
  default_config: z.record(z.unknown()).optional(),
});

type FormData = z.infer<typeof formSchema>;

// =============================================================================
// TABS
// =============================================================================

type TabId = 'general' | 'config' | 'defaults';

const TABS: { id: TabId; label: string; icon: typeof Settings }[] = [
  { id: 'general', label: 'General', icon: Settings },
  { id: 'config', label: 'Config Schema', icon: Sliders },
  { id: 'defaults', label: 'Defaults', icon: Database },
];

// =============================================================================
// COMPONENT
// =============================================================================

interface McpServerEditorProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: MCPServerRegistryCreate) => Promise<void>;
  server?: MCPServerRegistryEntry | null;
  checkIdAvailable: (id: string) => Promise<boolean>;
}

export function McpServerEditor({
  isOpen,
  onClose,
  onSave,
  server,
  checkIdAvailable,
}: McpServerEditorProps) {
  const isEditing = !!server;
  const [activeTab, setActiveTab] = useState<TabId>('general');
  const [saving, setSaving] = useState(false);
  const [idError, setIdError] = useState<string | null>(null);

  const {
    control,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      id: '',
      name: '',
      description: '',
      url: '',
      config_schema: undefined,
      default_config: undefined,
    },
  });

  const configSchema = watch('config_schema') as MCPServerConfigSchema | undefined;

  // Reset form when modal opens/closes or server changes
  useEffect(() => {
    if (isOpen) {
      if (server) {
        reset({
          id: server.id,
          name: server.name,
          description: server.description || '',
          url: server.url,
          config_schema: server.config_schema || undefined,
          default_config: server.default_config || undefined,
        });
      } else {
        reset({
          id: '',
          name: '',
          description: '',
          url: '',
          config_schema: undefined,
          default_config: undefined,
        });
      }
      setActiveTab('general');
      setIdError(null);
    }
  }, [isOpen, server, reset]);

  // Validate ID uniqueness on blur (not onChange to avoid performance issues)
  const validateIdOnBlur = async (value: string) => {
    if (!value || isEditing) {
      setIdError(null);
      return;
    }
    const available = await checkIdAvailable(value);
    if (!available) {
      setIdError(`MCP server "${value}" already exists`);
    } else {
      setIdError(null);
    }
  };

  const onSubmit = async (data: FormData) => {
    if (idError) return;

    setSaving(true);
    try {
      await onSave({
        id: data.id,
        name: data.name,
        description: data.description || undefined,
        url: data.url,
        config_schema: data.config_schema as MCPServerConfigSchema | undefined,
        default_config: data.default_config,
      });
      onClose();
    } catch (err) {
      console.error('Failed to save MCP server:', err);
    } finally {
      setSaving(false);
    }
  };

  // =============================================================================
  // TAB CONTENT
  // =============================================================================

  const GeneralTab = () => (
    <div className="space-y-4">
      {/* ID */}
      <div>
        <label className="label">
          ID <span className="text-red-500">*</span>
        </label>
        <Controller
          name="id"
          control={control}
          render={({ field }) => (
            <input
              {...field}
              onBlur={(e) => {
                field.onBlur();
                validateIdOnBlur(e.target.value);
              }}
              disabled={isEditing}
              className={`input ${isEditing ? 'bg-gray-100 cursor-not-allowed' : ''}`}
              placeholder="e.g., context-store"
            />
          )}
        />
        {errors.id && <p className="text-sm text-red-500 mt-1">{errors.id.message}</p>}
        {idError && <p className="text-sm text-red-500 mt-1">{idError}</p>}
        <p className="text-xs text-gray-500 mt-1">
          Unique identifier used as the "ref" value in agent configs
        </p>
      </div>

      {/* Name */}
      <div>
        <label className="label">
          Name <span className="text-red-500">*</span>
        </label>
        <Controller
          name="name"
          control={control}
          render={({ field }) => (
            <input {...field} className="input" placeholder="e.g., Context Store" />
          )}
        />
        {errors.name && <p className="text-sm text-red-500 mt-1">{errors.name.message}</p>}
      </div>

      {/* Description */}
      <div>
        <label className="label">Description</label>
        <Controller
          name="description"
          control={control}
          render={({ field }) => (
            <textarea
              {...field}
              className="input min-h-[80px]"
              placeholder="Optional description of what this MCP server provides"
            />
          )}
        />
      </div>

      {/* URL */}
      <div>
        <label className="label flex items-center gap-1">
          URL <span className="text-red-500">*</span>
          <PlaceholderInfo />
        </label>
        <Controller
          name="url"
          control={control}
          render={({ field }) => (
            <input
              {...field}
              className="input font-mono text-sm"
              placeholder="e.g., http://localhost:9501/mcp"
            />
          )}
        />
        {errors.url && <p className="text-sm text-red-500 mt-1">{errors.url.message}</p>}
        <p className="text-xs text-gray-500 mt-1">
          Can include placeholders like <code className="bg-gray-100 px-1 rounded">{'${runner.orchestrator_mcp_url}'}</code>
        </p>
      </div>
    </div>
  );

  const ConfigSchemaTab = () => (
    <div className="h-full overflow-y-auto">
      <Controller
        name="config_schema"
        control={control}
        render={({ field }) => (
          <ConfigSchemaEditor
            value={field.value as MCPServerConfigSchema | undefined}
            onChange={field.onChange}
          />
        )}
      />
    </div>
  );

  const DefaultsTab = () => {
    const schemaFields = configSchema ? Object.entries(configSchema) : [];

    return (
      <div className="space-y-4">
        <div>
          <div className="flex items-center gap-1">
            <label className="text-sm font-medium text-gray-700">Default Config Values</label>
            <PlaceholderInfo />
          </div>
          <p className="text-xs text-gray-500">
            Default values for config fields. Agents can override these.
          </p>
        </div>

        {schemaFields.length === 0 ? (
          <div className="text-center py-8 text-gray-500 text-sm bg-gray-50 rounded-lg border-2 border-dashed border-gray-200">
            No config fields defined. Add fields in the "Config Schema" tab first.
          </div>
        ) : (
          <div className="space-y-3">
            {schemaFields.map(([fieldName, fieldDef]) => (
              <div key={fieldName} className="flex items-start gap-3">
                <div className="flex-1">
                  <label className="text-sm font-medium text-gray-700">
                    {fieldName}
                    {fieldDef.required && <span className="text-red-500 ml-1">*</span>}
                  </label>
                  {fieldDef.description && (
                    <p className="text-xs text-gray-500">{fieldDef.description}</p>
                  )}
                  <Controller
                    name="default_config"
                    control={control}
                    render={({ field }) => {
                      const currentDefaults = (field.value || {}) as Record<string, unknown>;
                      const currentValue = currentDefaults[fieldName];

                      const handleChange = (newValue: unknown) => {
                        const updated = { ...currentDefaults };
                        if (newValue === undefined || newValue === '') {
                          delete updated[fieldName];
                        } else {
                          updated[fieldName] = newValue;
                        }
                        field.onChange(Object.keys(updated).length > 0 ? updated : undefined);
                      };

                      if (fieldDef.type === 'boolean') {
                        return (
                          <select
                            value={currentValue === undefined ? '' : String(currentValue)}
                            onChange={(e) => {
                              const val = e.target.value;
                              handleChange(val === '' ? undefined : val === 'true');
                            }}
                            className="input mt-1"
                          >
                            <option value="">Not set</option>
                            <option value="true">true</option>
                            <option value="false">false</option>
                          </select>
                        );
                      }

                      return (
                        <input
                          type={fieldDef.type === 'integer' ? 'number' : fieldDef.sensitive ? 'password' : 'text'}
                          value={currentValue !== undefined ? String(currentValue) : ''}
                          onChange={(e) => {
                            const val = e.target.value;
                            if (!val) {
                              handleChange(undefined);
                            } else if (fieldDef.type === 'integer') {
                              handleChange(parseInt(val, 10));
                            } else {
                              handleChange(val);
                            }
                          }}
                          className="input mt-1"
                          placeholder={
                            fieldDef.default !== undefined
                              ? `Schema default: ${fieldDef.default}`
                              : 'No default'
                          }
                        />
                      );
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  // =============================================================================
  // RENDER
  // =============================================================================

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <form onSubmit={handleSubmit(onSubmit)} className="h-[70vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
          <h2 className="text-lg font-semibold text-gray-900">
            {isEditing ? `Edit MCP Server: ${server.id}` : 'New MCP Server'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-500 focus:outline-none"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body: Sidebar + Content */}
        <div className="flex-1 flex min-h-0">
          {/* Sidebar Tabs */}
          <div className="w-40 bg-gray-50 border-r border-gray-200 p-2 flex flex-col gap-1 flex-shrink-0">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    isActive
                      ? 'bg-white shadow-sm text-gray-900 border-l-2 border-primary-600'
                      : 'text-gray-600 hover:bg-gray-100 border-l-2 border-transparent'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Tab Content */}
          <div className="flex-1 p-6 overflow-y-auto">
            {activeTab === 'general' && <GeneralTab />}
            {activeTab === 'config' && <ConfigSchemaTab />}
            {activeTab === 'defaults' && <DefaultsTab />}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3 flex-shrink-0">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving || !!idError}>
            {saving ? <Spinner size="sm" className="mr-2" /> : null}
            {isEditing ? 'Update' : 'Create'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
