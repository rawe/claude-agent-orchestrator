/**
 * Script Assistant Agent
 *
 * Used by: ScriptEditor
 * Purpose: Review and improve scripts, suggest parameter schema changes
 */

// =============================================================================
// TypeScript Interfaces
// =============================================================================

export interface ScriptAssistantInput {
  script_content: string;
  user_request?: string;
  parameters_schema?: Record<string, unknown>;
}

export interface ScriptAssistantOutput {
  script: string;
  parameters_schema?: Record<string, unknown>;
  remarks?: string;
}

// =============================================================================
// Type-safe field accessors
// =============================================================================

export const ScriptAssistantInputKeys = {
  script_content: 'script_content',
  user_request: 'user_request',
  parameters_schema: 'parameters_schema',
} as const satisfies Record<keyof ScriptAssistantInput, keyof ScriptAssistantInput>;

export const ScriptAssistantOutputKeys = {
  script: 'script',
  parameters_schema: 'parameters_schema',
  remarks: 'remarks',
} as const satisfies Record<keyof ScriptAssistantOutput, keyof ScriptAssistantOutput>;

// =============================================================================
// Agent Definition
// =============================================================================

export const scriptAssistantDefinition = {
  name: 'script-assistant',
  description: 'Reviews and improves scripts, suggests parameter schema changes',
  tags: ['internal'],

  systemPrompt: `You are a script assistant. Your task:

1. If user_request is provided, follow it precisely
2. Otherwise, review the script for syntax errors, best practices, and improvements

Always return the complete updated script. Keep remarks brief and actionable.

## Script Format

Scripts must be uv inline scripts with this structure:
\`\`\`python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["package-name"]
# ///
\`\`\`
- Parameters received as CLI arguments (--key value)
- Output to stdout, errors to stderr
- Non-zero exit = failure

## Parameters Schema

JSON Schema defines script inputs. Each property becomes a CLI argument:
- Schema property "input" → script receives --input <value>
- Use "required" array for mandatory parameters
- Use "description" for documentation
- Use "enum" for constrained choices
- Use "default" for optional parameters with defaults

If the script uses argparse/click, keep schema properties aligned with argument names.`,

  inputSchema: {
    type: 'object',
    properties: {
      script_content: {
        type: 'string',
        description: 'Current script content to review',
      },
      user_request: {
        type: 'string',
        description: 'User instruction',
      },
      parameters_schema: {
        type: 'object',
        description: 'Current parameters schema (if defined)',
      },
    },
    required: ['script_content'],
  },

  outputSchema: {
    type: 'object',
    properties: {
      script: {
        type: 'string',
        description: 'Updated script content',
      },
      parameters_schema: {
        type: 'object',
        description: 'Updated parameters schema (if changes suggested)',
      },
      remarks: {
        type: 'string',
        description: 'Explanation of changes',
      },
    },
    required: ['script'],
  },
} as const;
