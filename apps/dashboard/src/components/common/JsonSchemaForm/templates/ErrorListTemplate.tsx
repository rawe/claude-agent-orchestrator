import type { ErrorListProps } from '@rjsf/utils';
import { AlertCircle } from 'lucide-react';

export function ErrorListTemplate(props: ErrorListProps) {
  const { errors } = props;

  if (!errors || errors.length === 0) {
    return null;
  }

  return (
    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
      <div className="flex items-center gap-2 mb-2">
        <AlertCircle className="w-4 h-4 text-red-600" />
        <h4 className="text-sm font-medium text-red-800">
          Please fix the following errors:
        </h4>
      </div>
      <ul className="list-disc list-inside space-y-1">
        {errors.map((error, index) => (
          <li key={index} className="text-sm text-red-700">
            {error.stack}
          </li>
        ))}
      </ul>
    </div>
  );
}
