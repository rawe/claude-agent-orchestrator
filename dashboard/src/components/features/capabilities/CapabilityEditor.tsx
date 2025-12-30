import { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { Modal, Button, Spinner } from '@/components/common';
import { MCPJsonEditor } from '../agents/MCPJsonEditor';
import { Capability, CapabilityCreate } from '@/types/capability';
import { MCPServerConfig } from '@/types';
import { TEMPLATE_NAMES, addTemplate } from '@/utils/mcpTemplates';
import { Eye, Code } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface CapabilityEditorProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: CapabilityCreate) => Promise<void>;
  capability?: Capability | null;
  checkNameAvailable: (name: string) => Promise<boolean>;
}

interface FormData {
  name: string;
  description: string;
  text: string;
  mcp_servers: Record<string, MCPServerConfig> | null;
}

export function CapabilityEditor({
  isOpen,
  onClose,
  onSave,
  capability,
  checkNameAvailable,
}: CapabilityEditorProps) {
  const [textTab, setTextTab] = useState<'edit' | 'preview'>('edit');
  const [saving, setSaving] = useState(false);
  const [nameAvailable, setNameAvailable] = useState<boolean | null>(null);
  const [checkingName, setCheckingName] = useState(false);

  const isEditing = !!capability;

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
      text: '',
      mcp_servers: null,
    },
  });

  const watchedName = watch('name');
  const watchedText = watch('text');
  const watchedMcpServers = watch('mcp_servers');

  // Load capability data when editing
  useEffect(() => {
    if (capability) {
      reset({
        name: capability.name,
        description: capability.description,
        text: capability.text || '',
        mcp_servers: capability.mcp_servers,
      });
    } else {
      reset({
        name: '',
        description: '',
        text: '',
        mcp_servers: null,
      });
    }
    setNameAvailable(null);
  }, [capability, reset, isOpen]);

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

  const onSubmit = async (data: FormData) => {
    setSaving(true);
    try {
      const createData: CapabilityCreate = {
        name: data.name,
        description: data.description,
        text: data.text || undefined,
        mcp_servers: data.mcp_servers ?? {},  // null -> {} to clear MCP servers
      };
      await onSave(createData);
      onClose();
    } catch (err) {
      console.error('Failed to save capability:', err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? `Edit Capability: ${capability.name}` : 'New Capability'}
      size="xl"
    >
      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto">
          {/* Basic Information */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-gray-900">Basic Information</h3>

            {/* Name */}
            <div>
              <label className="label">Capability Name *</label>
              <div className="relative">
                <input
                  {...register('name', {
                    required: 'Capability name is required',
                    pattern: {
                      value: /^[a-zA-Z0-9][a-zA-Z0-9_-]*$/,
                      message: 'Must start with letter/number, then letters, numbers, hyphens, or underscores',
                    },
                    minLength: { value: 2, message: 'Minimum 2 characters' },
                    maxLength: { value: 60, message: 'Maximum 60 characters' },
                  })}
                  disabled={isEditing}
                  placeholder="my-capability-name"
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
                placeholder="Describe what this capability provides..."
                rows={2}
                className={`input resize-none ${errors.description ? 'border-red-500' : ''}`}
              />
              {errors.description && (
                <p className="mt-1 text-xs text-red-500">{errors.description.message}</p>
              )}
            </div>
          </div>

          {/* Text Content (for system prompt) */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="label mb-0">Text Content</label>
              <div className="flex rounded-md border border-gray-300 overflow-hidden">
                <button
                  type="button"
                  onClick={() => setTextTab('edit')}
                  className={`flex items-center gap-1 px-3 py-1 text-xs ${
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
                  className={`flex items-center gap-1 px-3 py-1 text-xs border-l ${
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
            <p className="text-xs text-gray-500 mb-2">
              Markdown content that will be appended to the agent's system prompt when this capability is used.
            </p>

            {textTab === 'edit' ? (
              <textarea
                {...register('text')}
                placeholder="## Capability Documentation&#10;&#10;Provide instructions, schemas, or documentation that agents using this capability need..."
                rows={10}
                className="input font-mono text-sm resize-none"
              />
            ) : (
              <div className="border border-gray-300 rounded-md p-4 min-h-[240px] max-h-[240px] overflow-auto bg-white">
                {watchedText ? (
                  <div className="markdown-content prose prose-sm max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{watchedText}</ReactMarkdown>
                  </div>
                ) : (
                  <p className="text-gray-400 text-sm italic">
                    Enter text content to see the preview
                  </p>
                )}
              </div>
            )}
          </div>

          {/* MCP Servers */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-gray-900">MCP Servers</h3>
            <p className="text-xs text-gray-500 -mt-2">
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
            {isEditing ? 'Save Changes' : 'Create Capability'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
