import { useMemo } from 'react';
import { withTheme } from '@rjsf/core';
import type { FormProps, IChangeEvent } from '@rjsf/core';
import type { RJSFSchema, UiSchema } from '@rjsf/utils';
import validator from '@rjsf/validator-ajv8';
import { tailwindTheme } from './theme';
import { Send } from 'lucide-react';

// Create themed form component
const ThemedForm = withTheme(tailwindTheme);

export interface JsonSchemaFormProps {
  /** The JSON Schema for the form */
  schema: RJSFSchema;
  /** Optional UI Schema for customizing form appearance */
  uiSchema?: UiSchema;
  /** Initial form data */
  formData?: Record<string, unknown>;
  /** Callback when form is submitted with valid data */
  onSubmit: (data: Record<string, unknown>) => void;
  /** Whether the form is in a loading/submitting state */
  isLoading?: boolean;
  /** Whether the form is disabled */
  disabled?: boolean;
  /** Custom submit button text */
  submitText?: string;
  /** Show live validation as user types */
  liveValidate?: boolean;
}

export function JsonSchemaForm({
  schema,
  uiSchema,
  formData,
  onSubmit,
  isLoading = false,
  disabled = false,
  submitText = 'Submit',
  liveValidate = false,
}: JsonSchemaFormProps) {
  // Generate default uiSchema if not provided
  const effectiveUiSchema = useMemo(() => {
    if (uiSchema) return uiSchema;

    // Auto-generate uiSchema based on schema
    const generated: UiSchema = {
      'ui:submitButtonOptions': {
        norender: true, // We render our own submit button
      },
    };

    // If schema has properties, iterate and set up widgets
    if (schema.properties) {
      for (const [key, propSchema] of Object.entries(schema.properties)) {
        const prop = propSchema as RJSFSchema;

        // Use textarea for string fields with longer expected content
        if (prop.type === 'string' && !prop.enum) {
          // Check if field seems to want longer text
          const isLongText =
            key.toLowerCase().includes('description') ||
            key.toLowerCase().includes('content') ||
            key.toLowerCase().includes('body') ||
            key.toLowerCase().includes('text') ||
            key.toLowerCase().includes('prompt') ||
            key.toLowerCase().includes('message');

          if (isLongText) {
            generated[key] = { 'ui:widget': 'textarea' };
          }
        }
      }
    }

    return generated;
  }, [schema, uiSchema]);

  const handleSubmit = (data: IChangeEvent<Record<string, unknown>>) => {
    if (data.formData) {
      onSubmit(data.formData);
    }
  };

  // Type assertion for FormProps
  const formProps: FormProps<Record<string, unknown>, RJSFSchema> = {
    schema,
    uiSchema: effectiveUiSchema,
    formData,
    validator,
    onSubmit: handleSubmit,
    disabled: disabled || isLoading,
    liveValidate,
    showErrorList: 'top',
    noHtml5Validate: true,
  };

  return (
    <div className="json-schema-form">
      <ThemedForm {...formProps}>
        <div className="mt-4 flex justify-end">
          <button
            type="submit"
            disabled={disabled || isLoading}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
          >
            {isLoading ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Submitting...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                {submitText}
              </>
            )}
          </button>
        </div>
      </ThemedForm>
    </div>
  );
}

// Re-export types for convenience
export type { RJSFSchema, UiSchema };
