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
import type { MCPServerRegistryEntry } from '@/types/mcpServer';
import { Badge, EmptyState, SkeletonLine } from '@/components/common';
import { truncate } from '@/utils/formatters';
import { Server, Search, Edit2, Trash2 } from 'lucide-react';

interface McpServerTableProps {
  servers: MCPServerRegistryEntry[];
  loading?: boolean;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onEditServer: (server: MCPServerRegistryEntry) => void;
  onDeleteServer: (id: string) => void;
}

const columnHelper = createColumnHelper<MCPServerRegistryEntry>();

export function McpServerTable({
  servers,
  loading = false,
  searchQuery,
  onSearchChange,
  onEditServer,
  onDeleteServer,
}: McpServerTableProps) {
  const [sorting, setSorting] = useState<SortingState>([{ id: 'id', desc: false }]);

  const filteredData = useMemo(() => {
    if (!searchQuery) return servers;

    const query = searchQuery.toLowerCase();
    return servers.filter(
      (server) =>
        server.id.toLowerCase().includes(query) ||
        server.name.toLowerCase().includes(query) ||
        (server.description?.toLowerCase().includes(query) ?? false) ||
        server.url.toLowerCase().includes(query)
    );
  }, [servers, searchQuery]);

  const columns = useMemo(
    () => [
      columnHelper.accessor('id', {
        header: 'ID',
        cell: (info) => (
          <button
            onClick={() => onEditServer(info.row.original)}
            className="font-mono text-sm font-medium text-primary-600 hover:text-primary-700 hover:underline"
          >
            {info.getValue()}
          </button>
        ),
      }),
      columnHelper.accessor('name', {
        header: 'Name',
        cell: (info) => (
          <span className="font-medium text-gray-900">{info.getValue()}</span>
        ),
      }),
      columnHelper.accessor('url', {
        header: 'URL',
        cell: (info) => (
          <span className="font-mono text-xs text-gray-600" title={info.getValue()}>
            {truncate(info.getValue(), 40)}
          </span>
        ),
      }),
      columnHelper.display({
        id: 'config_fields',
        header: 'Config Fields',
        cell: (info) => {
          const schema = info.row.original.config_schema;
          if (!schema || Object.keys(schema).length === 0) {
            return <span className="text-gray-400 text-xs italic">None</span>;
          }

          const fields = Object.entries(schema);
          const requiredCount = fields.filter(([, f]) => f.required).length;
          const display = fields.slice(0, 3).map(([name]) => name);
          const remaining = fields.length - 3;

          return (
            <div className="flex items-center gap-2">
              <div className="flex flex-wrap gap-1">
                {display.map((name) => {
                  const field = schema[name];
                  return (
                    <Badge
                      key={name}
                      size="sm"
                      variant={field.required ? 'warning' : 'gray'}
                    >
                      {name}
                      {field.required && <span className="text-red-500 ml-0.5">*</span>}
                    </Badge>
                  );
                })}
                {remaining > 0 && (
                  <Badge size="sm" variant="gray">
                    +{remaining}
                  </Badge>
                )}
              </div>
              {requiredCount > 0 && (
                <span className="text-xs text-amber-600">
                  ({requiredCount} required)
                </span>
              )}
            </div>
          );
        },
      }),
      columnHelper.accessor('description', {
        header: 'Description',
        cell: (info) => {
          const desc = info.getValue();
          if (!desc) {
            return <span className="text-gray-400 text-xs italic">No description</span>;
          }
          return (
            <span className="text-gray-600 text-sm" title={desc}>
              {truncate(desc, 40)}
            </span>
          );
        },
      }),
      columnHelper.display({
        id: 'actions',
        cell: (info) => {
          const server = info.row.original;
          return (
            <div className="flex items-center gap-1">
              <button
                onClick={() => onEditServer(server)}
                className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                title="Edit"
              >
                <Edit2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => onDeleteServer(server.id)}
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
    [onEditServer, onDeleteServer]
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
            placeholder="Search MCP servers..."
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
            icon={<Server className="w-12 h-12" />}
            title="No MCP servers found"
            description={
              searchQuery
                ? 'Try adjusting your search'
                : 'Create your first MCP server registry entry to get started'
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
        {filteredData.length} of {servers.length} MCP servers
      </div>
    </div>
  );
}
