import type { WidgetProps } from '@rjsf/utils';

export function SelectWidget(props: WidgetProps) {
  const {
    id,
    value,
    required,
    disabled,
    readonly,
    autofocus,
    placeholder,
    onChange,
    onBlur,
    onFocus,
    options,
    multiple,
  } = props;

  const { enumOptions = [] } = options;

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    if (multiple) {
      const selectedOptions = Array.from(e.target.selectedOptions).map(o => o.value);
      onChange(selectedOptions);
    } else {
      onChange(e.target.value === '' ? undefined : e.target.value);
    }
  };

  const handleBlur = (e: React.FocusEvent<HTMLSelectElement>) => {
    onBlur(id, e.target.value);
  };

  const handleFocus = (e: React.FocusEvent<HTMLSelectElement>) => {
    onFocus(id, e.target.value);
  };

  return (
    <select
      id={id}
      className="input"
      value={value ?? ''}
      required={required}
      disabled={disabled || readonly}
      autoFocus={autofocus}
      multiple={multiple}
      onChange={handleChange}
      onBlur={handleBlur}
      onFocus={handleFocus}
    >
      {!required && !multiple && (
        <option value="">{placeholder || 'Select...'}</option>
      )}
      {enumOptions.map(({ value: optValue, label }: { value: string; label: string }) => (
        <option key={optValue} value={optValue}>
          {label}
        </option>
      ))}
    </select>
  );
}
