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
import { CapabilitySummary, CapabilityType } from '@/types/capability';
import { Badge, EmptyState, SkeletonLine } from '@/components/common';
import { truncate } from '@/utils/formatters';
import { Puzzle, Search, Edit2, Trash2, FileText, Server, FileCode } from 'lucide-react';

const TYPE_BADGE_CONFIG: Record<CapabilityType, { variant: 'default' | 'info' | 'success'; icon: React.ReactNode; label: string }> = {
  script: { variant: 'success', icon: <FileCode className="w-3 h-3 mr-1" />, label: 'Script' },
  mcp: { variant: 'info', icon: <Server className="w-3 h-3 mr-1" />, label: 'MCP' },
  text: { variant: 'default', icon: <FileText className="w-3 h-3 mr-1" />, label: 'Text' },
};

interface CapabilityTableProps {
  capabilities: CapabilitySummary[];
  loading?: boolean;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onEditCapability: (capability: CapabilitySummary) => void;
  onDeleteCapability: (name: string) => void;
}

const columnHelper = createColumnHelper<CapabilitySummary>();

export function CapabilityTable({
  capabilities,
  loading = false,
  searchQuery,
  onSearchChange,
  onEditCapability,
  onDeleteCapability,
}: CapabilityTableProps) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'name', desc: false },
  ]);

  const filteredData = useMemo(() => {
    if (!searchQuery) return capabilities;

    const query = searchQuery.toLowerCase();
    return capabilities.filter(
      (cap) =>
        cap.name.toLowerCase().includes(query) ||
        cap.description.toLowerCase().includes(query)
    );
  }, [capabilities, searchQuery]);

  const columns = useMemo(
    () => [
      columnHelper.accessor('name', {
        header: 'Name',
        cell: (info) => (
          <button
            onClick={() => onEditCapability(info.row.original)}
            className="font-medium text-primary-600 hover:text-primary-700 hover:underline"
          >
            {info.getValue()}
          </button>
        ),
      }),
      columnHelper.accessor('type', {
        header: 'Type',
        cell: (info) => {
          const type = info.getValue();
          const config = TYPE_BADGE_CONFIG[type];
          return (
            <Badge size="sm" variant={config.variant}>
              {config.icon}
              {config.label}
            </Badge>
          );
        },
      }),
      columnHelper.accessor('description', {
        header: 'Description',
        cell: (info) => (
          <span className="text-gray-600" title={info.getValue()}>
            {truncate(info.getValue(), 50)}
          </span>
        ),
      }),
      columnHelper.display({
        id: 'content',
        header: 'Content',
        cell: (info) => {
          const cap = info.row.original;
          return (
            <div className="flex items-center gap-2">
              {cap.has_script && (
                <Badge size="sm" variant="success">
                  <FileCode className="w-3 h-3 mr-1" />
                  {cap.script_name}
                </Badge>
              )}
              {cap.has_text && (
                <Badge size="sm" variant="default">
                  <FileText className="w-3 h-3 mr-1" />
                  Text
                </Badge>
              )}
              {cap.has_mcp && (
                <Badge size="sm" variant="info">
                  <Server className="w-3 h-3 mr-1" />
                  {cap.mcp_server_names.length} MCP
                </Badge>
              )}
              {!cap.has_script && !cap.has_text && !cap.has_mcp && (
                <span className="text-gray-400 text-xs italic">Empty</span>
              )}
            </div>
          );
        },
      }),
      columnHelper.display({
        id: 'mcp_servers',
        header: 'MCP Servers',
        cell: (info) => {
          const names = info.row.original.mcp_server_names;
          if (names.length === 0) {
            return <span className="text-gray-400 text-xs italic">None</span>;
          }
          const display = names.slice(0, 2);
          const remaining = names.length - 2;
          return (
            <div className="flex flex-wrap gap-1">
              {display.map((name) => (
                <Badge key={name} size="sm" variant="gray">
                  {name}
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
      columnHelper.display({
        id: 'actions',
        cell: (info) => {
          const cap = info.row.original;
          return (
            <div className="flex items-center gap-1">
              <button
                onClick={() => onEditCapability(cap)}
                className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                title="Edit"
              >
                <Edit2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => onDeleteCapability(cap.name)}
                className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                title="Delete"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          );
        },
        size: 80,
      }),
    ],
    [onEditCapability, onDeleteCapability]
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
            placeholder="Search capabilities..."
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
            icon={<Puzzle className="w-12 h-12" />}
            title="No capabilities found"
            description={
              searchQuery
                ? 'Try adjusting your search'
                : 'Create your first capability to get started'
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
        {filteredData.length} of {capabilities.length} capabilities
      </div>
    </div>
  );
}
