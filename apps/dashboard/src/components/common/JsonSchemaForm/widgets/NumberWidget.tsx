import type { WidgetProps } from '@rjsf/utils';

export function NumberWidget(props: WidgetProps) {
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
    schema,
  } = props;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    if (val === '') {
      onChange(undefined);
    } else {
      const num = schema.type === 'integer' ? parseInt(val, 10) : parseFloat(val);
      onChange(isNaN(num) ? undefined : num);
    }
  };

  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    onBlur(id, e.target.value);
  };

  const handleFocus = (e: React.FocusEvent<HTMLInputElement>) => {
    onFocus(id, e.target.value);
  };

  return (
    <input
      id={id}
      type="number"
      className="input"
      value={value ?? ''}
      required={required}
      disabled={disabled || readonly}
      autoFocus={autofocus}
      placeholder={placeholder}
      step={schema.type === 'integer' ? 1 : 'any'}
      min={schema.minimum as number | undefined}
      max={schema.maximum as number | undefined}
      onChange={handleChange}
      onBlur={handleBlur}
      onFocus={handleFocus}
    />
  );
}
