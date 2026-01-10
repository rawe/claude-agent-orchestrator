import type { ArrayFieldTemplateProps } from '@rjsf/utils';
import { Plus } from 'lucide-react';

export function ArrayFieldTemplate(props: ArrayFieldTemplateProps) {
  const {
    title,
    items,
    canAdd,
    onAddClick,
    required,
  } = props;

  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-white">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {title && (
            <h4 className="text-sm font-medium text-gray-700">
              {title}
              {required && <span className="text-red-500 ml-1">*</span>}
            </h4>
          )}
          <span className="text-xs text-gray-400">
            {items.length} item{items.length !== 1 ? 's' : ''}
          </span>
        </div>
        {canAdd && (
          <button
            type="button"
            onClick={onAddClick}
            className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-primary-600 hover:text-primary-700 hover:bg-primary-50 rounded transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Add
          </button>
        )}
      </div>

      {items.length === 0 ? (
        <div className="text-center py-4 text-sm text-gray-400">
          No items. Click "Add" to create one.
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((item, index) => (
            <div key={index} className="border border-gray-100 rounded-lg bg-gray-50 p-3">
              {item}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
