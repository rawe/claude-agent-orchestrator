import { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { Modal, Button, Badge, Spinner, TagSelector, InfoPopover } from '@/components/common';
import { MCPJsonEditor } from './MCPJsonEditor';
import { InputSchemaEditor } from './InputSchemaEditor';
import { OutputSchemaEditor } from './OutputSchemaEditor';
import { Agent, AgentCreate, AgentType, AgentDemands, MCPServerConfig, AgentHooks, HookConfig, HookOnError } from '@/types';
import { TEMPLATE_NAMES, addTemplate } from '@/utils/mcpTemplates';
import { useCapabilities } from '@/hooks/useCapabilities';
import { useAgents } from '@/hooks/useAgents';
import { useScripts } from '@/hooks/useScripts';
import { agentService } from '@/services/agentService';
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
  Zap,
  FileCode,
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

// Hook form fields for a single hook
interface HookFormFields {
  enabled: boolean;
  agent_name: string;
  on_error: HookOnError;
  timeout_seconds: number;
}

interface FormData {
  name: string;
  description: string;
  type: AgentType;
  script: string;  // Script name for procedural agents
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
  // Hooks
  on_run_start: HookFormFields;
  on_run_finish: HookFormFields;
}

type TabId = 'general' | 'script' | 'input' | 'output' | 'prompt' | 'capabilities' | 'mcp' | 'runner' | 'hooks';

// Tabs for autonomous agents
const autonomousTabs: { id: TabId; label: string; icon: typeof Settings }[] = [
  { id: 'general', label: 'General', icon: Settings },
  { id: 'input', label: 'Input', icon: FileInput },
  { id: 'output', label: 'Output', icon: FileOutput },
  { id: 'prompt', label: 'Prompt', icon: ScrollText },
  { id: 'capabilities', label: 'Capabilities', icon: Puzzle },
  { id: 'mcp', label: 'MCP', icon: Server },
  { id: 'runner', label: 'Runner', icon: Target },
  { id: 'hooks', label: 'Hooks', icon: Zap },
];

// Tabs for procedural agents (simpler: no input/output/prompt/capabilities/mcp)
const proceduralTabs: { id: TabId; label: string; icon: typeof Settings }[] = [
  { id: 'general', label: 'General', icon: Settings },
  { id: 'script', label: 'Script', icon: FileCode },
  { id: 'runner', label: 'Runner', icon: Target },
  { id: 'hooks', label: 'Hooks', icon: Zap },
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

  // Load available agents for hook agent dropdown
  const { agents: availableAgents, loading: agentsLoading } = useAgents();

  // Load available scripts for procedural agents
  const { scripts: availableScripts, loading: scriptsLoading } = useScripts();

  const isEditing = !!agent;

  // Default values for hooks
  const defaultHookFields: HookFormFields = {
    enabled: false,
    agent_name: '',
    on_error: 'continue',
    timeout_seconds: 300,
  };

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
      type: 'autonomous',
      script: '',
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
      on_run_start: { ...defaultHookFields },
      on_run_finish: { ...defaultHookFields },
    },
  });

  const watchedType = watch('type');
  const watchedScript = watch('script');

  // Select tabs based on agent type
  const tabs = watchedType === 'procedural' ? proceduralTabs : autonomousTabs;

  const watchedSchemaEnabled = watch('parameters_schema_enabled');
  const watchedOutputSchemaEnabled = watch('output_schema_enabled');
  const watchedMcpServers = watch('mcp_servers');
  const watchedCapabilities = watch('capabilities');

  // Helper to convert hook config to form fields
  const hookConfigToFormFields = (hook: HookConfig | null | undefined): HookFormFields => {
    if (!hook) {
      return { ...defaultHookFields };
    }
    return {
      enabled: true,
      agent_name: hook.agent_name,
      on_error: hook.on_error,
      timeout_seconds: hook.timeout_seconds ?? 300,
    };
  };

  // Load agent data when editing - fetch RAW data to avoid showing resolved system_prompt
  useEffect(() => {
    if (agent && isOpen) {
      // Fetch raw agent data for editing (not resolved)
      agentService.getAgentRaw(agent.name).then((rawAgent) => {
        const hasInputSchema = rawAgent.parameters_schema != null;
        const hasOutputSchema = rawAgent.output_schema != null;
        reset({
          name: rawAgent.name,
          description: rawAgent.description,
          type: rawAgent.type || 'autonomous',
          script: rawAgent.script || '',
          parameters_schema_enabled: hasInputSchema,
          parameters_schema: rawAgent.parameters_schema,
          output_schema_enabled: hasOutputSchema,
          output_schema: rawAgent.output_schema,
          system_prompt: rawAgent.system_prompt || '',
          mcp_servers: rawAgent.mcp_servers,
          skills: rawAgent.skills || [],
          tags: rawAgent.tags || [],
          capabilities: rawAgent.capabilities || [],
          demands: rawAgent.demands,
          on_run_start: hookConfigToFormFields(rawAgent.hooks?.on_run_start),
          on_run_finish: hookConfigToFormFields(rawAgent.hooks?.on_run_finish),
        });
      });
    } else if (!agent) {
      reset({
        name: '',
        description: '',
        type: 'autonomous',
        script: '',
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
        on_run_start: { ...defaultHookFields },
        on_run_finish: { ...defaultHookFields },
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

      // Build on_run_start hook config (includes on_error and timeout_seconds)
      const onRunStartHook: HookConfig | null =
        data.on_run_start.enabled && data.on_run_start.agent_name
          ? {
              type: 'agent',
              agent_name: data.on_run_start.agent_name,
              on_error: data.on_run_start.on_error,
              timeout_seconds: data.on_run_start.timeout_seconds,
            }
          : null;

      // Build on_run_finish hook config (fire-and-forget: only type and agent_name)
      // on_error and timeout_seconds are meaningless for fire-and-forget hooks
      const onRunFinishHook: HookConfig | null =
        data.on_run_finish.enabled && data.on_run_finish.agent_name
          ? {
              type: 'agent',
              agent_name: data.on_run_finish.agent_name,
            } as HookConfig
          : null;
      const hooks: AgentHooks | null =
        onRunStartHook || onRunFinishHook
          ? {
              on_run_start: onRunStartHook,
              on_run_finish: onRunFinishHook,
            }
          : null;

      // Build agent create data based on type
      let createData: AgentCreate;

      if (data.type === 'procedural') {
        // Procedural agents: include script, exclude autonomous-specific fields
        createData = {
          name: data.name,
          description: data.description,
          type: 'procedural',
          script: data.script || undefined,
          tags: data.tags, // empty array clears tags
          demands: cleanDemands ?? null, // null clears demands
          hooks: hooks, // lifecycle hooks
        };
      } else {
        // Autonomous agents: include all autonomous-specific fields
        createData = {
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
          hooks: hooks, // lifecycle hooks
        };
      }
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

      {/* Agent Type */}
      <div>
        <div className="flex items-center gap-2 mb-1.5">
          <label className="text-sm font-medium text-gray-700">Agent Type</label>
          <span className="text-red-500">*</span>
          <InfoPopover title="Agent Type">
            <p>Choose the type of agent:</p>
            <ul className="list-disc ml-4 mt-2 space-y-1">
              <li>
                <strong>Autonomous:</strong> AI-powered agents that interpret intent and execute tasks using Claude
              </li>
              <li>
                <strong>Procedural:</strong> Script-based agents that execute predefined scripts with parameters
              </li>
            </ul>
          </InfoPopover>
        </div>
        <Controller
          name="type"
          control={control}
          render={({ field }) => (
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="autonomous"
                  checked={field.value === 'autonomous'}
                  onChange={() => {
                    field.onChange('autonomous');
                    setActiveTab('general');
                  }}
                  disabled={isEditing}
                  className="w-4 h-4 text-primary-600"
                />
                <span className={`text-sm ${isEditing ? 'text-gray-400' : ''}`}>Autonomous</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="procedural"
                  checked={field.value === 'procedural'}
                  onChange={() => {
                    field.onChange('procedural');
                    setActiveTab('general');
                  }}
                  disabled={isEditing}
                  className="w-4 h-4 text-primary-600"
                />
                <span className={`text-sm ${isEditing ? 'text-gray-400' : ''}`}>Procedural</span>
              </label>
            </div>
          )}
        />
        {isEditing && (
          <p className="mt-1 text-xs text-gray-500">Agent type cannot be changed after creation</p>
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

  // Script tab for procedural agents
  const ScriptTab = () => (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-2">
        <label className="text-sm font-medium text-gray-700">Script</label>
        <InfoPopover title="Script">
          <p>
            Select a script to execute when this agent is invoked. The script defines the execution
            logic, input parameters schema, and execution requirements.
          </p>
        </InfoPopover>
      </div>

      {scriptsLoading ? (
        <div className="flex items-center gap-2 text-gray-500 text-sm py-4">
          <Spinner size="sm" />
          <span>Loading scripts...</span>
        </div>
      ) : availableScripts.length === 0 ? (
        <div className="text-sm text-gray-500 italic py-4 p-4 bg-yellow-50 rounded-md border border-yellow-200">
          <p className="font-medium text-yellow-800 mb-1">No scripts available</p>
          <p>Create scripts in the Scripts page first, then come back to select one.</p>
        </div>
      ) : (
        <>
          <Controller
            name="script"
            control={control}
            render={({ field }) => (
              <select
                {...field}
                className={`input ${!watchedScript ? 'text-gray-400' : ''}`}
              >
                <option value="">Select a script...</option>
                {availableScripts.map((s) => (
                  <option key={s.name} value={s.name}>
                    {s.name}
                  </option>
                ))}
              </select>
            )}
          />

          {watchedScript && (
            <div className="mt-4 p-4 bg-gray-50 rounded-md border border-gray-200">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Selected Script Details</h4>
              {(() => {
                const selectedScript = availableScripts.find((s) => s.name === watchedScript);
                if (!selectedScript) return null;
                return (
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
                    <p className="text-xs text-gray-500 mt-2 italic">
                      Parameters schema and demands are inherited from the script.
                      Agent-level demands will be merged with script demands.
                    </p>
                  </div>
                );
              })()}
            </div>
          )}
        </>
      )}
    </div>
  );

  const InputTab = () => (
    <div className="h-full flex flex-col">
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
    <div className="h-full flex flex-col">
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
        />
      ) : (
        <div className="flex-1 border border-gray-300 rounded-md p-4 overflow-y-auto bg-white min-h-0">
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
    <div className="h-full flex flex-col">
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

  // Single hook configuration section (reused for on_run_start and on_run_finish)
  const HookSection = ({
    name,
    title,
    description,
  }: {
    name: 'on_run_start' | 'on_run_finish';
    title: string;
    description: string;
  }) => {
    const watchedEnabled = watch(`${name}.enabled`);
    const watchedAgentName = watch(`${name}.agent_name`);

    // Filter out the current agent from available agents (prevent circular hooks)
    const hookAgentOptions = availableAgents.filter(
      (a) => a.name !== agent?.name && a.status === 'active'
    );

    // on_run_finish is fire-and-forget, so on_error and timeout don't apply
    const showErrorAndTimeout = name === 'on_run_start';

    return (
      <div className="border border-gray-200 rounded-lg p-4">
        {/* Header with enable toggle */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">{title}</label>
            <InfoPopover title={title}>
              <p>{description}</p>
            </InfoPopover>
          </div>
          <Controller
            name={`${name}.enabled`}
            control={control}
            render={({ field }) => (
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={field.value}
                  onChange={(e) => {
                    field.onChange(e.target.checked);
                    // Clear agent_name when disabling
                    if (!e.target.checked) {
                      setValue(`${name}.agent_name`, '');
                    }
                  }}
                  className="w-4 h-4 text-primary-600 rounded"
                />
                <span className="text-sm font-medium">{field.value ? 'Enabled' : 'Disabled'}</span>
              </label>
            )}
          />
        </div>

        {watchedEnabled && (
          <div className="space-y-4">
            {/* Hook Agent Selection */}
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <label className="text-sm font-medium text-gray-700">Hook Agent</label>
                <span className="text-red-500">*</span>
                <InfoPopover title="Hook Agent">
                  <p>Select an agent to execute as this hook. The hook agent will receive context about the run.</p>
                </InfoPopover>
              </div>
              {agentsLoading ? (
                <div className="flex items-center gap-2 text-gray-500 text-sm py-2">
                  <Spinner size="sm" />
                  <span>Loading agents...</span>
                </div>
              ) : hookAgentOptions.length === 0 ? (
                <p className="text-sm text-gray-500 italic py-2">
                  No other agents available. Create another agent to use as a hook.
                </p>
              ) : (
                <Controller
                  name={`${name}.agent_name`}
                  control={control}
                  render={({ field }) => (
                    <select
                      {...field}
                      className={`input ${!watchedAgentName ? 'text-gray-400' : ''}`}
                    >
                      <option value="">Select an agent...</option>
                      {hookAgentOptions.map((a) => (
                        <option key={a.name} value={a.name}>
                          {a.name}
                        </option>
                      ))}
                    </select>
                  )}
                />
              )}
            </div>

            {/* On Error Behavior - only for on_run_start (on_run_finish is fire-and-forget) */}
            {showErrorAndTimeout && (
              <div>
                <div className="flex items-center gap-2 mb-1.5">
                  <label className="text-sm font-medium text-gray-700">On Error</label>
                  <InfoPopover title="On Error Behavior">
                    <p>What to do if the hook fails or times out:</p>
                    <ul className="list-disc ml-4 mt-2 space-y-1">
                      <li><strong>Continue:</strong> Proceed with the run despite hook failure</li>
                      <li><strong>Block:</strong> Fail the run if the hook fails</li>
                    </ul>
                  </InfoPopover>
                </div>
                <Controller
                  name={`${name}.on_error`}
                  control={control}
                  render={({ field }) => (
                    <div className="flex gap-4">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          value="continue"
                          checked={field.value === 'continue'}
                          onChange={() => field.onChange('continue')}
                          className="w-4 h-4 text-primary-600"
                        />
                        <span className="text-sm">Continue</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          value="block"
                          checked={field.value === 'block'}
                          onChange={() => field.onChange('block')}
                          className="w-4 h-4 text-primary-600"
                        />
                        <span className="text-sm">Block</span>
                      </label>
                    </div>
                  )}
                />
              </div>
            )}

            {/* Timeout - only for on_run_start (on_run_finish is fire-and-forget) */}
            {showErrorAndTimeout && (
              <div>
                <div className="flex items-center gap-2 mb-1.5">
                  <label className="text-sm font-medium text-gray-700">Timeout (seconds)</label>
                  <InfoPopover title="Hook Timeout">
                    <p>Maximum time to wait for the hook to complete. Default is 300 seconds (5 minutes).</p>
                  </InfoPopover>
                </div>
                <Controller
                  name={`${name}.timeout_seconds`}
                  control={control}
                  render={({ field }) => (
                    <input
                      type="number"
                      min={1}
                      max={3600}
                      {...field}
                      onChange={(e) => field.onChange(parseInt(e.target.value) || 300)}
                      className="input w-32"
                    />
                  )}
                />
              </div>
            )}

            {/* Fire-and-forget notice for on_run_finish */}
            {!showErrorAndTimeout && (
              <p className="text-sm text-gray-500 italic">
                This hook runs fire-and-forget after the run completes. It cannot block or transform results.
              </p>
            )}
          </div>
        )}
      </div>
    );
  };

  const HooksTab = () => (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-2">
        <label className="text-sm font-medium text-gray-700">Agent Run Hooks</label>
        <InfoPopover title="Agent Run Hooks">
          <p>
            Hooks execute automatically at specific points in the agent run lifecycle.
            Hook agents can validate input, transform parameters, or observe results.
          </p>
        </InfoPopover>
      </div>

      {/* on_run_start hook */}
      <HookSection
        name="on_run_start"
        title="On Run Start"
        description="Executes when a runner claims this agent's run, before execution begins. Can transform parameters or block the run."
      />

      {/* on_run_finish hook */}
      <HookSection
        name="on_run_finish"
        title="On Run Finish"
        description="Executes after a run completes (fire-and-forget). Useful for logging, notifications, or cleanup."
      />
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

          {/* Tab Content
              - flex flex-col: allows children with flex-1 to expand (Input, Output, Prompt, MCP tabs)
              - overflow-y-auto: provides scrolling for tabs without flex-1 children (General, Runner, Hooks)
              Both work together: expandable content fills space, fixed content scrolls if needed */}
          <div className="flex-1 p-6 flex flex-col overflow-y-auto">
            {activeTab === 'general' && <GeneralTab />}
            {activeTab === 'script' && <ScriptTab />}
            {activeTab === 'input' && <InputTab />}
            {activeTab === 'output' && <OutputTab />}
            {activeTab === 'prompt' && <PromptTab />}
            {activeTab === 'capabilities' && <CapabilitiesTab />}
            {activeTab === 'mcp' && <McpTab />}
            {activeTab === 'runner' && <RunnerTab />}
            {activeTab === 'hooks' && <HooksTab />}
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
