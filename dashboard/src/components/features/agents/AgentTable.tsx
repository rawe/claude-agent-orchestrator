import { useMemo, useState } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  SortingState,
} from '@tanstack/react-table';
import { Agent } from '@/types';
import { Badge, StatusBadge, EmptyState, SkeletonLine } from '@/components/common';
import { truncate } from '@/utils/formatters';
import { Settings, Search, Edit2, Trash2, ToggleLeft, ToggleRight, Tag, X } from 'lucide-react';

// Tag filter component
function TagFilter({
  allTags,
  selectedTags,
  onTagToggle,
  onClearAll,
}: {
  allTags: string[];
  selectedTags: Set<string>;
  onTagToggle: (tag: string) => void;
  onClearAll: () => void;
}) {
  if (allTags.length === 0) return null;

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-xs text-gray-500 font-medium">Filter by tag:</span>
      {allTags.map((tag) => {
        const isSelected = selectedTags.has(tag);
        return (
          <button
            key={tag}
            onClick={() => onTagToggle(tag)}
            className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full transition-colors ${
              isSelected
                ? 'bg-primary-100 text-primary-700 ring-1 ring-primary-300'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            <Tag className="w-2.5 h-2.5" />
            {tag}
          </button>
        );
      })}
      {selectedTags.size > 0 && (
        <button
          onClick={onClearAll}
          className="inline-flex items-center gap-1 px-2 py-1 text-xs text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors"
        >
          <X className="w-3 h-3" />
          Clear
        </button>
      )}
    </div>
  );
}

// Tags display component
function TagsDisplay({ tags }: { tags: string[] }) {
  if (!tags || tags.length === 0) {
    return <span className="text-gray-400 text-xs italic">No tags</span>;
  }

  const displayTags = tags.slice(0, 3);
  const hiddenTags = tags.slice(3);

  return (
    <div className="relative group">
      <div className="flex flex-wrap gap-1">
        {displayTags.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-700"
          >
            <Tag className="w-2.5 h-2.5" />
            {tag}
          </span>
        ))}
        {hiddenTags.length > 0 && (
          <span className="px-2 py-0.5 text-xs text-gray-500 group-hover:hidden">
            +{hiddenTags.length}
          </span>
        )}
      </div>
      {hiddenTags.length > 0 && (
        <div className="absolute left-0 top-full mt-1 z-10 hidden group-hover:block">
          <div className="bg-white rounded-lg border border-gray-200 shadow-lg px-3 py-2">
            <div className="flex flex-wrap gap-1 max-w-xs">
              {hiddenTags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-700"
                >
                  <Tag className="w-2.5 h-2.5" />
                  {tag}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface AgentTableProps {
  agents: Agent[];
  loading?: boolean;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onEditAgent: (agent: Agent) => void;
  onDeleteAgent: (name: string) => void;
  onToggleStatus: (name: string, currentStatus: 'active' | 'inactive') => void;
}

const columnHelper = createColumnHelper<Agent>();

export function AgentTable({
  agents,
  loading = false,
  searchQuery,
  onSearchChange,
  onEditAgent,
  onDeleteAgent,
  onToggleStatus,
}: AgentTableProps) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'name', desc: false },
  ]);
  const [selectedTags, setSelectedTags] = useState<Set<string>>(new Set());
  const [hideInactive, setHideInactive] = useState(false);

  // Extract all unique tags from agents
  const allTags = useMemo(() => {
    const tagSet = new Set<string>();
    agents.forEach((agent) => {
      (agent.tags || []).forEach((tag) => tagSet.add(tag));
    });
    return Array.from(tagSet).sort();
  }, [agents]);

  const handleTagToggle = (tag: string) => {
    setSelectedTags((prev) => {
      const next = new Set(prev);
      if (next.has(tag)) {
        next.delete(tag);
      } else {
        next.add(tag);
      }
      return next;
    });
  };

  const handleClearTags = () => {
    setSelectedTags(new Set());
  };

  const filteredData = useMemo(() => {
    let result = agents;

    // Filter out inactive agents if toggle is on
    if (hideInactive) {
      result = result.filter((agent) => agent.status === 'active');
    }

    // Filter by selected tags (AND logic - agent must have ALL selected tags)
    if (selectedTags.size > 0) {
      result = result.filter((agent) => {
        const agentTags = new Set(agent.tags || []);
        return Array.from(selectedTags).every((tag) => agentTags.has(tag));
      });
    }

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (agent) =>
          agent.name.toLowerCase().includes(query) ||
          agent.description.toLowerCase().includes(query)
      );
    }

    return result;
  }, [agents, searchQuery, selectedTags, hideInactive]);

  const columns = useMemo(
    () => [
      columnHelper.accessor('name', {
        header: 'Name',
        cell: (info) => (
          <button
            onClick={() => onEditAgent(info.row.original)}
            className="font-medium text-primary-600 hover:text-primary-700 hover:underline"
          >
            {info.getValue()}
          </button>
        ),
      }),
      columnHelper.accessor('description', {
        header: 'Description',
        cell: (info) => (
          <span className="text-gray-600" title={info.getValue()}>
            {truncate(info.getValue(), 60)}
          </span>
        ),
      }),
      columnHelper.display({
        id: 'capabilities',
        header: 'Capabilities',
        cell: (info) => {
          const agent = info.row.original;
          const mcpServerNames = agent.mcp_servers ? Object.keys(agent.mcp_servers) : [];
          const skills = agent.skills || [];
          const allCapabilities = [...mcpServerNames, ...skills];
          const display = allCapabilities.slice(0, 2);
          const remaining = allCapabilities.length - 2;

          return (
            <div className="flex flex-wrap gap-1">
              {display.map((cap) => (
                <Badge key={cap} size="sm" variant="default">
                  {cap}
                </Badge>
              ))}
              {remaining > 0 && (
                <Badge size="sm" variant="gray">
                  +{remaining}
                </Badge>
              )}
            </div>
          );
        },
      }),
      columnHelper.accessor('tags', {
        header: 'Tags',
        cell: (info) => <TagsDisplay tags={info.getValue()} />,
      }),
      columnHelper.accessor('status', {
        header: 'Status',
        cell: (info) => <StatusBadge status={info.getValue()} />,
      }),
      columnHelper.display({
        id: 'actions',
        cell: (info) => {
          const agent = info.row.original;
          return (
            <div className="flex items-center gap-1">
              <button
                onClick={() => onToggleStatus(agent.name, agent.status)}
                className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                title={agent.status === 'active' ? 'Deactivate' : 'Activate'}
              >
                {agent.status === 'active' ? (
                  <ToggleRight className="w-4 h-4 text-green-500" />
                ) : (
                  <ToggleLeft className="w-4 h-4" />
                )}
              </button>
              <button
                onClick={() => onEditAgent(agent)}
                className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                title="Edit"
              >
                <Edit2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => onDeleteAgent(agent.name)}
                className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                title="Delete"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          );
        },
        size: 120,
      }),
    ],
    [onEditAgent, onDeleteAgent, onToggleStatus]
  );

  const table = useReactTable({
    data: filteredData,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  if (loading) {
    return (
      <div className="p-4 space-y-3">
        <SkeletonLine width="w-full" />
        <SkeletonLine width="w-full" />
        <SkeletonLine width="w-3/4" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Search and Tag Filter */}
      <div className="p-4 border-b border-gray-200 space-y-3">
        <div className="flex items-center gap-4">
          <div className="relative max-w-md flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search agents..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
          <button
            onClick={() => setHideInactive(!hideInactive)}
            className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none"
          >
            <div
              className={`relative w-9 h-5 rounded-full transition-colors ${
                hideInactive ? 'bg-primary-500' : 'bg-gray-300'
              }`}
            >
              <div
                className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${
                  hideInactive ? 'translate-x-4' : 'translate-x-0.5'
                }`}
              />
            </div>
            <span>Hide inactive</span>
          </button>
        </div>
        <TagFilter
          allTags={allTags}
          selectedTags={selectedTags}
          onTagToggle={handleTagToggle}
          onClearAll={handleClearTags}
        />
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        {filteredData.length === 0 ? (
          <EmptyState
            icon={<Settings className="w-12 h-12" />}
            title="No agents found"
            description={
              searchQuery || selectedTags.size > 0
                ? 'Try adjusting your search or tag filters'
                : 'Create your first specialized agent to get started'
            }
          />
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 sticky top-0">
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {table.getRowModel().rows.map((row) => {
                const isInactive = row.original.status === 'inactive';
                return (
                  <tr
                    key={row.id}
                    className={`hover:bg-gray-50 ${isInactive ? 'opacity-50' : ''}`}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-3 whitespace-nowrap">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Count */}
      <div className="px-4 py-2 border-t border-gray-200 text-xs text-gray-500 bg-white">
        {filteredData.length} of {agents.length} agents
      </div>
    </div>
  );
}
