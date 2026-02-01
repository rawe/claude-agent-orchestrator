import { useState } from 'react';
import { Modal, Button } from '@/components/common';

interface CreatePartitionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (name: string, description?: string) => Promise<void>;
}

// Validate partition name: must start with letter or underscore, then letters/numbers/underscores
const isValidPartitionName = (name: string): boolean => {
  return /^[a-z_][a-z0-9_]*$/.test(name);
};

export function CreatePartitionModal({ isOpen, onClose, onCreate }: CreatePartitionModalProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const trimmedName = name.trim().toLowerCase();

    if (!trimmedName) {
      setError('Name is required');
      return;
    }

    if (!isValidPartitionName(trimmedName)) {
      setError('Must start with letter or underscore, then letters, numbers, or underscores');
      return;
    }

    if (trimmedName === '_global') {
      setError('Cannot use reserved name "_global"');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await onCreate(trimmedName, description.trim() || undefined);
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create partition');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setName('');
    setDescription('');
    setError(null);
    onClose();
  };

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.toLowerCase();
    setName(value);
    if (error) setError(null);
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Create Partition" size="sm">
      <form onSubmit={handleSubmit}>
        <div className="p-6 space-y-4">
          <div>
            <label htmlFor="partition-name" className="block text-sm font-medium text-gray-700 mb-1">
              Name <span className="text-red-500">*</span>
            </label>
            <input
              id="partition-name"
              type="text"
              value={name}
              onChange={handleNameChange}
              placeholder="my_partition"
              className={`w-full px-3 py-2 text-sm border rounded-md focus:outline-none focus:ring-1 ${
                error
                  ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
                  : 'border-gray-300 focus:ring-primary-500 focus:border-primary-500'
              }`}
              autoFocus
              disabled={loading}
            />
            <p className="mt-1 text-xs text-gray-500">
              Starts with letter or underscore; letters, numbers, underscores allowed
            </p>
            {error && (
              <p className="mt-1 text-xs text-red-600">{error}</p>
            )}
          </div>

          <div>
            <label htmlFor="partition-description" className="block text-sm font-medium text-gray-700 mb-1">
              Description <span className="text-gray-400">(optional)</span>
            </label>
            <textarea
              id="partition-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Purpose of this partition..."
              rows={2}
              maxLength={200}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500 resize-none"
              disabled={loading}
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 px-6 py-4 bg-gray-50 border-t">
          <Button variant="secondary" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <Button type="submit" loading={loading} disabled={!name.trim()}>
            Create
          </Button>
        </div>
      </form>
    </Modal>
  );
}
