import { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Modal, Button, Spinner } from '@/components/common';
import { MCPJsonEditor } from '../agents/MCPJsonEditor';
import { Capability, CapabilityCreate, CapabilityType } from '@/types/capability';
import { MCPServerConfig } from '@/types';
import { TEMPLATE_NAMES, addTemplate } from '@/utils/mcpTemplates';
import { Eye, Code, FileCode, Server, FileText, Settings, X, FlaskConical } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useScripts } from '@/hooks/useScripts';

// =============================================================================
// ZOD SCHEMA
// =============================================================================

const formSchema = z.object({
  name: z
    .string()
    .min(2, 'Minimum 2 characters')
    .max(60, 'Maximum 60 characters')
    .regex(
      /^[a-zA-Z0-9][a-zA-Z0-9_-]*$/,
      'Must start with letter/number, then letters, numbers, hyphens, or underscores'
    ),
  description: z.string().min(1, 'Description is required'),
  type: z.enum(['script', 'mcp', 'text'] as const),
  script: z.string(),
  text: z.string(),
  mcp_servers: z.record(z.unknown()).nullable(),
});

type FormData = z.infer<typeof formSchema>;

// Type-safe field names constant
const F = {
  name: 'name',
  description: 'description',
  type: 'type',
  script: 'script',
  text: 'text',
  mcp_servers: 'mcp_servers',
} as const satisfies Record<keyof FormData, keyof FormData>;

// =============================================================================
// TABS CONFIGURATION
// =============================================================================

type TabId = 'general' | 'text' | 'script' | 'mcp';

const TABS: { id: TabId; label: string; icon: typeof Settings }[] = [
  { id: 'general', label: 'General', icon: Settings },
  { id: 'text', label: 'Text', icon: FileText },
  { id: 'script', label: 'Script', icon: FileCode },
  { id: 'mcp', label: 'MCP', icon: Server },
];

// =============================================================================
// TYPE OPTIONS
// =============================================================================

const TYPE_OPTIONS: {
  value: CapabilityType;
  label: string;
  description: string;
  icon: React.ReactNode;
  experimental?: boolean;
}[] = [
  {
    value: 'script',
    label: 'Script',
    description: 'Local script execution',
    icon: <FileCode className="w-4 h-4" />,
    experimental: true,
  },
  {
    value: 'mcp',
    label: 'MCP',
    description: 'MCP server integration',
    icon: <Server className="w-4 h-4" />,
  },
  {
    value: 'text',
    label: 'Text',
    description: 'Instructions only',
    icon: <FileText className="w-4 h-4" />,
  },
];

// =============================================================================
// COMPONENT
// =============================================================================

interface CapabilityEditorProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: CapabilityCreate) => Promise<void>;
  capability?: Capability | null;
  checkNameAvailable: (name: string) => Promise<boolean>;
}

export function CapabilityEditor({
  isOpen,
  onClose,
  onSave,
  capability,
  checkNameAvailable,
}: CapabilityEditorProps) {
  const [activeTab, setActiveTab] = useState<TabId>('general');
  const [textTab, setTextTab] = useState<'edit' | 'preview'>('edit');
  const [saving, setSaving] = useState(false);
  const [nameAvailable, setNameAvailable] = useState<boolean | null>(null);
  const [checkingName, setCheckingName] = useState(false);

  const { scripts: availableScripts, loading: scriptsLoading } = useScripts();

  const isEditing = !!capability;

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    control,
    getValues,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: 'onBlur',
    reValidateMode: 'onBlur',
    defaultValues: {
      name: '',
      description: '',
      type: 'text',
      script: '',
      text: '',
      mcp_servers: null,
    },
  });

  const watchedType = watch(F.type);
  const watchedMcpServers = watch(F.mcp_servers);

  // Determine which tabs to show based on type
  const visibleTabs = TABS.filter((tab) => {
    if (tab.id === 'script') return watchedType === 'script';
    if (tab.id === 'mcp') return watchedType === 'mcp';
    return true; // general and text always visible
  });

  // Load capability data when editing
  useEffect(() => {
    if (capability) {
      reset({
        name: capability.name,
        description: capability.description,
        type: capability.type,
        script: capability.script || '',
        text: capability.text || '',
        mcp_servers: capability.mcp_servers ?? null, // Convert undefined to null for Zod
      });
    } else {
      reset({
        name: '',
        description: '',
        type: 'text',
        script: '',
        text: '',
        mcp_servers: null,
      });
    }
    setNameAvailable(null);
    setActiveTab('general');
  }, [capability, reset, isOpen]);

  // Handle name availability check on blur
  const handleNameBlur = async (e: React.FocusEvent<HTMLInputElement>) => {
    const name = e.target.value;
    if (isEditing || !name || name.length < 2) {
      setNameAvailable(null);
      return;
    }

    setCheckingName(true);
    try {
      const available = await checkNameAvailable(name);
      setNameAvailable(available);
    } catch {
      setNameAvailable(null);
    } finally {
      setCheckingName(false);
    }
  };

  const handleAddTemplate = (templateName: string) => {
    const updated = addTemplate(watchedMcpServers as Record<string, MCPServerConfig> | null, templateName);
    setValue(F.mcp_servers, updated);
  };

  const onSubmit = async (data: FormData) => {
    // Check name availability if not yet checked
    if (!isEditing && nameAvailable === null && data.name.length >= 2) {
      setCheckingName(true);
      try {
        const available = await checkNameAvailable(data.name);
        setNameAvailable(available);
        if (!available) {
          setCheckingName(false);
          return; // Don't submit if name is taken
        }
      } catch {
        setNameAvailable(null);
      } finally {
        setCheckingName(false);
      }
    }

    // Don't submit if name is taken
    if (!isEditing && nameAvailable === false) {
      return;
    }

    setSaving(true);
    try {
      const createData: CapabilityCreate = {
        name: data.name,
        description: data.description,
        type: data.type,
        // Only include script if type is 'script'
        script: data.type === 'script' ? data.script || undefined : undefined,
        text: data.text || undefined,
        // Only include mcp_servers if type is 'mcp'
        mcp_servers:
          data.type === 'mcp' ? ((data.mcp_servers as Record<string, MCPServerConfig>) ?? {}) : undefined,
      };
      await onSave(createData);
      onClose();
    } catch (err) {
      console.error('Failed to save capability:', err);
    } finally {
      setSaving(false);
    }
  };

  // ===========================================================================
  // TAB CONTENT COMPONENTS
  // ===========================================================================

  const GeneralTab = () => (
    <div className="space-y-6">
      {/* Name */}
      <div>
        <label className="label">Capability Name *</label>
        <div className="relative">
          <input
            {...register(F.name, { onBlur: handleNameBlur })}
            disabled={isEditing}
            placeholder="my-capability-name"
            className={`input ${isEditing ? 'bg-gray-100' : ''} ${errors.name ? 'border-red-500' : ''}`}
          />
          {checkingName && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <Spinner size="sm" />
            </div>
          )}
        </div>
        {errors.name && <p className="mt-1 text-xs text-red-500">{errors.name.message}</p>}
        {!isEditing && nameAvailable !== null && !checkingName && (
          <p className={`mt-1 text-xs ${nameAvailable ? 'text-green-600' : 'text-red-500'}`}>
            {nameAvailable ? 'Name is available' : 'Name is already taken'}
          </p>
        )}
      </div>

      {/* Description */}
      <div>
        <label className="label">Description *</label>
        <textarea
          {...register(F.description)}
          placeholder="Describe what this capability provides..."
          rows={3}
          className={`input resize-none ${errors.description ? 'border-red-500' : ''}`}
        />
        {errors.description && <p className="mt-1 text-xs text-red-500">{errors.description.message}</p>}
      </div>

      {/* Capability Type */}
      <div>
        <label className="label">Capability Type</label>
        <div className="grid grid-cols-3 gap-3">
          {TYPE_OPTIONS.map((option) => (
            <label
              key={option.value}
              className={`relative flex flex-col items-center p-4 border-2 rounded-lg cursor-pointer transition-all ${
                watchedType === option.value
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <input type="radio" {...register(F.type)} value={option.value} className="sr-only" />
              {option.experimental && (
                <span className="absolute top-1 right-1 inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 bg-amber-100 rounded">
                  <FlaskConical className="w-2.5 h-2.5" />
                  Experimental
                </span>
              )}
              <div
                className={`mb-2 ${watchedType === option.value ? 'text-primary-600' : 'text-gray-400'}`}
              >
                {option.icon}
              </div>
              <span
                className={`text-sm font-medium ${
                  watchedType === option.value ? 'text-primary-700' : 'text-gray-700'
                }`}
              >
                {option.label}
              </span>
              <span className="text-xs text-gray-500 text-center mt-1">{option.description}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );

  const TextTab = () => (
    <div className="h-full flex flex-col">
      {/* Header with Edit/Preview toggle */}
      <div className="flex items-center justify-between mb-2 flex-shrink-0">
        <div>
          <label className="label mb-0">Text Content</label>
          <p className="text-xs text-gray-500">
            Markdown content appended to the agent's system prompt when this capability is used.
          </p>
        </div>
        <div className="flex rounded-md border border-gray-300 overflow-hidden">
          <button
            type="button"
            onClick={() => setTextTab('edit')}
            className={`flex items-center gap-1 px-3 py-1.5 text-xs ${
              textTab === 'edit'
                ? 'bg-primary-50 text-primary-700'
                : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            <Code className="w-3.5 h-3.5" />
            Edit
          </button>
          <button
            type="button"
            onClick={() => setTextTab('preview')}
            className={`flex items-center gap-1 px-3 py-1.5 text-xs border-l ${
              textTab === 'preview'
                ? 'bg-primary-50 text-primary-700'
                : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            <Eye className="w-3.5 h-3.5" />
            Preview
          </button>
        </div>
      </div>

      {/* Full-height editor/preview */}
      {textTab === 'edit' ? (
        <textarea
          {...register(F.text)}
          placeholder="## Capability Documentation&#10;&#10;Provide instructions, schemas, or documentation that agents using this capability need..."
          className="input font-mono text-sm resize-none flex-1 min-h-0"
        />
      ) : (
        <div className="border border-gray-300 rounded-md p-4 flex-1 min-h-0 overflow-auto bg-white">
          {getValues(F.text) ? (
            <div className="markdown-content prose prose-sm max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{getValues(F.text)}</ReactMarkdown>
            </div>
          ) : (
            <p className="text-gray-400 text-sm italic">Enter text content to see the preview</p>
          )}
        </div>
      )}
    </div>
  );

  const ScriptTab = () => (
    <div className="space-y-4">
      {/* Experimental Notice */}
      <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-md">
        <FlaskConical className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
        <p className="text-xs text-amber-800">
          <span className="font-medium">Experimental:</span> Script capabilities currently rely on
          procedural and autonomous runners sharing the same project directory. Explicit script
          deployment to autonomous agents is not yet implemented.
        </p>
      </div>

      <div>
        <label className="label">Script</label>
        <p className="text-xs text-gray-500 mb-2">
          Select a script that agents can execute locally when using this capability.
        </p>
        <select {...register(F.script)} className="input" disabled={scriptsLoading}>
          <option value="">Select a script...</option>
          {availableScripts.map((script) => (
            <option key={script.name} value={script.name}>
              {script.name} - {script.description}
            </option>
          ))}
        </select>
        {scriptsLoading && <p className="mt-1 text-xs text-gray-500">Loading scripts...</p>}
        {!scriptsLoading && availableScripts.length === 0 && (
          <p className="mt-1 text-xs text-amber-600">No scripts available. Create scripts first.</p>
        )}
      </div>
    </div>
  );

  const McpTab = () => (
    <div className="h-full flex flex-col">
      <div className="flex-shrink-0 mb-3">
        <label className="label mb-1">MCP Servers</label>
        <p className="text-xs text-gray-500 mb-3">
          MCP server configurations that will be available to agents using this capability.
        </p>

        {/* Template Quick Add Buttons */}
        <div className="flex flex-wrap gap-2">
          <span className="text-xs text-gray-500 py-1">Quick add:</span>
          {TEMPLATE_NAMES.map((name) => (
            <button
              key={name}
              type="button"
              onClick={() => handleAddTemplate(name)}
              className="px-2 py-1 text-xs bg-blue-50 hover:bg-blue-100 text-blue-700 rounded border border-blue-200"
            >
              + {name}
            </button>
          ))}
        </div>
      </div>

      {/* JSON Editor - fills remaining space */}
      <Controller
        name={F.mcp_servers}
        control={control}
        render={({ field }) => (
          <MCPJsonEditor
            value={(field.value as Record<string, MCPServerConfig>) ?? null}
            onChange={field.onChange}
            className="flex-1 min-h-0"
          />
        )}
      />
    </div>
  );

  // ===========================================================================
  // RENDER
  // ===========================================================================

  // Log validation errors for debugging
  const onInvalid = (errors: Record<string, unknown>) => {
    console.error('Form validation errors:', errors);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <form onSubmit={handleSubmit(onSubmit, onInvalid)} className="h-[75vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
          <h2 className="text-lg font-semibold text-gray-900">
            {isEditing ? `Edit Capability: ${capability.name}` : 'New Capability'}
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
            {visibleTabs.map((tab) => {
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

          {/* Tab Content - all tabs always rendered, hidden when inactive */}
          <div
            className={`flex-1 p-6 flex flex-col overflow-y-auto ${activeTab !== 'general' ? 'hidden' : ''}`}
          >
            <GeneralTab />
          </div>
          <div
            className={`flex-1 p-6 flex flex-col overflow-y-auto ${activeTab !== 'text' ? 'hidden' : ''}`}
          >
            <TextTab />
          </div>
          <div
            className={`flex-1 p-6 flex flex-col overflow-y-auto ${activeTab !== 'script' ? 'hidden' : ''}`}
          >
            <ScriptTab />
          </div>
          <div
            className={`flex-1 p-6 flex flex-col overflow-y-auto ${activeTab !== 'mcp' ? 'hidden' : ''}`}
          >
            <McpTab />
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 bg-gray-50 border-t border-gray-200 flex-shrink-0">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={saving} disabled={!isEditing && nameAvailable === false}>
            {isEditing ? 'Save Changes' : 'Create Capability'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
