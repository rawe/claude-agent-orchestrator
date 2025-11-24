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
import { Settings, Search, Edit2, Trash2, ToggleLeft, ToggleRight } from 'lucide-react';

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

  const filteredData = useMemo(() => {
    if (!searchQuery) return agents;
    const query = searchQuery.toLowerCase();
    return agents.filter(
      (agent) =>
        agent.name.toLowerCase().includes(query) ||
        agent.description.toLowerCase().includes(query)
    );
  }, [agents, searchQuery]);

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
          const allCapabilities = [...agent.mcp_servers, ...agent.skills];
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
      {/* Search */}
      <div className="p-4 border-b border-gray-200">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search agents..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        {filteredData.length === 0 ? (
          <EmptyState
            icon={<Settings className="w-12 h-12" />}
            title="No agents found"
            description={
              searchQuery
                ? 'Try adjusting your search'
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
              {table.getRowModel().rows.map((row) => (
                <tr key={row.id} className="hover:bg-gray-50">
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-4 py-3 whitespace-nowrap">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
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
