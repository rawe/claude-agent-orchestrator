import { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { Modal, Button, Badge, Spinner, TagSelector, InfoPopover } from '@/components/common';
import { MCPJsonEditor } from './MCPJsonEditor';
import { InputSchemaEditor } from './InputSchemaEditor';
import { OutputSchemaEditor } from './OutputSchemaEditor';
import { Agent, AgentCreate, AgentDemands, MCPServerConfig } from '@/types';
import { TEMPLATE_NAMES, addTemplate } from '@/utils/mcpTemplates';
import { useCapabilities } from '@/hooks/useCapabilities';
import {
  Eye,
  Code,
  X,
  AlertCircle,
  Settings,
  FileInput,
  FileOutput,
  ScrollText,
  Puzzle,
  Server,
  Target,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface AgentEditorProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: AgentCreate) => Promise<void>;
  agent?: Agent | null;
  checkNameAvailable: (name: string) => Promise<boolean>;
}

interface FormData {
  name: string;
  description: string;
  parameters_schema_enabled: boolean;
  parameters_schema: Record<string, unknown> | null;
  output_schema_enabled: boolean;
  output_schema: Record<string, unknown> | null;
  system_prompt: string;
  mcp_servers: Record<string, MCPServerConfig> | null;
  skills: string[];
  tags: string[];
  capabilities: string[];
  demands: AgentDemands | null;
}

type TabId = 'general' | 'input' | 'output' | 'prompt' | 'capabilities' | 'mcp' | 'runner';

const tabs: { id: TabId; label: string; icon: typeof Settings }[] = [
  { id: 'general', label: 'General', icon: Settings },
  { id: 'input', label: 'Input', icon: FileInput },
  { id: 'output', label: 'Output', icon: FileOutput },
  { id: 'prompt', label: 'Prompt', icon: ScrollText },
  { id: 'capabilities', label: 'Capabilities', icon: Puzzle },
  { id: 'mcp', label: 'MCP', icon: Server },
  { id: 'runner', label: 'Runner', icon: Target },
];

export function AgentEditor({
  isOpen,
  onClose,
  onSave,
  agent,
  checkNameAvailable,
}: AgentEditorProps) {
  const [activeTab, setActiveTab] = useState<TabId>('general');
  const [promptTab, setPromptTab] = useState<'edit' | 'preview'>('edit');
  const [saving, setSaving] = useState(false);
  const [nameAvailable, setNameAvailable] = useState<boolean | null>(null);
  const [checkingName, setCheckingName] = useState(false);

  // Load available capabilities for the multi-select
  const { capabilities: availableCapabilities, loading: capabilitiesLoading } = useCapabilities();

  const isEditing = !!agent;

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
    defaultValues: {
      name: '',
      description: '',
      parameters_schema_enabled: false,
      parameters_schema: null,
      output_schema_enabled: false,
      output_schema: null,
      system_prompt: '',
      mcp_servers: null,
      skills: [],
      tags: [],
      capabilities: [],
      demands: null,
    },
  });

  const watchedSchemaEnabled = watch('parameters_schema_enabled');
  const watchedOutputSchemaEnabled = watch('output_schema_enabled');
  const watchedMcpServers = watch('mcp_servers');
  const watchedCapabilities = watch('capabilities');

  // Load agent data when editing
  useEffect(() => {
    if (agent) {
      // parameters_schema_enabled is true if the agent has a non-null schema
      const hasInputSchema = agent.parameters_schema != null;
      const hasOutputSchema = agent.output_schema != null;
      reset({
        name: agent.name,
        description: agent.description,
        parameters_schema_enabled: hasInputSchema,
        parameters_schema: agent.parameters_schema,
        output_schema_enabled: hasOutputSchema,
        output_schema: agent.output_schema,
        system_prompt: agent.system_prompt || '',
        mcp_servers: agent.mcp_servers,
        skills: agent.skills || [],
        tags: agent.tags || [],
        capabilities: agent.capabilities || [],
        demands: agent.demands,
      });
    } else {
      reset({
        name: '',
        description: '',
        parameters_schema_enabled: false,
        parameters_schema: null,
        output_schema_enabled: false,
        output_schema: null,
        system_prompt: '',
        mcp_servers: null,
        skills: [],
        tags: [],
        capabilities: [],
        demands: null,
      });
    }
    setNameAvailable(null);
    setActiveTab('general');
  }, [agent, reset, isOpen]);

  // Check name availability on blur (not on every keystroke to avoid focus issues)
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
    const updated = addTemplate(watchedMcpServers, templateName);
    setValue('mcp_servers', updated);
  };

  const onSubmit = async (data: FormData) => {
    setSaving(true);
    try {
      // Convert form data to AgentCreate/AgentUpdate format
      // Always send mcp_servers, skills, and tags so clearing them works on update
      // Empty object {} for mcp_servers means "clear/delete"
      // Clean up demands - convert empty strings to undefined, remove empty object
      let cleanDemands: AgentDemands | undefined = undefined;
      if (data.demands) {
        const d = data.demands;
        const cleaned: AgentDemands = {};
        if (d.hostname?.trim()) cleaned.hostname = d.hostname.trim();
        if (d.project_dir?.trim()) cleaned.project_dir = d.project_dir.trim();
        if (d.executor_profile?.trim()) cleaned.executor_profile = d.executor_profile.trim();
        if (d.tags && d.tags.length > 0) cleaned.tags = d.tags;
        // Only include demands if at least one field is set
        if (Object.keys(cleaned).length > 0) {
          cleanDemands = cleaned;
        }
      }

      // Handle parameters_schema: enabled toggle determines if schema is set
      // If disabled or null, schema is null (use default behavior)
      // If enabled and has value, use that value
      const parametersSchema =
        data.parameters_schema_enabled && data.parameters_schema ? data.parameters_schema : null;

      // Handle output_schema: enabled toggle determines if schema is set
      const outputSchema =
        data.output_schema_enabled && data.output_schema ? data.output_schema : null;

      // UI-created agents are always autonomous (procedural agents are runner-owned)
      const createData: AgentCreate = {
        name: data.name,
        description: data.description,
        type: 'autonomous',
        parameters_schema: parametersSchema,
        output_schema: outputSchema,
        system_prompt: data.system_prompt || undefined,
        mcp_servers: data.mcp_servers ?? {}, // null → {} to clear MCP servers
        skills: data.skills, // empty array clears skills
        tags: data.tags, // empty array clears tags
        capabilities: data.capabilities, // capability references
        demands: cleanDemands ?? null, // null clears demands
      };
      await onSave(createData);
      onClose();
    } catch (err) {
      console.error('Failed to save agent:', err);
    } finally {
      setSaving(false);
    }
  };

  const hasMcpServers = watchedMcpServers && Object.keys(watchedMcpServers).length > 0;
  const hasCapabilities = watchedCapabilities && watchedCapabilities.length > 0;

  // Toggle capability selection
  const toggleCapability = (name: string) => {
    const current = watchedCapabilities || [];
    if (current.includes(name)) {
      setValue(
        'capabilities',
        current.filter((c) => c !== name)
      );
    } else {
      setValue('capabilities', [...current, name]);
    }
  };

  // Tab content components
  const GeneralTab = () => (
    <div className="space-y-6">
      {/* Name */}
      <div>
        <div className="flex items-center gap-2 mb-1.5">
          <label className="text-sm font-medium text-gray-700">Agent Name</label>
          <span className="text-red-500">*</span>
          <InfoPopover title="Agent Name">
            <p>Unique identifier for your agent.</p>
            <ul className="list-disc ml-4 mt-2 space-y-1">
              <li>Must start with a letter or number</li>
              <li>Can contain letters, numbers, hyphens, and underscores</li>
              <li>Length: 2-60 characters</li>
            </ul>
          </InfoPopover>
        </div>
        <div className="relative">
          <input
            {...register('name', {
              required: 'Agent name is required',
              pattern: {
                value: /^[a-zA-Z0-9][a-zA-Z0-9_-]*$/,
                message: 'Must start with letter/number, then letters, numbers, hyphens, or underscores',
              },
              minLength: { value: 2, message: 'Minimum 2 characters' },
              maxLength: { value: 60, message: 'Maximum 60 characters' },
              onBlur: handleNameBlur,
            })}
            disabled={isEditing}
            placeholder="my-agent-name"
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
        <div className="flex items-center gap-2 mb-1.5">
          <label className="text-sm font-medium text-gray-700">Description</label>
          <span className="text-red-500">*</span>
          <InfoPopover title="Description">
            <p>Describe what this agent does. This helps users understand the agent's purpose and capabilities.</p>
          </InfoPopover>
        </div>
        <textarea
          {...register('description', {
            required: 'Description is required',
          })}
          placeholder="Describe what this agent does..."
          rows={6}
          className={`input resize-none ${errors.description ? 'border-red-500' : ''}`}
        />
        {errors.description && (
          <p className="mt-1 text-xs text-red-500">{errors.description.message}</p>
        )}
      </div>

      {/* Tags */}
      <div>
        <div className="flex items-center gap-2 mb-1.5">
          <label className="text-sm font-medium text-gray-700">Tags</label>
          <InfoPopover title="Tags">
            <p>Tags control which consumers can discover this agent:</p>
            <ul className="list-disc ml-4 mt-2 space-y-1">
              <li>
                <strong>external:</strong> Entry-point for Claude Desktop, users
              </li>
              <li>
                <strong>internal:</strong> Worker agent for orchestrator framework
              </li>
              <li>Add both tags for agents usable in either context</li>
              <li>Custom tags can be used for project-specific filtering</li>
            </ul>
          </InfoPopover>
        </div>
        <Controller
          name="tags"
          control={control}
          render={({ field }) => (
            <TagSelector
              value={field.value || []}
              onChange={field.onChange}
              placeholder="Add tags (e.g., internal, external, research)..."
            />
          )}
        />
      </div>
    </div>
  );

  const InputTab = () => (
    <div className="h-full flex flex-col" style={{ height: 'calc(85vh - 180px)' }}>
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">Input Schema</label>
          <InfoPopover title="Input Schema">
            <p>
              {watchedSchemaEnabled
                ? 'Define the input parameters for this agent. All parameters will be formatted as an <inputs> block when the agent starts.'
                : 'When disabled, the agent uses the default schema that only accepts {"prompt": "..."}.'}
            </p>
            {watchedSchemaEnabled && (
              <p className="mt-2 text-amber-600">
                Note: If you need free-form user input, add a "prompt" field to your schema
                explicitly.
              </p>
            )}
          </InfoPopover>
        </div>
        <Controller
          name="parameters_schema_enabled"
          control={control}
          render={({ field }) => (
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={field.value}
                onChange={(e) => {
                  field.onChange(e.target.checked);
                  if (!e.target.checked) {
                    setValue('parameters_schema', null);
                  }
                }}
                className="w-4 h-4 text-primary-600 rounded"
              />
              <span className="text-sm font-medium">{field.value ? 'Enabled' : 'Disabled'}</span>
            </label>
          )}
        />
      </div>
      {watchedSchemaEnabled ? (
        <Controller
          name="parameters_schema"
          control={control}
          render={({ field }) => (
            <InputSchemaEditor
              value={field.value ?? null}
              onChange={field.onChange}
              className="flex-1 min-h-0"
            />
          )}
        />
      ) : (
        <p className="text-sm text-gray-500 italic">
          Using default schema: {'{"prompt": "..."}'}
        </p>
      )}
    </div>
  );

  const OutputTab = () => (
    <div className="h-full flex flex-col" style={{ height: 'calc(85vh - 180px)' }}>
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">Output Schema</label>
          <InfoPopover title="Output Schema">
            <p>
              {watchedOutputSchemaEnabled
                ? 'The agent will be instructed to produce JSON matching this schema. Output will be validated and stored in result_data.'
                : 'When disabled, the agent produces free-form text output stored in result_text.'}
            </p>
          </InfoPopover>
        </div>
        <Controller
          name="output_schema_enabled"
          control={control}
          render={({ field }) => (
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={field.value}
                onChange={(e) => {
                  field.onChange(e.target.checked);
                  if (!e.target.checked) {
                    setValue('output_schema', null);
                  }
                }}
                className="w-4 h-4 text-primary-600 rounded"
              />
              <span className="text-sm font-medium">{field.value ? 'Enabled' : 'Disabled'}</span>
            </label>
          )}
        />
      </div>
      {watchedOutputSchemaEnabled ? (
        <Controller
          name="output_schema"
          control={control}
          render={({ field }) => (
            <OutputSchemaEditor
              value={field.value ?? null}
              onChange={field.onChange}
              className="flex-1 min-h-0"
            />
          )}
        />
      ) : (
        <p className="text-sm text-gray-500 italic">Agent will produce free-form text output.</p>
      )}
    </div>
  );

  const PromptTab = () => (
    <div className="h-full flex flex-col">
      {/* Header with Edit/Preview toggle */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">System Prompt</label>
          <InfoPopover title="System Prompt">
            <p>
              Instructions that define the agent's behavior, capabilities, and constraints. Supports
              Markdown formatting.
            </p>
            <p className="mt-2">
              This prompt is sent to the AI model at the start of each conversation to guide its
              responses.
            </p>
          </InfoPopover>
        </div>
        <div className="flex rounded-md border border-gray-300 overflow-hidden">
          <button
            type="button"
            onClick={() => setPromptTab('edit')}
            className={`flex items-center gap-1 px-3 py-1.5 text-xs ${
              promptTab === 'edit'
                ? 'bg-primary-50 text-primary-700'
                : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            <Code className="w-3.5 h-3.5" />
            Edit
          </button>
          <button
            type="button"
            onClick={() => setPromptTab('preview')}
            className={`flex items-center gap-1 px-3 py-1.5 text-xs border-l ${
              promptTab === 'preview'
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
      {promptTab === 'edit' ? (
        <textarea
          {...register('system_prompt')}
          placeholder="# Agent System Prompt&#10;&#10;Define the agent's behavior, capabilities, and constraints..."
          className="flex-1 input font-mono text-sm resize-none min-h-0"
          style={{ height: 'calc(85vh - 220px)' }}
        />
      ) : (
        <div
          className="flex-1 border border-gray-300 rounded-md p-4 overflow-y-auto bg-white min-h-0"
          style={{ height: 'calc(85vh - 220px)' }}
        >
          {getValues('system_prompt') ? (
            <div className="markdown-content prose prose-sm max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{getValues('system_prompt')}</ReactMarkdown>
            </div>
          ) : (
            <p className="text-gray-400 text-sm italic">Enter a system prompt to see the preview</p>
          )}
        </div>
      )}
    </div>
  );

  const CapabilitiesTab = () => (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-1.5">
        <label className="text-sm font-medium text-gray-700">Capabilities</label>
        <InfoPopover title="Capabilities">
          <p>
            Reusable configurations that provide MCP servers and system prompt extensions to your
            agent.
          </p>
          <p className="mt-2">
            Capabilities are defined in the Capabilities page and can be shared across multiple
            agents.
          </p>
        </InfoPopover>
      </div>

      {capabilitiesLoading ? (
        <div className="flex items-center gap-2 text-gray-500 text-sm py-4">
          <Spinner size="sm" />
          <span>Loading capabilities...</span>
        </div>
      ) : availableCapabilities.length === 0 ? (
        <p className="text-sm text-gray-500 italic py-4">
          No capabilities defined. Create capabilities in the Capabilities page first.
        </p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {availableCapabilities.map((cap) => {
            const isSelected = watchedCapabilities?.includes(cap.name);
            // Build tooltip with capability details
            const tooltipParts = [cap.description];
            if (cap.has_mcp || cap.has_text) {
              const includes = [];
              if (cap.has_mcp) includes.push('MCP servers');
              if (cap.has_text) includes.push('system prompt');
              tooltipParts.push(`Includes: ${includes.join(', ')}`);
            }
            return (
              <button
                key={cap.name}
                type="button"
                onClick={() => toggleCapability(cap.name)}
                title={tooltipParts.join('\n')}
                className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
                  isSelected
                    ? 'bg-purple-50 border-purple-300 text-purple-700'
                    : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
                }`}
              >
                {cap.name}
              </button>
            );
          })}
        </div>
      )}

      {hasCapabilities && (
        <div className="mt-4">
          <p className="text-xs text-gray-500 mb-2">Selected capabilities:</p>
          <div className="flex flex-wrap gap-1">
            {watchedCapabilities.map((name) => (
              <Badge key={name} size="sm" variant="default" className="bg-purple-100 text-purple-700">
                {name}
                <button type="button" onClick={() => toggleCapability(name)} className="ml-1">
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            ))}
          </div>
        </div>
      )}

      {!hasCapabilities && !hasMcpServers && (
        <div className="flex items-center gap-2 text-yellow-600 text-sm mt-4 p-3 bg-yellow-50 rounded-md">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>Consider adding at least one capability for the agent</span>
        </div>
      )}
    </div>
  );

  const McpTab = () => (
    <div className="h-full flex flex-col" style={{ height: 'calc(85vh - 180px)' }}>
      <div className="flex items-center gap-2 mb-3 flex-shrink-0">
        <label className="text-sm font-medium text-gray-700">MCP Servers</label>
        <InfoPopover title="MCP Servers">
          <p>Direct MCP server configurations for this agent.</p>
          <p className="mt-2 text-amber-600">
            Note: This will be deprecated in favor of capabilities. Consider using capabilities
            instead for better reusability.
          </p>
        </InfoPopover>
      </div>

      {/* Template Quick Add Buttons */}
      <div className="flex flex-wrap gap-2 mb-3 flex-shrink-0">
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

      {/* JSON Editor */}
      <Controller
        name="mcp_servers"
        control={control}
        render={({ field }) => (
          <MCPJsonEditor
            value={field.value ?? null}
            onChange={field.onChange}
            className="flex-1 min-h-0"
          />
        )}
      />
    </div>
  );

  const RunnerTab = () => (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-2">
        <label className="text-sm font-medium text-gray-700">Runner Demands</label>
        <InfoPopover title="Runner Demands">
          <p>
            Optional constraints that must be satisfied by a runner before this agent can execute.
          </p>
          <p className="mt-2">Leave all fields empty to allow any runner to execute this agent.</p>
        </InfoPopover>
      </div>

      {/* Hostname */}
      <div>
        <div className="flex items-center gap-2 mb-1.5">
          <label className="text-sm font-medium text-gray-700">Hostname</label>
          <InfoPopover title="Hostname">
            <p>Require this agent to run on a specific machine.</p>
            <p className="mt-2">Example: "my-macbook", "prod-server-01"</p>
          </InfoPopover>
        </div>
        <Controller
          name="demands.hostname"
          control={control}
          render={({ field }) => (
            <input
              {...field}
              value={field.value || ''}
              placeholder="e.g., my-macbook"
              className="input"
            />
          )}
        />
      </div>

      {/* Project Directory */}
      <div>
        <div className="flex items-center gap-2 mb-1.5">
          <label className="text-sm font-medium text-gray-700">Project Directory</label>
          <InfoPopover title="Project Directory">
            <p>Require this agent to run in a specific working directory.</p>
            <p className="mt-2">Example: "/Users/me/projects/my-app"</p>
          </InfoPopover>
        </div>
        <Controller
          name="demands.project_dir"
          control={control}
          render={({ field }) => (
            <input
              {...field}
              value={field.value || ''}
              placeholder="e.g., /Users/me/projects/my-app"
              className="input font-mono text-sm"
            />
          )}
        />
      </div>

      {/* Executor Profile */}
      <div>
        <div className="flex items-center gap-2 mb-1.5">
          <label className="text-sm font-medium text-gray-700">Executor Profile</label>
          <InfoPopover title="Executor Profile">
            <p>Require a specific executor profile for this agent.</p>
            <p className="mt-2">Examples: "coding", "research", "supervised"</p>
          </InfoPopover>
        </div>
        <Controller
          name="demands.executor_profile"
          control={control}
          render={({ field }) => (
            <input
              {...field}
              value={field.value || ''}
              placeholder="e.g., coding, research"
              className="input"
            />
          )}
        />
      </div>

      {/* Demand Tags */}
      <div>
        <div className="flex items-center gap-2 mb-1.5">
          <label className="text-sm font-medium text-gray-700">Required Runner Tags</label>
          <InfoPopover title="Required Runner Tags">
            <p>Runner must have ALL specified tags to execute this agent (AND logic).</p>
            <p className="mt-2">Examples: "python", "docker", "nodejs", "gpu"</p>
          </InfoPopover>
        </div>
        <Controller
          name="demands.tags"
          control={control}
          render={({ field }) => (
            <TagSelector
              value={field.value || []}
              onChange={field.onChange}
              placeholder="Add required tags (e.g., python, docker, nodejs)..."
            />
          )}
        />
      </div>
    </div>
  );

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="2xl">
      <form onSubmit={handleSubmit(onSubmit)} className="h-[85vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
          <h2 className="text-lg font-semibold text-gray-900">
            {isEditing ? `Edit Agent: ${agent.name}` : 'New Agent'}
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
          <div className="w-48 bg-gray-50 border-r border-gray-200 p-2 flex flex-col gap-1 flex-shrink-0">
            {tabs.map((tab) => {
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
          <div className="flex-1 overflow-y-auto p-6">
            {activeTab === 'general' && <GeneralTab />}
            {activeTab === 'input' && <InputTab />}
            {activeTab === 'output' && <OutputTab />}
            {activeTab === 'prompt' && <PromptTab />}
            {activeTab === 'capabilities' && <CapabilitiesTab />}
            {activeTab === 'mcp' && <McpTab />}
            {activeTab === 'runner' && <RunnerTab />}
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 bg-gray-50 border-t border-gray-200 flex-shrink-0">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={saving} disabled={!isEditing && nameAvailable === false}>
            {isEditing ? 'Save Changes' : 'Create Agent'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
