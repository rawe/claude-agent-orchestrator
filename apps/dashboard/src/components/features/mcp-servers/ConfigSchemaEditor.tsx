import { useState } from 'react';
import { Plus, Trash2, Eye, EyeOff } from 'lucide-react';
import { Button } from '@/components/common';
import type { MCPServerConfigSchema, ConfigSchemaField } from '@/types/mcpServer';

interface ConfigSchemaEditorProps {
  value: MCPServerConfigSchema | undefined;
  onChange: (value: MCPServerConfigSchema | undefined) => void;
}

const FIELD_TYPES = ['string', 'integer', 'boolean'] as const;

interface FieldRowProps {
  fieldName: string;
  field: ConfigSchemaField;
  onUpdate: (name: string, field: ConfigSchemaField) => void;
  onDelete: (name: string) => void;
  onRename: (oldName: string, newName: string) => void;
}

function FieldRow({ fieldName, field, onUpdate, onDelete, onRename }: FieldRowProps) {
  const [localName, setLocalName] = useState(fieldName);

  const handleNameBlur = () => {
    if (localName !== fieldName && localName.trim()) {
      onRename(fieldName, localName.trim());
    }
  };

  return (
    <div className="grid grid-cols-12 gap-2 items-start p-3 bg-gray-50 rounded-lg">
      {/* Field Name */}
      <div className="col-span-3">
        <label className="text-xs text-gray-500 mb-1 block">Name</label>
        <input
          type="text"
          value={localName}
          onChange={(e) => setLocalName(e.target.value)}
          onBlur={handleNameBlur}
          className="input text-sm"
          placeholder="field_name"
        />
      </div>

      {/* Type */}
      <div className="col-span-2">
        <label className="text-xs text-gray-500 mb-1 block">Type</label>
        <select
          value={field.type}
          onChange={(e) => onUpdate(fieldName, { ...field, type: e.target.value as ConfigSchemaField['type'] })}
          className="input text-sm"
        >
          {FIELD_TYPES.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>

      {/* Description */}
      <div className="col-span-3">
        <label className="text-xs text-gray-500 mb-1 block">Description</label>
        <input
          type="text"
          value={field.description || ''}
          onChange={(e) => onUpdate(fieldName, { ...field, description: e.target.value || undefined })}
          className="input text-sm"
          placeholder="Optional description"
        />
      </div>

      {/* Default Value */}
      <div className="col-span-2">
        <label className="text-xs text-gray-500 mb-1 block">Default</label>
        <input
          type={field.type === 'boolean' ? 'text' : field.type === 'integer' ? 'number' : 'text'}
          value={field.default !== undefined ? String(field.default) : ''}
          onChange={(e) => {
            const val = e.target.value;
            let parsed: unknown = undefined;
            if (val) {
              if (field.type === 'integer') {
                parsed = parseInt(val, 10);
              } else if (field.type === 'boolean') {
                parsed = val.toLowerCase() === 'true';
              } else {
                parsed = val;
              }
            }
            onUpdate(fieldName, { ...field, default: parsed });
          }}
          className="input text-sm"
          placeholder={field.type === 'boolean' ? 'true/false' : 'Optional'}
        />
      </div>

      {/* Flags & Actions */}
      <div className="col-span-2 flex items-end gap-1">
        <button
          type="button"
          onClick={() => onUpdate(fieldName, { ...field, required: !field.required })}
          className={`p-2 rounded text-xs font-medium ${
            field.required
              ? 'bg-red-100 text-red-700 hover:bg-red-200'
              : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
          }`}
          title={field.required ? 'Required' : 'Optional'}
        >
          Req
        </button>
        <button
          type="button"
          onClick={() => onUpdate(fieldName, { ...field, sensitive: !field.sensitive })}
          className={`p-2 rounded ${
            field.sensitive
              ? 'bg-amber-100 text-amber-700 hover:bg-amber-200'
              : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
          }`}
          title={field.sensitive ? 'Sensitive (masked)' : 'Not sensitive'}
        >
          {field.sensitive ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
        <button
          type="button"
          onClick={() => onDelete(fieldName)}
          className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
          title="Delete field"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

export function ConfigSchemaEditor({ value, onChange }: ConfigSchemaEditorProps) {
  const schema = value || {};
  const fields = Object.entries(schema);

  const handleAddField = () => {
    const baseName = 'new_field';
    let name = baseName;
    let counter = 1;
    while (schema[name]) {
      name = `${baseName}_${counter}`;
      counter++;
    }

    const newField: ConfigSchemaField = {
      type: 'string',
      required: false,
      sensitive: false,
    };

    onChange({ ...schema, [name]: newField });
  };

  const handleUpdateField = (name: string, field: ConfigSchemaField) => {
    onChange({ ...schema, [name]: field });
  };

  const handleDeleteField = (name: string) => {
    const newSchema = { ...schema };
    delete newSchema[name];
    onChange(Object.keys(newSchema).length > 0 ? newSchema : undefined);
  };

  const handleRenameField = (oldName: string, newName: string) => {
    if (oldName === newName || schema[newName]) return;

    const newSchema: MCPServerConfigSchema = {};
    for (const [key, val] of Object.entries(schema)) {
      if (key === oldName) {
        newSchema[newName] = val;
      } else {
        newSchema[key] = val;
      }
    }
    onChange(newSchema);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <label className="text-sm font-medium text-gray-700">Config Schema</label>
          <p className="text-xs text-gray-500">
            Define configuration fields that agents must provide when using this server
          </p>
        </div>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={handleAddField}
          icon={<Plus className="w-4 h-4" />}
        >
          Add Field
        </Button>
      </div>

      {fields.length === 0 ? (
        <div className="text-center py-8 text-gray-500 text-sm bg-gray-50 rounded-lg border-2 border-dashed border-gray-200">
          No config fields defined. Click "Add Field" to define configuration parameters.
        </div>
      ) : (
        <div className="space-y-2">
          {fields.map(([name, field]) => (
            <FieldRow
              key={name}
              fieldName={name}
              field={field}
              onUpdate={handleUpdateField}
              onDelete={handleDeleteField}
              onRename={handleRenameField}
            />
          ))}
        </div>
      )}
    </div>
  );
}
