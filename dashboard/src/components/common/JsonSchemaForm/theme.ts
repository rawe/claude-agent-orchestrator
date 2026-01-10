import type { ThemeProps } from '@rjsf/core';
import type { TemplatesType, WidgetProps, RJSFSchema, FormContextType } from '@rjsf/utils';

// Templates
import { FieldTemplate } from './templates/FieldTemplate';
import { ObjectFieldTemplate } from './templates/ObjectFieldTemplate';
import { ArrayFieldTemplate } from './templates/ArrayFieldTemplate';
import { ArrayFieldItemTemplate } from './templates/ArrayFieldItemTemplate';
import { ErrorListTemplate } from './templates/ErrorListTemplate';

// Widgets
import { TextWidget } from './widgets/TextWidget';
import { TextareaWidget } from './widgets/TextareaWidget';
import { SelectWidget } from './widgets/SelectWidget';
import { CheckboxWidget } from './widgets/CheckboxWidget';
import { NumberWidget } from './widgets/NumberWidget';

// Cast widgets to the correct type for RJSF
type WidgetComponent = React.ComponentType<WidgetProps<unknown, RJSFSchema, FormContextType>>;

const templates: Partial<TemplatesType> = {
  FieldTemplate,
  ObjectFieldTemplate,
  ArrayFieldTemplate,
  ArrayFieldItemTemplate,
  ErrorListTemplate,
};

const widgets = {
  TextWidget: TextWidget as WidgetComponent,
  TextareaWidget: TextareaWidget as WidgetComponent,
  SelectWidget: SelectWidget as WidgetComponent,
  CheckboxWidget: CheckboxWidget as WidgetComponent,
  NumberWidget: NumberWidget as WidgetComponent,
  // Map number/integer types to NumberWidget
  UpDownWidget: NumberWidget as WidgetComponent,
  RangeWidget: NumberWidget as WidgetComponent,
};

export const tailwindTheme: ThemeProps = {
  templates,
  widgets,
};
