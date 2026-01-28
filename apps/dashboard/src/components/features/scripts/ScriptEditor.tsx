import { useState, useEffect, useCallback } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Modal, Button, Spinner, TagSelector } from '@/components/common';
import { Script, ScriptCreate } from '@/types/script';
import { AgentDemands } from '@/types/agent';
import { AlertCircle, Check, Code, Eye, FileCode, Settings, FileInput, Target, X, Sparkles } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useAiAssist } from '@/hooks/useAiAssist';
import { useAiGroup } from '@/hooks/useAiGroup';
import {
  scriptAssistantDefinition,
  type ScriptAssistantInput,
  type ScriptAssistantOutput,
  ScriptAssistantOutputKeys as OUT,
} from '@/lib/system-agents';

interface ScriptEditorProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: ScriptCreate) => Promise<void>;
  script?: Script | null;
  checkNameAvailable: (name: string) => Promise<boolean>;
}

// Zod schema for form validation
const formSchema = z.object({
  name: z
    .string()
    .min(2, 'Minimum 2 characters')
    .max(60, 'Maximum 60 characters')
    .regex(/^[a-zA-Z0-9][a-zA-Z0-9_-]*$/, 'Must start with letter/number, then letters, numbers, hyphens, or underscores'),
  description: z.string().min(1, 'Description is required'),
  script_file: z
    .string()
    .min(1, 'Script file name is required')
    .regex(/^[a-zA-Z0-9._-]+$/, 'Only letters, numbers, dots, hyphens, and underscores allowed'),
  script_content: z.string().min(1, 'Script content is required'),
  parameters_schema_enabled: z.boolean(),
  parameters_schema: z.record(z.unknown()).nullable(),
  demands_enabled: z.boolean(),
  demands: z.object({
    hostname: z.string().optional(),
    project_dir: z.string().optional(),
    executor_profile: z.string().optional(),
    tags: z.array(z.string()).optional(),
  }).nullable(),
});

type FormData = z.infer<typeof formSchema>;

// Type-safe form field names
const F = {
  name: 'name',
  description: 'description',
  script_file: 'script_file',
  script_content: 'script_content',
  parameters_schema_enabled: 'parameters_schema_enabled',
  parameters_schema: 'parameters_schema',
  demands_enabled: 'demands_enabled',
  demands: 'demands',
} as const satisfies Record<keyof FormData, keyof FormData>;

type TabId = 'general' | 'script' | 'schema' | 'demands';

const tabs: { id: TabId; label: string; icon: typeof Settings }[] = [
  { id: 'general', label: 'General', icon: Settings },
  { id: 'script', label: 'Script', icon: FileCode },
  { id: 'schema', label: 'Schema', icon: FileInput },
  { id: 'demands', label: 'Runner', icon: Target },
];

// Default schema template
const DEFAULT_SCHEMA_TEMPLATE = {
  type: 'object',
  properties: {
    input: {
      type: 'string',
      description: 'Input parameter',
    },
  },
  additionalProperties: false,
};


export function ScriptEditor({
  isOpen,
  onClose,
  onSave,
  script,
  checkNameAvailable,
}: ScriptEditorProps) {
  const [activeTab, setActiveTab] = useState<TabId>('general');
  const [descriptionTab, setDescriptionTab] = useState<'edit' | 'preview'>('edit');
  const [saving, setSaving] = useState(false);
  const [nameAvailable, setNameAvailable] = useState<boolean | null>(null);
  const [checkingName, setCheckingName] = useState(false);
  const [schemaText, setSchemaText] = useState('');
  const [schemaError, setSchemaError] = useState<string | null>(null);
  const [schemaValid, setSchemaValid] = useState(true);

  const isEditing = !!script;

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
    mode: 'onBlur', // Only validate when leaving fields, not while typing
    reValidateMode: 'onBlur', // After failed submit, still only re-validate on blur
    defaultValues: {
      name: '',
      description: '',
      script_file: '',
      script_content: '',
      parameters_schema_enabled: false,
      parameters_schema: null,
      demands_enabled: false,
      demands: null,
    },
  });

  const watchedSchemaEnabled = watch('parameters_schema_enabled');
  const watchedDemandsEnabled = watch('demands_enabled');

  // State for description preview (only updated when clicking Preview tab)
  const [previewContent, setPreviewContent] = useState('');

  // Load script data when editing
  useEffect(() => {
    if (script) {
      // Loose equality (!=) catches both null and undefined
      // API uses response_model_exclude_none=True, so missing fields are undefined, not null
      const hasSchema = script.parameters_schema != null;
      const hasDemands = script.demands !== null;
      reset({
        name: script.name,
        description: script.description,
        script_file: script.script_file,
        script_content: script.script_content,
        parameters_schema_enabled: hasSchema,
        parameters_schema: script.parameters_schema,
        demands_enabled: hasDemands,
        demands: script.demands,
      });
      if (hasSchema && script.parameters_schema) {
        setSchemaText(JSON.stringify(script.parameters_schema, null, 2));
        setSchemaValid(true);
        setSchemaError(null);
      } else {
        setSchemaText(JSON.stringify(DEFAULT_SCHEMA_TEMPLATE, null, 2));
      }
    } else {
      reset({
        name: '',
        description: '',
        script_file: '',
        script_content: '',
        parameters_schema_enabled: false,
        parameters_schema: null,
        demands_enabled: false,
        demands: null,
      });
      setSchemaText(JSON.stringify(DEFAULT_SCHEMA_TEMPLATE, null, 2));
    }
    setNameAvailable(null);
    setActiveTab('general');
  }, [script, reset, isOpen]);

  // Check name availability on blur
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

  // Validate and update schema
  const validateAndUpdateSchema = useCallback(
    (text: string) => {
      setSchemaText(text);

      if (!text.trim()) {
        setSchemaError('Schema cannot be empty');
        setSchemaValid(false);
        return;
      }

      try {
        const parsed = JSON.parse(text);

        if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
          setSchemaError('Schema must be a JSON object');
          setSchemaValid(false);
          return;
        }

        if (parsed.type && parsed.type !== 'object') {
          setSchemaError('Schema type must be "object"');
          setSchemaValid(false);
          return;
        }

        setSchemaError(null);
        setSchemaValid(true);
        setValue(F.parameters_schema, parsed);
      } catch (e) {
        if (e instanceof SyntaxError) {
          setSchemaError(`Invalid JSON: ${e.message}`);
        } else {
          setSchemaError('Invalid JSON');
        }
        setSchemaValid(false);
      }
    },
    [setValue]
  );

  const handlePrettifySchema = () => {
    try {
      const parsed = JSON.parse(schemaText);
      setSchemaText(JSON.stringify(parsed, null, 2));
    } catch {
      // Ignore if invalid JSON
    }
  };

  // AI Assist: Script Assistant for creating/editing scripts
  const scriptAssistantAi = useAiAssist<ScriptAssistantInput, ScriptAssistantOutput>({
    agentName: scriptAssistantDefinition.name,
    buildInput: (userRequest) => {
      const scriptContent = getValues(F.script_content);
      const schemaEnabled = getValues(F.parameters_schema_enabled);
      const schema = getValues(F.parameters_schema);

      // Build input - script_content is optional (empty for new scripts)
      const input: ScriptAssistantInput = {
        user_request: userRequest,
      };

      // Include script_content if it exists (edit mode)
      if (scriptContent?.trim()) {
        input.script_content = scriptContent;
      }

      // Include current schema if defined
      if (schemaEnabled && schema) {
        input.parameters_schema = schema;
      }

      return input;
    },
    defaultRequest: isEditing ? 'Review and improve this script' : 'Create a simple hello world script',
  });

  // AI Group: Aggregates all AI instances for unified protection
  // Add more AI instances to this array as they are added to the component
  const ai = useAiGroup([scriptAssistantAi]);

  // Handle accepting AI result - applies all generated fields
  const handleAiAccept = () => {
    const result = scriptAssistantAi.result;
    if (!result) return;

    // Apply name (only if creating new script or name is empty)
    if (result[OUT.name] && !isEditing) {
      setValue(F.name, result[OUT.name]);
      // Reset name availability since we have a new name
      setNameAvailable(null);
    }

    // Apply description
    if (result[OUT.description]) {
      setValue(F.description, result[OUT.description]);
    }

    // Apply script_file
    if (result[OUT.script_file]) {
      setValue(F.script_file, result[OUT.script_file]);
    }

    // Apply script content
    if (result[OUT.script]) {
      setValue(F.script_content, result[OUT.script]);
    }

    // Apply parameters schema if returned
    if (result[OUT.parameters_schema]) {
      const newSchema = result[OUT.parameters_schema];
      setValue(F.parameters_schema, newSchema ?? null);
      setValue(F.parameters_schema_enabled, true);
      setSchemaText(JSON.stringify(newSchema, null, 2));
      setSchemaValid(true);
      setSchemaError(null);
    }

    scriptAssistantAi.accept();
  };

  const onSubmit = async (data: FormData) => {
    // Check name availability if not yet checked (user typed name and clicked Save without leaving field)
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

    setSaving(true);
    try {
      // Clean up demands
      let cleanDemands: AgentDemands | undefined = undefined;
      if (data.demands_enabled && data.demands) {
        const d = data.demands;
        const cleaned: AgentDemands = {};
        if (d.hostname?.trim()) cleaned.hostname = d.hostname.trim();
        if (d.project_dir?.trim()) cleaned.project_dir = d.project_dir.trim();
        if (d.executor_profile?.trim()) cleaned.executor_profile = d.executor_profile.trim();
        if (d.tags && d.tags.length > 0) cleaned.tags = d.tags;
        if (Object.keys(cleaned).length > 0) {
          cleanDemands = cleaned;
        }
      }

      // Handle parameters_schema
      const parametersSchema =
        data.parameters_schema_enabled && data.parameters_schema ? data.parameters_schema : undefined;

      const createData: ScriptCreate = {
        name: data.name,
        description: data.description,
        script_file: data.script_file,
        script_content: data.script_content,
        parameters_schema: parametersSchema,
        demands: cleanDemands,
      };
      await onSave(createData);
      onClose();
    } catch (err) {
      console.error('Failed to save script:', err);
    } finally {
      setSaving(false);
    }
  };

  const GeneralTab = () => (
    <div className="h-full flex flex-col gap-6">
      {/* AI Assistant Card */}
      <div className="p-4 bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200 rounded-lg">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <Sparkles className="w-5 h-5 text-purple-600" />
              <span className="font-medium text-purple-900">AI Script Assistant</span>
            </div>
            <p className="text-sm text-purple-700">
              {isEditing
                ? 'Describe changes you want to make to this script.'
                : 'Describe what you want the script to do and AI will generate it for you.'}
            </p>
          </div>
          {scriptAssistantAi.isLoading ? (
            <button
              type="button"
              onClick={scriptAssistantAi.cancel}
              className="flex items-center gap-2 px-4 py-2 text-sm rounded-md bg-red-100 hover:bg-red-200 text-red-700 font-medium"
            >
              <Spinner size="sm" />
              Cancel
            </button>
          ) : (
            <button
              type="button"
              onClick={scriptAssistantAi.toggle}
              disabled={!scriptAssistantAi.available || scriptAssistantAi.checkingAvailability}
              className={`flex items-center gap-2 px-4 py-2 text-sm rounded-md font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors ${
                scriptAssistantAi.showInput
                  ? 'bg-purple-600 text-white hover:bg-purple-700'
                  : scriptAssistantAi.available
                    ? 'bg-purple-100 hover:bg-purple-200 text-purple-700'
                    : 'bg-gray-100 text-gray-400'
              }`}
              title={scriptAssistantAi.unavailableReason || 'AI Assistant'}
            >
              {scriptAssistantAi.checkingAvailability ? (
                <Spinner size="sm" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              {scriptAssistantAi.showInput ? 'Hide' : isEditing ? 'Edit with AI' : 'Generate with AI'}
            </button>
          )}
        </div>

        {/* AI Input */}
        {scriptAssistantAi.showInput && !scriptAssistantAi.isLoading && (
          <div className="mt-4 flex gap-2">
            <input
              type="text"
              value={scriptAssistantAi.userRequest}
              onChange={(e) => scriptAssistantAi.setUserRequest(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && scriptAssistantAi.submit()}
              placeholder={
                isEditing
                  ? "What changes do you want? (e.g., 'Add error handling', 'Optimize performance')"
                  : "What should the script do? (e.g., 'Backup PostgreSQL database to S3')"
              }
              className="input flex-1 text-sm"
              autoFocus
            />
            <button
              type="button"
              onClick={scriptAssistantAi.submit}
              className="px-4 py-2 text-sm bg-purple-600 hover:bg-purple-700 text-white rounded-md font-medium"
            >
              Generate
            </button>
          </div>
        )}

        {/* AI Error */}
        {scriptAssistantAi.error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-700">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <div className="flex-1 whitespace-pre-line">{scriptAssistantAi.error}</div>
              <button
                type="button"
                onClick={scriptAssistantAi.clearError}
                className="flex-shrink-0 text-red-400 hover:text-red-600"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Name */}
      <div>
        <label className="label">Script Name *</label>
        <div className="relative">
          <input
            {...register('name', { onBlur: handleNameBlur })}
            disabled={isEditing}
            placeholder="my-script-name"
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

      {/* Description - expands to fill remaining space */}
      <div className="flex-1 flex flex-col min-h-0">
        <div className="flex items-center justify-between mb-2">
          <label className="label mb-0">Description *</label>
          <div className="flex rounded-md border border-gray-300 overflow-hidden">
            <button
              type="button"
              onClick={() => setDescriptionTab('edit')}
              className={`flex items-center gap-1 px-3 py-1 text-xs ${
                descriptionTab === 'edit'
                  ? 'bg-primary-50 text-primary-700'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              <Code className="w-3.5 h-3.5" />
              Edit
            </button>
            <button
              type="button"
              onClick={() => {
                setPreviewContent(getValues(F.description) || '');
                setDescriptionTab('preview');
              }}
              className={`flex items-center gap-1 px-3 py-1 text-xs border-l ${
                descriptionTab === 'preview'
                  ? 'bg-primary-50 text-primary-700'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              Preview
            </button>
          </div>
        </div>
        {descriptionTab === 'edit' ? (
          <textarea
            {...register('description')}
            placeholder="Describe what this script does. Supports Markdown."
            className={`input resize-none flex-1 ${errors.description ? 'border-red-500' : ''}`}
          />
        ) : (
          <div className="border border-gray-300 rounded-md p-4 flex-1 overflow-auto bg-white">
            {previewContent ? (
              <div className="markdown-content prose prose-sm max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{previewContent}</ReactMarkdown>
              </div>
            ) : (
              <p className="text-gray-400 text-sm italic">Enter a description to see the preview</p>
            )}
          </div>
        )}
        {errors.description && (
          <p className="mt-1 text-xs text-red-500">{errors.description.message}</p>
        )}
      </div>
    </div>
  );

  const ScriptTab = () => (
    <div className="h-full flex flex-col gap-4">
      {/* Script File Name - compact row */}
      <div>
        <label className="label">File Name *</label>
        <div className="relative">
          <FileCode className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            {...register('script_file')}
            placeholder="run.py"
            className={`input pl-10 ${errors.script_file ? 'border-red-500' : ''}`}
          />
        </div>
        {errors.script_file && (
          <p className="mt-1 text-xs text-red-500">{errors.script_file.message}</p>
        )}
      </div>

      {/* Script Content - fills remaining space */}
      <div className="flex-1 flex flex-col min-h-0">
        <div className="flex items-center justify-between mb-2">
          <label className="label mb-0">Script Content *</label>
          <p className="text-xs text-gray-500">Parameters passed as CLI arguments (--key value)</p>
        </div>

        <textarea
          {...register('script_content')}
          placeholder="#!/usr/bin/env -S uv run --script&#10;# /// script&#10;# requires-python = &quot;>=3.11&quot;&#10;# dependencies = []&#10;# ///&#10;&#10;print(&quot;Hello, World!&quot;)"
          className={`input font-mono text-sm resize-none flex-1 ${errors.script_content ? 'border-red-500' : ''}`}
        />
        {errors.script_content && (
          <p className="mt-1 text-xs text-red-500">{errors.script_content.message}</p>
        )}
      </div>
    </div>
  );

  const SchemaTab = () => (
    <div className="h-full flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <label className="label mb-0">Parameters Schema</label>
          <p className="text-xs text-gray-500 mt-1">
            Define JSON Schema for input parameters validation
          </p>
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
                  if (e.target.checked) {
                    // Initialize with template
                    setSchemaText(JSON.stringify(DEFAULT_SCHEMA_TEMPLATE, null, 2));
                    setValue(F.parameters_schema, DEFAULT_SCHEMA_TEMPLATE);
                    setSchemaValid(true);
                    setSchemaError(null);
                  } else {
                    setValue(F.parameters_schema, null);
                  }
                }}
                className="w-4 h-4 text-primary-600 rounded"
              />
              <span className="text-sm font-medium">{field.value ? 'Enabled' : 'Disabled'}</span>
            </label>
          )}
        />
      </div>

      {watchedSchemaEnabled && (
        <div className="flex-1 flex flex-col min-h-0">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              {schemaValid ? (
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
              onClick={handlePrettifySchema}
              className="flex items-center gap-1 px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded"
            >
              <Code className="w-3 h-3" />
              Prettify
            </button>
          </div>

          <textarea
            value={schemaText}
            onChange={(e) => validateAndUpdateSchema(e.target.value)}
            placeholder={JSON.stringify(DEFAULT_SCHEMA_TEMPLATE, null, 2)}
            className={`input font-mono text-sm resize-none flex-1 ${
              !schemaValid ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : ''
            }`}
          />

          {schemaError && (
            <p className="text-xs text-red-500 flex items-center gap-1 mt-2">
              <AlertCircle className="w-3 h-3" />
              {schemaError}
            </p>
          )}
        </div>
      )}

      {!watchedSchemaEnabled && (
        <p className="text-sm text-gray-500 italic">
          No schema defined. All parameters will be passed to the script without validation.
        </p>
      )}
    </div>
  );

  const DemandsTab = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <label className="label mb-0">Runner Demands</label>
          <p className="text-xs text-gray-500 mt-1">
            Requirements that must be satisfied by a runner to execute this script
          </p>
        </div>
        <Controller
          name="demands_enabled"
          control={control}
          render={({ field }) => (
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={field.value}
                onChange={(e) => {
                  field.onChange(e.target.checked);
                  if (!e.target.checked) {
                    setValue(F.demands, null);
                  } else {
                    setValue(F.demands, {});
                  }
                }}
                className="w-4 h-4 text-primary-600 rounded"
              />
              <span className="text-sm font-medium">{field.value ? 'Enabled' : 'Disabled'}</span>
            </label>
          )}
        />
      </div>

      {watchedDemandsEnabled && (
        <div className="space-y-4 pt-4 border-t border-gray-200">
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
                  placeholder="e.g., my-macbook"
                  className="input"
                />
              )}
            />
            <p className="mt-1 text-xs text-gray-500">Require script to run on a specific machine</p>
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
                  placeholder="e.g., /Users/me/projects/my-app"
                  className="input font-mono text-sm"
                />
              )}
            />
            <p className="mt-1 text-xs text-gray-500">Require script to run in a specific directory</p>
          </div>

          {/* Executor Profile */}
          <div>
            <label className="label">Executor Profile</label>
            <Controller
              name="demands.executor_profile"
              control={control}
              render={({ field }) => (
                <input
                  {...field}
                  value={field.value || ''}
                  placeholder="e.g., procedural"
                  className="input"
                />
              )}
            />
            <p className="mt-1 text-xs text-gray-500">Require a specific executor profile</p>
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
                  placeholder="Add required tags (e.g., python, docker)..."
                />
              )}
            />
            <p className="mt-1 text-xs text-gray-500">
              Runner must have ALL specified tags (AND logic)
            </p>
          </div>
        </div>
      )}

      {!watchedDemandsEnabled && (
        <p className="text-sm text-gray-500 italic">No demands defined. Any runner can execute this script.</p>
      )}
    </div>
  );

  return (
    <>
      <Modal isOpen={isOpen} onClose={() => { if (!ai.isAnyLoading && !ai.hasAnyResult) onClose(); }} size="xl">
        <form onSubmit={handleSubmit(onSubmit)} className="h-[75vh] flex flex-col">
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
            <h2 className="text-lg font-semibold text-gray-900">
              {isEditing ? `Edit Script: ${script.name}` : 'New Script'}
            </h2>
            <button
              type="button"
              onClick={onClose}
              disabled={ai.isAnyLoading}
              className="text-gray-400 hover:text-gray-500 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Body: Sidebar + Content */}
          <div className="flex-1 flex min-h-0">
            {/* Sidebar Tabs */}
            <div className="w-40 bg-gray-50 border-r border-gray-200 p-2 flex flex-col gap-1 flex-shrink-0">
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

            {/* Tab Content - all tabs always rendered (hidden when inactive) for form validation */}
            <div className={`flex-1 p-6 flex flex-col overflow-y-auto ${activeTab !== 'general' ? 'hidden' : ''}`}>
              <GeneralTab />
            </div>
            <div className={`flex-1 p-6 flex flex-col overflow-y-auto ${activeTab !== 'script' ? 'hidden' : ''}`}>
              <ScriptTab />
            </div>
            <div className={`flex-1 p-6 flex flex-col overflow-y-auto ${activeTab !== 'schema' ? 'hidden' : ''}`}>
              <SchemaTab />
            </div>
            <div className={`flex-1 p-6 flex flex-col overflow-y-auto ${activeTab !== 'demands' ? 'hidden' : ''}`}>
              <DemandsTab />
            </div>
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-3 px-6 py-4 bg-gray-50 border-t border-gray-200 flex-shrink-0">
            <Button type="button" variant="secondary" onClick={onClose} disabled={ai.isAnyLoading}>
              Cancel
            </Button>
            <Button
              type="submit"
              loading={saving}
              disabled={ai.isAnyLoading || (!isEditing && nameAvailable === false)}
            >
              {isEditing ? 'Save Changes' : 'Create Script'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* AI Result Modal - rendered outside main modal to avoid z-index issues */}
      {scriptAssistantAi.result && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50"
          onClick={(e) => e.stopPropagation()}
        >
          <div
            className="bg-white rounded-lg shadow-xl w-[90vw] max-w-4xl max-h-[85vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-purple-50">
              <span className="text-lg font-semibold text-purple-700 flex items-center gap-2">
                <Sparkles className="w-5 h-5" />
                AI Generated Script
              </span>
              <div className="flex items-center gap-3">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={scriptAssistantAi.reject}
                  className="flex items-center gap-1"
                >
                  <X className="w-4 h-4" />
                  Reject
                </Button>
                <Button
                  type="button"
                  onClick={handleAiAccept}
                  className="flex items-center gap-1 bg-green-600 hover:bg-green-700"
                >
                  <Check className="w-4 h-4" />
                  Accept
                </Button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Remarks */}
              {scriptAssistantAi.result[OUT.remarks] && (
                <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg">
                  <div className="text-sm font-medium text-purple-700 mb-1">AI Notes</div>
                  <div className="text-sm text-purple-800">{scriptAssistantAi.result[OUT.remarks]}</div>
                </div>
              )}

              {/* Name, File - Row */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Script Name</label>
                  <div className="mt-1 p-3 bg-gray-50 rounded-md font-mono text-sm">
                    {scriptAssistantAi.result[OUT.name]}
                    {isEditing && (
                      <span className="ml-2 text-xs text-amber-600">(name cannot be changed when editing)</span>
                    )}
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">File Name</label>
                  <div className="mt-1 p-3 bg-gray-50 rounded-md font-mono text-sm">{scriptAssistantAi.result[OUT.script_file]}</div>
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Description</label>
                <div className="mt-1 p-4 bg-gray-50 rounded-md border border-gray-200 prose prose-sm max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{scriptAssistantAi.result[OUT.description]}</ReactMarkdown>
                </div>
              </div>

              {/* Script Content */}
              <div>
                <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Script Content</label>
                <pre className="mt-1 p-4 bg-gray-900 text-gray-100 rounded-md overflow-x-auto text-sm font-mono max-h-64 overflow-y-auto">
                  {scriptAssistantAi.result[OUT.script]}
                </pre>
              </div>

              {/* Parameters Schema */}
              {scriptAssistantAi.result[OUT.parameters_schema] && (
                <div>
                  <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Parameters Schema</label>
                  <pre className="mt-1 p-4 bg-blue-50 border border-blue-200 rounded-md overflow-x-auto text-sm font-mono text-blue-800">
                    {JSON.stringify(scriptAssistantAi.result[OUT.parameters_schema], null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
