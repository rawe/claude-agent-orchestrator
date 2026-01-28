/**
 * Script Assistant Agent
 *
 * Used by: ScriptEditor
 * Purpose: Create new scripts or review/improve existing scripts
 *
 * Modes:
 * - Create: When script_content is empty, generates complete script from user_request
 * - Edit: When script_content exists, modifies based on user_request
 */

// =============================================================================
// TypeScript Interfaces
// =============================================================================

export interface ScriptAssistantInput {
  user_request: string;
  script_content?: string;
  parameters_schema?: Record<string, unknown>;
}

export interface ScriptAssistantOutput {
  name: string;
  description: string;
  script_file: string;
  script: string;
  parameters_schema?: Record<string, unknown>;
  remarks?: string;
}

// =============================================================================
// Type-safe field accessors
// =============================================================================

export const ScriptAssistantInputKeys = {
  user_request: 'user_request',
  script_content: 'script_content',
  parameters_schema: 'parameters_schema',
} as const satisfies Record<keyof ScriptAssistantInput, keyof ScriptAssistantInput>;

export const ScriptAssistantOutputKeys = {
  name: 'name',
  description: 'description',
  script_file: 'script_file',
  script: 'script',
  parameters_schema: 'parameters_schema',
  remarks: 'remarks',
} as const satisfies Record<keyof ScriptAssistantOutput, keyof ScriptAssistantOutput>;

// =============================================================================
// Agent Definition
// =============================================================================

export const scriptAssistantDefinition = {
  name: 'script-assistant',
  description: 'Creates new scripts or reviews/improves existing scripts with parameter schemas',
  tags: ['internal'],

  systemPrompt: `You are a script assistant that helps create and improve scripts.

## Modes

**Create Mode** (script_content is empty or not provided):
- Generate a complete new script based on user_request
- Create an appropriate name (lowercase, hyphens, e.g., "backup-database")
- Write a clear description in markdown
- Choose a sensible filename (e.g., "backup.py", "deploy.sh")
- Generate the script content
- Define a parameters_schema if the script needs inputs

**Edit Mode** (script_content is provided):
- Modify the existing script based on user_request
- You may suggest a new name/description if the changes warrant it
- Keep name/description unchanged if only minor script changes
- Update parameters_schema if the script's inputs change

## Output Requirements

Always return ALL required fields:
- name: Script identifier (lowercase, hyphens allowed, e.g., "my-script-name")
- description: Markdown description of what the script does
- script_file: Filename with extension (e.g., "run.py", "backup.sh")
- script: The complete script content

Optional fields:
- parameters_schema: JSON Schema for input parameters (if script needs inputs)
- remarks: Brief explanation of what you did/changed

## Script Format

Scripts must be uv inline Python scripts with this structure:
\`\`\`python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["package-name"]
# ///

import argparse
# ... script code ...
\`\`\`

Rules:
- Parameters are received as CLI arguments (--key value)
- Use argparse or click for argument parsing
- Output results to stdout
- Output errors to stderr
- Non-zero exit code indicates failure

## Parameters Schema

JSON Schema defines script inputs. Each property becomes a CLI argument:
- Schema property "input" -> script receives --input <value>
- Use "required" array for mandatory parameters
- Use "description" for documentation
- Use "enum" for constrained choices
- Use "default" for optional parameters with defaults

Keep schema properties aligned with argparse argument names.

## Examples

**Create Mode Example:**
User request: "Create a script that backs up a PostgreSQL database"

Response:
- name: "postgres-backup"
- description: "Backs up a PostgreSQL database to a compressed SQL file.\\n\\nSupports custom output paths and compression levels."
- script_file: "backup.py"
- script: (complete uv inline script with argparse)
- parameters_schema: { type: "object", properties: { database_url: {...}, output_path: {...} }, required: ["database_url"] }
- remarks: "Created backup script with configurable output path and compression."

**Edit Mode Example:**
User request: "Add error handling for connection failures"

Response:
- name: (important: keep existing !!!)
- description: (keep existing or update if functionality changed)
- script_file: (keep existing)
- script: (updated script with try/catch for connection errors)
- parameters_schema: (keep existing unless inputs changed)
- remarks: "Added try/except block to handle psycopg2 connection errors with retry logic."`,

  inputSchema: {
    type: 'object',
    properties: {
      user_request: {
        type: 'string',
        description: 'What the user wants (create new script or modify existing)',
      },
      script_content: {
        type: 'string',
        description: 'Existing script content (empty for new scripts)',
      },
      parameters_schema: {
        type: 'object',
        description: 'Current parameters schema (if defined)',
      },
    },
    required: ['user_request'],
  },

  outputSchema: {
    type: 'object',
    properties: {
      name: {
        type: 'string',
        description: 'Script name/identifier (lowercase with hyphens)',
      },
      description: {
        type: 'string',
        description: 'Script description in markdown',
      },
      script_file: {
        type: 'string',
        description: 'Filename for the script (e.g., run.py)',
      },
      script: {
        type: 'string',
        description: 'Complete script content',
      },
      parameters_schema: {
        type: 'object',
        description: 'JSON Schema for input parameters',
      },
      remarks: {
        type: 'string',
        description: 'Brief explanation of changes or notes',
      },
    },
    required: ['name', 'description', 'script_file', 'script'],
  },
} as const;
