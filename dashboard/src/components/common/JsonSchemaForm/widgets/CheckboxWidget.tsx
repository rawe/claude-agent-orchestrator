import type { WidgetProps } from '@rjsf/utils';

export function CheckboxWidget(props: WidgetProps) {
  const {
    id,
    value,
    disabled,
    readonly,
    autofocus,
    onChange,
    onBlur,
    onFocus,
    label,
  } = props;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.checked);
  };

  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    onBlur(id, e.target.checked);
  };

  const handleFocus = (e: React.FocusEvent<HTMLInputElement>) => {
    onFocus(id, e.target.checked);
  };

  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <input
        id={id}
        type="checkbox"
        className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
        checked={value ?? false}
        disabled={disabled || readonly}
        autoFocus={autofocus}
        onChange={handleChange}
        onBlur={handleBlur}
        onFocus={handleFocus}
      />
      {label && (
        <span className="text-sm text-gray-700">{label}</span>
      )}
    </label>
  );
}
