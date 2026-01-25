# Form Validation Pattern

Standard pattern for form validation using react-hook-form with Zod schemas.

## Dependencies

```bash
npm install zod @hookform/resolvers
```

## Schema Definition

Define validation once in a Zod schema (single source of truth for types and validation):

```typescript
import { z } from 'zod';

const formSchema = z.object({
  name: z
    .string()
    .min(2, 'Minimum 2 characters')
    .max(60, 'Maximum 60 characters')
    .regex(/^[a-zA-Z0-9][a-zA-Z0-9_-]*$/, 'Invalid format'),
  description: z.string().min(1, 'Description is required'),
  // optional fields
  tags: z.array(z.string()).optional(),
  config: z.record(z.unknown()).nullable(),
});

// Infer TypeScript type from schema
type FormData = z.infer<typeof formSchema>;
```

## useForm Configuration

```typescript
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
  resolver: zodResolver(formSchema),
  mode: 'onBlur',           // Validate only when leaving field
  reValidateMode: 'onBlur', // After failed submit, still only validate on blur
  defaultValues: {
    name: '',
    description: '',
    tags: [],
    config: null,
  },
});
```

### Why These Settings Matter

| Setting | Value | Reason |
|---------|-------|--------|
| `resolver` | `zodResolver(formSchema)` | Validates against schema regardless of rendered inputs |
| `mode` | `'onBlur'` | Prevents validation on every keystroke (causes re-renders) |
| `reValidateMode` | `'onBlur'` | After failed submit, prevents focus loss from onChange re-validation |

## Register Calls

Keep register calls minimal - no duplicate validation rules:

```typescript
// Good - validation handled by Zod
<input {...register('name')} />
<input {...register('description')} />

// For fields with additional blur handlers (e.g., API checks)
<input {...register('name', { onBlur: handleNameBlur })} />
```

Do NOT duplicate validation in register:
```typescript
// Bad - redundant, Zod already handles this
<input {...register('name', {
  required: 'Required',  // Redundant
  minLength: 2,          // Redundant
})} />
```

## Tabbed Forms

When using tabs, **render all tabs but hide inactive ones**. This ensures:
1. All fields are registered with react-hook-form
2. Zod can validate all fields on submit
3. No focus loss from component unmounting

```tsx
// Good - all tabs rendered, inactive hidden
<div className={activeTab !== 'general' ? 'hidden' : ''}>
  <GeneralTab />
</div>
<div className={activeTab !== 'settings' ? 'hidden' : ''}>
  <SettingsTab />
</div>

// Bad - conditionally rendered tabs
{activeTab === 'general' && <GeneralTab />}
{activeTab === 'settings' && <SettingsTab />}
```

## Async Validation (API Checks)

For checks like "is name available", use a separate blur handler:

```typescript
const [nameAvailable, setNameAvailable] = useState<boolean | null>(null);
const [checkingName, setCheckingName] = useState(false);

const handleNameBlur = async (e: React.FocusEvent<HTMLInputElement>) => {
  const name = e.target.value;
  if (isEditing || !name || name.length < 2) {
    setNameAvailable(null);
    return;
  }

  setCheckingName(true);
  try {
    const available = await checkNameAvailable(name);
    setNameAvailable(available);
  } catch {
    setNameAvailable(null);
  } finally {
    setCheckingName(false);
  }
};

// In form
<input {...register('name', { onBlur: handleNameBlur })} />
```

Optionally, also check on submit (for users who type and immediately click Save):

```typescript
const onSubmit = async (data: FormData) => {
  // Check name if not yet validated
  if (!isEditing && nameAvailable === null && data.name.length >= 2) {
    setCheckingName(true);
    try {
      const available = await checkNameAvailable(data.name);
      setNameAvailable(available);
      if (!available) {
        setCheckingName(false);
        return;
      }
    } finally {
      setCheckingName(false);
    }
  }

  // Proceed with save...
};
```

## Error Display

```tsx
<input
  {...register('name')}
  className={errors.name ? 'border-red-500' : ''}
/>
{errors.name && (
  <p className="text-xs text-red-500">{errors.name.message}</p>
)}
```

## Reference Implementation

See `src/components/features/scripts/ScriptEditor.tsx` for a complete example.
