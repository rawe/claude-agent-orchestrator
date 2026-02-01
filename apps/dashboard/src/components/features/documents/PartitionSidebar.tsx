import { useState } from 'react';
import { Globe, Folder, Plus, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button, ConfirmModal } from '@/components/common';
import type { Partition } from '@/types';
import { GLOBAL_PARTITION_NAME } from '@/types';

interface PartitionSidebarProps {
  partitions: Partition[];
  selectedPartition: string;
  onSelectPartition: (name: string) => void;
  onCreatePartition: () => void;
  onDeletePartition: (name: string) => Promise<void>;
  documentCounts: Record<string, number>;
  loading?: boolean;
}

export function PartitionSidebar({
  partitions,
  selectedPartition,
  onSelectPartition,
  onCreatePartition,
  onDeletePartition,
  documentCounts,
  loading = false,
}: PartitionSidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; partitionName: string | null }>({
    isOpen: false,
    partitionName: null,
  });
  const [deleteLoading, setDeleteLoading] = useState(false);

  const handleDelete = async () => {
    if (!deleteConfirm.partitionName) return;
    setDeleteLoading(true);
    try {
      await onDeletePartition(deleteConfirm.partitionName);
      // If the deleted partition was selected, switch to global
      if (selectedPartition === deleteConfirm.partitionName) {
        onSelectPartition(GLOBAL_PARTITION_NAME);
      }
    } finally {
      setDeleteLoading(false);
      setDeleteConfirm({ isOpen: false, partitionName: null });
    }
  };

  const globalDocCount = documentCounts[GLOBAL_PARTITION_NAME] ?? 0;

  if (collapsed) {
    return (
      <div className="w-10 flex-shrink-0 border-r border-gray-200 bg-gray-50 flex flex-col">
        <button
          onClick={() => setCollapsed(false)}
          className="p-2 hover:bg-gray-100 text-gray-500 hover:text-gray-700"
          title="Expand partitions"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
    );
  }

  return (
    <>
      <div className="w-52 flex-shrink-0 border-r border-gray-200 bg-gray-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Partitions</span>
          <button
            onClick={() => setCollapsed(true)}
            className="p-1 hover:bg-gray-200 rounded text-gray-500 hover:text-gray-700"
            title="Collapse"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
        </div>

        {/* Partition List */}
        <div className="flex-1 overflow-y-auto py-2">
          {/* Global Partition */}
          <button
            onClick={() => onSelectPartition(GLOBAL_PARTITION_NAME)}
            className={`w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors ${
              selectedPartition === GLOBAL_PARTITION_NAME
                ? 'bg-primary-50 text-primary-700 font-medium'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            <Globe className="w-4 h-4 flex-shrink-0" />
            <span className="flex-1 text-left truncate">Global</span>
            {selectedPartition === GLOBAL_PARTITION_NAME && (
              <span className="text-xs px-1.5 py-0.5 rounded-full bg-primary-100 text-primary-600">
                {globalDocCount}
              </span>
            )}
          </button>

          {/* Other Partitions */}
          {loading ? (
            <div className="px-3 py-4 text-sm text-gray-400 italic">Loading...</div>
          ) : (
            partitions.map((partition) => {
              const docCount = documentCounts[partition.name] ?? 0;
              const isSelected = selectedPartition === partition.name;
              return (
                <div
                  key={partition.name}
                  className={`group flex items-center gap-2 px-3 py-2 text-sm transition-colors ${
                    isSelected
                      ? 'bg-primary-50 text-primary-700 font-medium'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <button
                    onClick={() => onSelectPartition(partition.name)}
                    className="flex-1 flex items-center gap-2 min-w-0"
                  >
                    <Folder className="w-4 h-4 flex-shrink-0" />
                    <span className="flex-1 text-left truncate" title={partition.name}>
                      {partition.name}
                    </span>
                    {isSelected && (
                      <span className="text-xs px-1.5 py-0.5 rounded-full bg-primary-100 text-primary-600">
                        {docCount}
                      </span>
                    )}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleteConfirm({ isOpen: true, partitionName: partition.name });
                    }}
                    className="p-1 opacity-0 group-hover:opacity-100 hover:bg-red-100 hover:text-red-600 rounded transition-opacity"
                    title="Delete partition"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Create Button */}
        <div className="p-2 border-t border-gray-200">
          <Button
            onClick={onCreatePartition}
            variant="secondary"
            size="sm"
            className="w-full justify-center"
            icon={<Plus className="w-4 h-4" />}
          >
            New
          </Button>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={deleteConfirm.isOpen}
        onClose={() => setDeleteConfirm({ isOpen: false, partitionName: null })}
        onConfirm={handleDelete}
        title="Delete Partition"
        message={`Delete partition "${deleteConfirm.partitionName}"? This will permanently delete all documents in this partition. This action cannot be undone.`}
        confirmText="Delete"
        variant="danger"
        loading={deleteLoading}
      />
    </>
  );
}
