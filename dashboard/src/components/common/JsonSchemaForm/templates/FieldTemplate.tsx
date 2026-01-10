import type { FieldTemplateProps } from '@rjsf/utils';

export function FieldTemplate(props: FieldTemplateProps) {
  const {
    id,
    label,
    required,
    description,
    errors,
    children,
    schema,
    hidden,
  } = props;

  if (hidden) {
    return <div className="hidden">{children}</div>;
  }

  // Don't render label for object types (they have their own title)
  const isObject = schema.type === 'object';
  const isArray = schema.type === 'array';
  const showLabel = !isObject && !isArray && label;

  return (
    <div className="mb-4">
      {showLabel && (
        <label htmlFor={id} className="label">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      {description && !isObject && (
        <p className="text-xs text-gray-500 mb-1">{description}</p>
      )}
      {children}
      {errors && (
        <div className="mt-1 text-xs text-red-600">{errors}</div>
      )}
    </div>
  );
}
