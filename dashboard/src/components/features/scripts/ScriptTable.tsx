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
import { ScriptSummary } from '@/types/script';
import { Badge, EmptyState, SkeletonLine } from '@/components/common';
import { truncate } from '@/utils/formatters';
import { Code2, Search, Edit2, Trash2, FileCode, Tag } from 'lucide-react';

interface ScriptTableProps {
  scripts: ScriptSummary[];
  loading?: boolean;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onEditScript: (script: ScriptSummary) => void;
  onDeleteScript: (name: string) => void;
}

const columnHelper = createColumnHelper<ScriptSummary>();

export function ScriptTable({
  scripts,
  loading = false,
  searchQuery,
  onSearchChange,
  onEditScript,
  onDeleteScript,
}: ScriptTableProps) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'name', desc: false },
  ]);

  const filteredData = useMemo(() => {
    if (!searchQuery) return scripts;

    const query = searchQuery.toLowerCase();
    return scripts.filter(
      (script) =>
        script.name.toLowerCase().includes(query) ||
        script.description.toLowerCase().includes(query) ||
        script.script_file.toLowerCase().includes(query)
    );
  }, [scripts, searchQuery]);

  const columns = useMemo(
    () => [
      columnHelper.accessor('name', {
        header: 'Name',
        cell: (info) => (
          <button
            onClick={() => onEditScript(info.row.original)}
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
      columnHelper.accessor('script_file', {
        header: 'Script File',
        cell: (info) => (
          <div className="flex items-center gap-1">
            <FileCode className="w-3.5 h-3.5 text-gray-400" />
            <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded text-gray-700">
              {info.getValue()}
            </code>
          </div>
        ),
      }),
      columnHelper.display({
        id: 'content',
        header: 'Features',
        cell: (info) => {
          const script = info.row.original;
          return (
            <div className="flex items-center gap-2">
              {script.has_parameters_schema && (
                <Badge size="sm" variant="default">
                  Schema
                </Badge>
              )}
              {script.has_demands && (
                <Badge size="sm" variant="info">
                  Demands
                </Badge>
              )}
              {!script.has_parameters_schema && !script.has_demands && (
                <span className="text-gray-400 text-xs italic">Basic</span>
              )}
            </div>
          );
        },
      }),
      columnHelper.display({
        id: 'demand_tags',
        header: 'Demand Tags',
        cell: (info) => {
          const tags = info.row.original.demand_tags;
          if (tags.length === 0) {
            return <span className="text-gray-400 text-xs italic">None</span>;
          }
          const display = tags.slice(0, 2);
          const remaining = tags.length - 2;
          return (
            <div className="flex flex-wrap gap-1">
              {display.map((tag) => (
                <Badge key={tag} size="sm" variant="gray">
                  <Tag className="w-3 h-3 mr-0.5" />
                  {tag}
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
          const script = info.row.original;
          return (
            <div className="flex items-center gap-1">
              <button
                onClick={() => onEditScript(script)}
                className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                title="Edit"
              >
                <Edit2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => onDeleteScript(script.name)}
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
    [onEditScript, onDeleteScript]
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
            placeholder="Search scripts..."
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
            icon={<Code2 className="w-12 h-12" />}
            title="No scripts found"
            description={
              searchQuery
                ? 'Try adjusting your search'
                : 'Create your first script to get started'
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
        {filteredData.length} of {scripts.length} scripts
      </div>
    </div>
  );
}
