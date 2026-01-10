import type { WidgetProps } from '@rjsf/utils';

export function TextareaWidget(props: WidgetProps) {
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
  } = props;

  const rows = (options?.rows as number) || 4;

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value === '' ? undefined : e.target.value);
  };

  const handleBlur = (e: React.FocusEvent<HTMLTextAreaElement>) => {
    onBlur(id, e.target.value);
  };

  const handleFocus = (e: React.FocusEvent<HTMLTextAreaElement>) => {
    onFocus(id, e.target.value);
  };

  return (
    <textarea
      id={id}
      className="input resize-y min-h-[80px]"
      value={value ?? ''}
      required={required}
      disabled={disabled || readonly}
      autoFocus={autofocus}
      placeholder={placeholder}
      rows={rows}
      onChange={handleChange}
      onBlur={handleBlur}
      onFocus={handleFocus}
    />
  );
}
