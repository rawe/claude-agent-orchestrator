import type { ObjectFieldTemplateProps } from '@rjsf/utils';

export function ObjectFieldTemplate(props: ObjectFieldTemplateProps) {
  const { title, description, properties, fieldPathId } = props;

  // Root object - no wrapper, just render properties
  const isRoot = fieldPathId.$id === 'root';

  if (isRoot) {
    return (
      <div className="space-y-4">
        {properties.map((prop) => (
          <div key={prop.name}>{prop.content}</div>
        ))}
      </div>
    );
  }

  // Nested object - show with border and title
  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-gray-50/50">
      {title && (
        <h4 className="text-sm font-medium text-gray-700 mb-1">{title}</h4>
      )}
      {description && (
        <p className="text-xs text-gray-500 mb-3">{description}</p>
      )}
      <div className="space-y-4">
        {properties.map((prop) => (
          <div key={prop.name}>{prop.content}</div>
        ))}
      </div>
    </div>
  );
}
