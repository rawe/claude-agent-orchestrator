import type { ArrayFieldItemTemplateProps } from '@rjsf/utils';
import { Trash2, ChevronUp, ChevronDown } from 'lucide-react';

export function ArrayFieldItemTemplate(props: ArrayFieldItemTemplateProps) {
  const {
    children,
    buttonsProps,
    disabled,
    readonly,
  } = props;

  const {
    hasMoveUp,
    hasMoveDown,
    hasRemove,
    onMoveUpItem,
    onMoveDownItem,
    onRemoveItem,
  } = buttonsProps;

  const isDisabled = disabled || readonly;

  return (
    <div className="flex items-start gap-2">
      <div className="flex-1 min-w-0">{children}</div>
      <div className="flex items-center gap-1 flex-shrink-0 pt-1">
        {hasMoveUp && (
          <button
            type="button"
            onClick={onMoveUpItem}
            disabled={isDisabled}
            className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Move up"
          >
            <ChevronUp className="w-4 h-4" />
          </button>
        )}
        {hasMoveDown && (
          <button
            type="button"
            onClick={onMoveDownItem}
            disabled={isDisabled}
            className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Move down"
          >
            <ChevronDown className="w-4 h-4" />
          </button>
        )}
        {hasRemove && (
          <button
            type="button"
            onClick={onRemoveItem}
            disabled={isDisabled}
            className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Remove"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}
