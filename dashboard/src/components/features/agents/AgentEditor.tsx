import { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { Modal, Button, Badge, Spinner, TagSelector } from '@/components/common';
import { MCPJsonEditor } from './MCPJsonEditor';
import { Agent, AgentCreate, AgentDemands, MCPServerConfig, SKILLS } from '@/types';
import { TEMPLATE_NAMES, addTemplate } from '@/utils/mcpTemplates';
import { useCapabilities } from '@/hooks/useCapabilities';
import { Eye, Code, X, AlertCircle, Info, Package } from 'lucide-react';
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
  system_prompt: string;
  mcp_servers: Record<string, MCPServerConfig> | null;
  skills: string[];
  tags: string[];
  capabilities: string[];
  demands: AgentDemands | null;
}

export function AgentEditor({
  isOpen,
  onClose,
  onSave,
  agent,
  checkNameAvailable,
}: AgentEditorProps) {
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
    formState: { errors },
  } = useForm<FormData>({
    defaultValues: {
      name: '',
      description: '',
      system_prompt: '',
      mcp_servers: null,
      skills: [],
      tags: [],
      capabilities: [],
      demands: null,
    },
  });

  const watchedName = watch('name');
  const watchedPrompt = watch('system_prompt');
  const watchedMcpServers = watch('mcp_servers');
  const watchedSkills = watch('skills');
  const watchedCapabilities = watch('capabilities');

  // Load agent data when editing
  useEffect(() => {
    if (agent) {
      reset({
        name: agent.name,
        description: agent.description,
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
        system_prompt: '',
        mcp_servers: null,
        skills: [],
        tags: [],
        capabilities: [],
        demands: null,
      });
    }
    setNameAvailable(null);
  }, [agent, reset, isOpen]);

  // Check name availability (debounced)
  useEffect(() => {
    if (isEditing || !watchedName || watchedName.length < 2) {
      setNameAvailable(null);
      return;
    }

    const timer = setTimeout(async () => {
      setCheckingName(true);
      try {
        const available = await checkNameAvailable(watchedName);
        setNameAvailable(available);
      } catch {
        setNameAvailable(null);
      } finally {
        setCheckingName(false);
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [watchedName, isEditing, checkNameAvailable]);

  const handleAddTemplate = (templateName: string) => {
    const updated = addTemplate(watchedMcpServers, templateName);
    setValue('mcp_servers', updated);
  };

  const toggleSkill = (name: string) => {
    const current = watchedSkills || [];
    if (current.includes(name)) {
      setValue(
        'skills',
        current.filter((s) => s !== name)
      );
    } else {
      setValue('skills', [...current, name]);
    }
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
        if (d.executor_type?.trim()) cleaned.executor_type = d.executor_type.trim();
        if (d.tags && d.tags.length > 0) cleaned.tags = d.tags;
        // Only include demands if at least one field is set
        if (Object.keys(cleaned).length > 0) {
          cleanDemands = cleaned;
        }
      }

      const createData: AgentCreate = {
        name: data.name,
        description: data.description,
        system_prompt: data.system_prompt || undefined,
        mcp_servers: data.mcp_servers ?? {},  // null → {} to clear MCP servers
        skills: data.skills,                   // empty array clears skills
        tags: data.tags,                       // empty array clears tags
        capabilities: data.capabilities,       // capability references
        demands: cleanDemands ?? null,         // null clears demands
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
  const hasSkills = watchedSkills && watchedSkills.length > 0;
  const hasCapabilities = watchedCapabilities && watchedCapabilities.length > 0;

  // Toggle capability selection
  const toggleCapability = (name: string) => {
    const current = watchedCapabilities || [];
    if (current.includes(name)) {
      setValue('capabilities', current.filter((c) => c !== name));
    } else {
      setValue('capabilities', [...current, name]);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? `Edit Agent: ${agent.name}` : 'New Agent'}
      size="xl"
    >
      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto">
          {/* Basic Information */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-gray-900">Basic Information</h3>

            {/* Name */}
            <div>
              <label className="label">Agent Name *</label>
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
                  })}
                  disabled={isEditing}
                  placeholder="my-agent-name"
                  className={`input ${isEditing ? 'bg-gray-100' : ''} ${
                    errors.name ? 'border-red-500' : ''
                  }`}
                />
                {checkingName && (
                  <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    <Spinner size="sm" />
                  </div>
                )}
              </div>
              {errors.name && (
                <p className="mt-1 text-xs text-red-500">{errors.name.message}</p>
              )}
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
                {...register('description', {
                  required: 'Description is required',
                })}
                placeholder="Describe what this agent does..."
                rows={3}
                className={`input resize-none ${errors.description ? 'border-red-500' : ''}`}
              />
              {errors.description && (
                <p className="mt-1 text-xs text-red-500">{errors.description.message}</p>
              )}
            </div>

            {/* Tags */}
            <div>
              <label className="label">Tags</label>
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
              <div className="mt-2 flex items-start gap-2 text-xs text-gray-500">
                <Info className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <div>
                  <p>Tags control which consumers can discover this agent:</p>
                  <ul className="mt-1 ml-4 list-disc space-y-0.5">
                    <li><strong>external:</strong> Entry-point for Claude Desktop, users</li>
                    <li><strong>internal:</strong> Worker agent for orchestrator framework</li>
                    <li>Add both tags for agents usable in either context</li>
                    <li>Custom tags can be used for project-specific filtering</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* System Prompt */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="label mb-0">System Prompt</label>
              <div className="flex rounded-md border border-gray-300 overflow-hidden">
                <button
                  type="button"
                  onClick={() => setPromptTab('edit')}
                  className={`flex items-center gap-1 px-3 py-1 text-xs ${
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
                  className={`flex items-center gap-1 px-3 py-1 text-xs border-l ${
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

            {promptTab === 'edit' ? (
              <textarea
                {...register('system_prompt')}
                placeholder="# Agent System Prompt&#10;&#10;Define the agent's behavior, capabilities, and constraints..."
                rows={12}
                className="input font-mono text-sm resize-none"
              />
            ) : (
              <div className="border border-gray-300 rounded-md p-4 min-h-[288px] max-h-[288px] overflow-auto bg-white">
                {watchedPrompt ? (
                  <div className="markdown-content prose prose-sm max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{watchedPrompt}</ReactMarkdown>
                  </div>
                ) : (
                  <p className="text-gray-400 text-sm italic">
                    Enter a system prompt to see the preview
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Capabilities */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-gray-900">Capabilities</h3>

            {/* MCP Servers - JSON Editor */}
            <div>
              <label className="label">MCP Servers</label>

              {/* Template Quick Add Buttons */}
              <div className="flex flex-wrap gap-2 mb-3">
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
                  />
                )}
              />
            </div>

            {/* Skills */}
            <div>
              <label className="label">Skills <span className="text-xs text-gray-400 font-normal">(coming soon)</span></label>
              <div className="flex flex-wrap gap-2">
                {SKILLS.map((skill) => (
                  <button
                    key={skill.name}
                    type="button"
                    onClick={() => !skill.disabled && toggleSkill(skill.name)}
                    disabled={skill.disabled}
                    className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
                      skill.disabled
                        ? 'bg-gray-100 border-gray-200 text-gray-400 cursor-not-allowed'
                        : watchedSkills?.includes(skill.name)
                        ? 'bg-primary-50 border-primary-300 text-primary-700'
                        : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    {skill.label}
                  </button>
                ))}
              </div>
              {hasSkills && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {watchedSkills.map((name) => (
                    <Badge key={name} size="sm" variant="info">
                      {name}
                      <button
                        type="button"
                        onClick={() => toggleSkill(name)}
                        className="ml-1"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}
            </div>

            {/* Capabilities */}
            <div>
              <label className="label">
                <span className="flex items-center gap-1.5">
                  <Package className="w-4 h-4" />
                  Capabilities
                </span>
              </label>
              <p className="text-xs text-gray-500 mb-2">
                Reusable configurations that provide MCP servers and system prompt extensions.
              </p>
              {capabilitiesLoading ? (
                <div className="flex items-center gap-2 text-gray-500 text-sm py-2">
                  <Spinner size="sm" />
                  <span>Loading capabilities...</span>
                </div>
              ) : availableCapabilities.length === 0 ? (
                <p className="text-sm text-gray-500 italic py-2">
                  No capabilities defined. Create capabilities in the Capabilities page first.
                </p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {availableCapabilities.map((cap) => (
                    <button
                      key={cap.name}
                      type="button"
                      onClick={() => toggleCapability(cap.name)}
                      title={cap.description}
                      className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
                        watchedCapabilities?.includes(cap.name)
                          ? 'bg-purple-50 border-purple-300 text-purple-700'
                          : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
                      }`}
                    >
                      {cap.name}
                      {cap.has_mcp && <span className="ml-1 text-xs opacity-60">⚙</span>}
                      {cap.has_text && <span className="ml-0.5 text-xs opacity-60">📝</span>}
                    </button>
                  ))}
                </div>
              )}
              {hasCapabilities && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {watchedCapabilities.map((name) => (
                    <Badge key={name} size="sm" variant="default" className="bg-purple-100 text-purple-700">
                      {name}
                      <button
                        type="button"
                        onClick={() => toggleCapability(name)}
                        className="ml-1"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}
            </div>

            {!hasMcpServers && !hasSkills && !hasCapabilities && (
              <div className="flex items-center gap-2 text-yellow-600 text-sm">
                <AlertCircle className="w-4 h-4" />
                <span>Consider adding at least one capability for the agent</span>
              </div>
            )}
          </div>

          {/* Runner Demands (ADR-011) */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-gray-900">Runner Demands</h3>
            <div className="flex items-start gap-2 text-xs text-gray-500 mb-3">
              <Info className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <p>
                Optional constraints that must be satisfied by a runner before this agent can execute.
                Leave empty to allow any runner to execute this agent.
              </p>
            </div>

            {/* Hostname */}
            <div>
              <label className="label">Hostname</label>
              <Controller
                name="demands.hostname"
                control={control}
                render={({ field }) => (
                  <input
                    {...field}
                    value={field.value || ''}
                    placeholder="e.g., my-macbook (must run on this specific host)"
                    className="input"
                  />
                )}
              />
            </div>

            {/* Project Directory */}
            <div>
              <label className="label">Project Directory</label>
              <Controller
                name="demands.project_dir"
                control={control}
                render={({ field }) => (
                  <input
                    {...field}
                    value={field.value || ''}
                    placeholder="e.g., /Users/me/projects/my-app (must run in this directory)"
                    className="input font-mono text-sm"
                  />
                )}
              />
            </div>

            {/* Executor Type */}
            <div>
              <label className="label">Executor Type</label>
              <Controller
                name="demands.executor_type"
                control={control}
                render={({ field }) => (
                  <input
                    {...field}
                    value={field.value || ''}
                    placeholder="e.g., claude-code (must use this executor)"
                    className="input"
                  />
                )}
              />
            </div>

            {/* Demand Tags */}
            <div>
              <label className="label">Required Runner Tags</label>
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
              <p className="mt-1 text-xs text-gray-500">
                Runner must have ALL specified tags to execute this agent.
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 bg-gray-50 border-t">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            loading={saving}
            disabled={!isEditing && nameAvailable === false}
          >
            {isEditing ? 'Save Changes' : 'Create Agent'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
